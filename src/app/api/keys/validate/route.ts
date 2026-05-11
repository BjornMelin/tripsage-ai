/**
 * @fileoverview POST /api/keys/validate verifies a user-supplied provider API key without persisting it.
 */

import "server-only";

// Security: Prevent caching of sensitive API key data per ADR-0024.
// With Cache Components enabled, route handlers are dynamic by default.
// Using withApiGuards({ auth: true }) ensures this route uses cookies/headers,
// making it dynamic and preventing caching. No 'use cache' directives are present.

import {
  ANTHROPIC_VALIDATION_MODEL_ID,
  DEFAULT_GATEWAY_MODEL_ID,
  DEFAULT_OPENAI_MODEL_ID,
  DEFAULT_OPENROUTER_MODEL_ID,
  DEFAULT_XAI_MODEL_ID,
} from "@ai/models/defaults";
import { createAnthropic } from "@ai-sdk/anthropic";
import { createOpenAI } from "@ai-sdk/openai";
import { postKeyBodySchema } from "@schemas/api";
import { createGateway } from "ai";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { validateGatewayBaseUrl } from "@/lib/ai/gateway-url";
import { withApiGuards } from "@/lib/api/factory";
import { parseJsonBody, validateSchema } from "@/lib/api/route-helpers";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { recordTelemetryEvent, withTelemetrySpan } from "@/lib/telemetry/span";
import {
  mapProviderExceptionToCode,
  mapProviderStatusToCode,
  PLANNED_ERROR_CODES,
} from "../_error-mapping";

type ValidateResult = { isValid: boolean; reason?: string };

const DEFAULT_MODEL_IDS: Record<string, string> = {
  anthropic: ANTHROPIC_VALIDATION_MODEL_ID,
  gateway: DEFAULT_GATEWAY_MODEL_ID,
  openai: DEFAULT_OPENAI_MODEL_ID,
  openrouter: DEFAULT_OPENROUTER_MODEL_ID,
  xai: DEFAULT_XAI_MODEL_ID,
};

type ProviderRequest = {
  fetchImpl: typeof fetch;
  headers: HeadersInit;
  url: string;
};

type ProviderRequestBuilder = (
  apiKey: string
) => ProviderRequest | Promise<ProviderRequest>;

type SDKCreator = (options: {
  apiKey: string;
  baseURL?: string;
  headers?: Record<string, string>;
}) => (modelId: string) => unknown;

type ConfigurableModel = {
  config: {
    baseURL?: string;
    fetch?: typeof fetch;
    headers: () => HeadersInit | Promise<HeadersInit>;
  };
};

const OPENAI_BASE_URL = "https://api.openai.com/v1";
const OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1";
const ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1";
const XAI_BASE_URL = "https://api.x.ai/v1";
/**
 * Timeout for key validation requests.
 *
 * NOTE: AbortSignal.timeout(VALIDATE_TIMEOUT_MS) only cancels the fetch at the
 * application/promise level and does not override undici’s internal connect
 * timeout (which defaults to ~10s), so callers should configure a Dispatcher
 * when strict connect-level timing is required.
 */
const VALIDATE_TIMEOUT_MS = 5_000;

const validateKeyRequestSchema = postKeyBodySchema.pick({
  apiKey: true,
  service: true,
});

type BuildSDKRequestOptions = {
  apiKey: string;
  baseURL?: string;
  defaultBaseURL: string;
  headers?: Record<string, string>;
  modelId: string;
  probePath?: string;
  sdkCreator: SDKCreator;
};

async function buildSDKRequest(
  options: BuildSDKRequestOptions
): Promise<ProviderRequest> {
  const trimmedBaseURL = options.baseURL?.trim();
  const provider = options.sdkCreator({
    apiKey: options.apiKey,
    ...(trimmedBaseURL ? { baseURL: trimmedBaseURL } : {}),
    ...(options.headers ? { headers: options.headers } : {}),
  });
  const model = provider(options.modelId) as ConfigurableModel;
  const config = model.config;
  if (!config || typeof config.headers !== "function") {
    throw new Error(
      "Unexpected SDK model structure for provider - config access failed"
    );
  }
  const resolvedBaseURL = trimmedBaseURL || config.baseURL || options.defaultBaseURL;
  const normalizedBase = resolvedBaseURL.endsWith("/")
    ? resolvedBaseURL
    : `${resolvedBaseURL}/`;
  return {
    fetchImpl: config.fetch ?? fetch,
    headers: await config.headers(),
    url: new URL(options.probePath ?? "models", normalizedBase).toString(),
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
  openai: (apiKey) =>
    buildSDKRequest({
      apiKey,
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
  return mapProviderExceptionToCode(error);
}

function getErrorStatus(error: unknown): number | undefined {
  if (!error || typeof error !== "object") return undefined;
  const status = (error as { status?: unknown }).status;
  if (typeof status === "number") return status;
  const statusCode = (error as { statusCode?: unknown }).statusCode;
  if (typeof statusCode === "number") return statusCode;
  const response = (error as { response?: { status?: unknown } }).response;
  return typeof response?.status === "number" ? response.status : undefined;
}

function mapGatewayCreditsErrorToCode(error: unknown): string {
  const status = getErrorStatus(error);
  return typeof status === "number"
    ? mapProviderStatusToCode(status)
    : mapProviderExceptionToCode(error);
}

function createValidationFetch(timeoutMs: number): typeof fetch {
  return async (input, init) =>
    fetch(input, {
      ...init,
      signal: init?.signal ?? AbortSignal.timeout(timeoutMs),
    });
}

async function validateGatewayKey(apiKey: string): Promise<ValidateResult> {
  const configuredUrl = getServerEnvVarWithFallback("AI_GATEWAY_URL", undefined);
  const gatewayUrl = validateGatewayBaseUrl(configuredUrl, { source: "team" });
  if (!gatewayUrl.ok) {
    throw new Error(`Gateway base URL rejected: ${gatewayUrl.reason}`);
  }

  const gateway = createGateway({
    apiKey,
    fetch: createValidationFetch(VALIDATE_TIMEOUT_MS),
    ...(gatewayUrl.baseUrl
      ? {
          baseURL: gatewayUrl.baseUrl,
        }
      : {}),
  });

  try {
    await gateway.getCredits();
    return { isValid: true };
  } catch (error) {
    return { isValid: false, reason: mapGatewayCreditsErrorToCode(error) };
  }
}

/**
 * Validates a provider API key by probing the provider's endpoint.
 *
 * @param service - Provider identifier: "openai", "openrouter", "anthropic", "xai", or "gateway".
 * @param apiKey - The plaintext API key to validate.
 * @returns `{ isValid: true }` if the key is accepted;
 *   `{ isValid: false, reason: string }` otherwise.
 */
async function validateProviderKey(
  service: string,
  apiKey: string
): Promise<ValidateResult> {
  const providerId = service.trim().toLowerCase();
  return await withTelemetrySpan(
    "keys.provider.validate",
    {
      attributes: {
        "keys.provider": providerId,
        "keys.validation.timeout_ms": VALIDATE_TIMEOUT_MS,
      },
    },
    async (span) => {
      try {
        if (providerId === "gateway") {
          const result = await validateGatewayKey(apiKey);
          span.setAttribute("keys.validation.is_valid", result.isValid);
          if (result.reason) span.setAttribute("keys.validation.reason", result.reason);
          return result;
        }

        const builder = PROVIDER_BUILDERS[providerId];
        if (!builder) {
          // Planned BYOK GA codes intentionally collapse schema/provider-builder
          // drift into user-actionable invalid-key handling instead of returning
          // the legacy unstable INVALID_SERVICE code.
          span.setAttribute("keys.validation.is_valid", false);
          span.setAttribute("keys.validation.reason", PLANNED_ERROR_CODES.invalidKey);
          return { isValid: false, reason: PLANNED_ERROR_CODES.invalidKey };
        }

        const { fetchImpl, headers, url } = await builder(apiKey);
        const response = await fetchImpl(url, {
          headers,
          method: "GET",
          signal: AbortSignal.timeout(VALIDATE_TIMEOUT_MS),
        });
        span.setAttribute("http.response.status_code", response.status);
        if (response.status === 200) {
          span.setAttribute("keys.validation.is_valid", true);
          return { isValid: true };
        }
        const reason = mapProviderStatusToCode(response.status);
        span.setAttribute("keys.validation.is_valid", false);
        span.setAttribute("keys.validation.reason", reason);
        return { isValid: false, reason };
      } catch (error) {
        const reason = normalizeErrorReason(error);
        span.setAttribute("keys.validation.is_valid", false);
        span.setAttribute("keys.validation.reason", reason);
        recordTelemetryEvent("api.keys.validate_provider_error", {
          attributes: {
            error_name: error instanceof Error ? error.name : typeof error,
            provider: providerId,
            reason,
          },
          level: "error",
        });
        return { isValid: false, reason };
      }
    }
  );
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
  botId: true,
  rateLimit: "keys:validate",
  // Custom telemetry handled below
})(async (req: NextRequest) => {
  const parsed = await parseJsonBody(req);
  if (!parsed.ok) {
    recordTelemetryEvent("api.keys.validate.parse_error", {
      attributes: { message: "JSON parse failed", status: parsed.error.status },
      level: "error",
    });
    return parsed.error;
  }

  const validation = validateSchema(validateKeyRequestSchema, parsed.data);
  if (!validation.ok) return validation.error;

  const result = await validateProviderKey(
    validation.data.service,
    validation.data.apiKey
  );
  return NextResponse.json(result, { status: 200 });
});
