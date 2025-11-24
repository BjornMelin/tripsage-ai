/**
 * @fileoverview BYOK validate route. Checks if a provided API key is valid for a given service.
 * Route: POST /api/keys/validate
 * Never persists the key.
 */

import "server-only";

// Security: Prevent caching of sensitive API key data per ADR-0024.
// With Cache Components enabled, route handlers are dynamic by default.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching. No 'use cache' directives are present.

import { createAnthropic } from "@ai-sdk/anthropic";
import { createOpenAI } from "@ai-sdk/openai";
import { createGateway } from "ai";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody } from "@/lib/api/route-helpers";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

type ValidateResult = { isValid: boolean; reason?: string };

const DEFAULT_MODEL_IDS: Record<string, string> = {
  anthropic: "claude-3-5-sonnet-20241022",
  gateway: "openai/gpt-4o-mini",
  openai: "gpt-4o-mini",
  openrouter: "openai/gpt-4o-mini",
  xai: "grok-3",
};

type ProviderRequest = {
  fetchImpl: typeof fetch;
  headers: HeadersInit;
  url: string;
};

type ProviderRequestBuilder = (apiKey: string) => ProviderRequest;

type SDKCreator = (options: {
  apiKey: string;
  baseURL?: string;
  headers?: Record<string, string>;
}) => (modelId: string) => unknown;

type ConfigurableModel = {
  config: {
    baseURL?: string;
    fetch?: typeof fetch;
    headers: () => HeadersInit;
  };
};

const OPENAI_BASE_URL = "https://api.openai.com/v1";
const OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1";
const ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1";
const XAI_BASE_URL = "https://api.x.ai/v1";

type BuildSDKRequestOptions = {
  apiKey: string;
  baseURL?: string;
  defaultBaseURL: string;
  headers?: Record<string, string>;
  modelId: string;
  sdkCreator: SDKCreator;
};

function buildSDKRequest(options: BuildSDKRequestOptions): ProviderRequest {
  const trimmedBaseURL = options.baseURL?.trim();
  const provider = options.sdkCreator({
    apiKey: options.apiKey,
    ...(trimmedBaseURL ? { baseURL: trimmedBaseURL } : {}),
    ...(options.headers ? { headers: options.headers } : {}),
  });
  const model = provider(options.modelId) as ConfigurableModel;
  const config = model.config;
  const resolvedBaseURL = trimmedBaseURL || config.baseURL || options.defaultBaseURL;
  const normalizedBase = resolvedBaseURL.endsWith("/")
    ? resolvedBaseURL
    : `${resolvedBaseURL}/`;
  return {
    fetchImpl: config.fetch ?? fetch,
    headers: config.headers(),
    url: new URL("models", normalizedBase).toString(),
  };
}

const PROVIDER_BUILDERS: Partial<Record<string, ProviderRequestBuilder>> = {
  anthropic: (apiKey) =>
    buildSDKRequest({
      apiKey,
      defaultBaseURL: ANTHROPIC_BASE_URL,
      modelId: DEFAULT_MODEL_IDS.anthropic,
      sdkCreator: createAnthropic as SDKCreator,
    }),
  gateway: (apiKey) =>
    buildSDKRequest({
      apiKey,
      baseURL: getServerEnvVarWithFallback("AI_GATEWAY_URL", undefined),
      defaultBaseURL: "https://ai-gateway.vercel.sh/v1",
      modelId: DEFAULT_MODEL_IDS.gateway,
      sdkCreator: createGateway as unknown as SDKCreator,
    }),
  openai: (apiKey) =>
    buildSDKRequest({
      apiKey,
      baseURL: getServerEnvVarWithFallback("AI_GATEWAY_URL", undefined),
      defaultBaseURL: OPENAI_BASE_URL,
      modelId: DEFAULT_MODEL_IDS.openai,
      sdkCreator: createOpenAI as SDKCreator,
    }),
  openrouter: (apiKey) =>
    buildSDKRequest({
      apiKey,
      baseURL: OPENROUTER_BASE_URL,
      defaultBaseURL: OPENROUTER_BASE_URL,
      modelId: DEFAULT_MODEL_IDS.openrouter,
      sdkCreator: createOpenAI as SDKCreator,
    }),
  xai: (apiKey) =>
    buildSDKRequest({
      apiKey,
      baseURL: XAI_BASE_URL,
      defaultBaseURL: XAI_BASE_URL,
      modelId: DEFAULT_MODEL_IDS.xai,
      sdkCreator: createOpenAI as SDKCreator,
    }),
};

function normalizeErrorReason(error: unknown): string {
  if (error instanceof TypeError) return "TRANSPORT_ERROR";
  if (error instanceof Error && error.name) {
    return error.name.toUpperCase();
  }
  return "UNKNOWN_ERROR";
}

/**
 * Generic validator using provider configuration map.
 *
 * @param service Provider identifier (openai|openrouter|anthropic|xai).
 * @param apiKey The plaintext API key to check.
 * @returns Validation result with is_valid and optional reason.
 */
async function validateProviderKey(
  service: string,
  apiKey: string
): Promise<ValidateResult> {
  const providerId = service.trim().toLowerCase();
  const builder = PROVIDER_BUILDERS[providerId];
  if (!builder) {
    return { isValid: false, reason: "INVALID_SERVICE" };
  }

  try {
    const { fetchImpl, headers, url } = builder(apiKey);
    const response = await fetchImpl(url, {
      headers,
      method: "GET",
    });
    if (response.status === 200) return { isValid: true };
    if ([401, 403].includes(response.status)) {
      return { isValid: false, reason: "UNAUTHORIZED" };
    }
    return { isValid: false, reason: `HTTP_${response.status}` };
  } catch (error) {
    const reason = normalizeErrorReason(error);
    const message = error instanceof Error ? error.message : "Unknown error";
    recordTelemetryEvent("api.keys.validate_provider_error", {
      attributes: {
        message,
        provider: providerId,
        reason,
      },
      level: "error",
    });
    return { isValid: false, reason };
  }
}

/**
 * Handle POST /api/keys/validate to verify a user-supplied API key.
 *
 * Orchestrates rate limiting, authentication, and provider validation.
 *
 * @param req Next.js request containing JSON body with { service, apiKey }.
 * @param routeContext Route context from withApiGuards
 * @returns 200 with validation result; 400/401/429/500 on error.
 */
export const POST = withApiGuards({
  auth: true,
  rateLimit: "keys:validate",
  // Custom telemetry handled below
})(async (req: NextRequest, { user: _user }) => {
  const parsed = await parseJsonBody(req);
  if ("error" in parsed) {
    recordTelemetryEvent("api.keys.validate.parse_error", {
      attributes: { message: "JSON parse failed" },
      level: "error",
    });
    return NextResponse.json(
      { code: "BAD_REQUEST", error: "Malformed JSON in request body" },
      { status: 400 }
    );
  }

  const body = parsed.body as { service?: unknown; apiKey?: unknown };
  const service = body.service;
  const apiKey = body.apiKey;

  if (
    !service ||
    !apiKey ||
    typeof service !== "string" ||
    typeof apiKey !== "string"
  ) {
    return NextResponse.json(
      { code: "BAD_REQUEST", error: "Invalid request body" },
      { status: 400 }
    );
  }

  const result = await validateProviderKey(service, apiKey);
  return NextResponse.json(result, { status: 200 });
});
