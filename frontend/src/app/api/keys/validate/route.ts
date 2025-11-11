/**
 * @fileoverview BYOK validate route. Checks if a provided API key is valid for a given service.
 * Route: POST /api/keys/validate
 * Never persists the key.
 */

"use cache";

export const dynamic = "force-dynamic";

import { createAnthropic } from "@ai-sdk/anthropic";
import { createOpenAI } from "@ai-sdk/openai";
import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { buildRateLimitKey } from "@/lib/next/route-helpers";
import type { ProviderId } from "@/lib/providers/types";
import { getProviderSettings } from "@/lib/settings";
import { createServerSupabase } from "@/lib/supabase/server";

// Environment variables
const UPSTASH_URL = process.env.UPSTASH_REDIS_REST_URL;
const UPSTASH_TOKEN = process.env.UPSTASH_REDIS_REST_TOKEN;
const RATELIMIT_PREFIX = "ratelimit:keys-validate";

// Create rate limit instance lazily to make testing easier
const GET_RATELIMIT_INSTANCE = () => {
  if (!UPSTASH_URL || !UPSTASH_TOKEN) {
    return undefined;
  }

  return new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(20, "1 m"),
    prefix: RATELIMIT_PREFIX,
    redis: Redis.fromEnv(),
  });
};

type ValidateResult = { isValid: boolean; reason?: string };

const DEFAULT_MODEL_IDS: Record<ProviderId, string> = {
  anthropic: "claude-3-5-sonnet-20241022",
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

type ConfigurableModel = {
  config: {
    baseURL?: string;
    fetch?: typeof fetch;
    headers: () => HeadersInit;
  };
};

const OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1";
const XAI_BASE_URL = "https://api.x.ai/v1";

function toHeaders(
  headers?: Record<string, string>
): Record<string, string> | undefined {
  if (!headers) return undefined;
  const entries = Object.entries(headers).filter(([, value]) => value !== undefined);
  if (entries.length === 0) return undefined;
  return Object.fromEntries(entries);
}

function buildOpenAICompatibleRequest(options: {
  apiKey: string;
  baseURL?: string;
  headers?: Record<string, string>;
  modelId: string;
}): ProviderRequest {
  const providerHeaders = toHeaders(options.headers);
  const provider = createOpenAI({
    apiKey: options.apiKey,
    ...(options.baseURL ? { baseURL: options.baseURL } : {}),
    ...(providerHeaders ? { headers: providerHeaders } : {}),
  });
  const model = provider(options.modelId) as unknown as ConfigurableModel;
  const config = model.config;
  const headers = config.headers();
  const baseURL =
    options.baseURL?.trim() || config.baseURL || "https://api.openai.com/v1";
  const normalizedBase = baseURL.endsWith("/") ? baseURL : `${baseURL}/`;
  const url = new URL("models", normalizedBase).toString();
  return {
    fetchImpl: config.fetch ?? fetch,
    headers,
    url,
  };
}

function buildAnthropicRequest(apiKey: string): ProviderRequest {
  const provider = createAnthropic({ apiKey });
  const model = provider(DEFAULT_MODEL_IDS.anthropic) as unknown as ConfigurableModel;
  const config = model.config;
  const baseURL = config.baseURL ?? "https://api.anthropic.com/v1";
  const normalizedBase = baseURL.endsWith("/") ? baseURL : `${baseURL}/`;
  const url = new URL("models", normalizedBase).toString();
  const headers = config.headers();
  return {
    fetchImpl: config.fetch ?? fetch,
    headers,
    url,
  };
}

function buildOpenRouterHeaders(): Record<string, string> | undefined {
  const settings = getProviderSettings();
  const headers: Record<string, string> = {};
  const referer = settings.openrouterAttribution?.referer;
  const title = settings.openrouterAttribution?.title;
  if (referer) headers["HTTP-Referer"] = referer;
  if (title) headers["X-Title"] = title;
  return Object.keys(headers).length > 0 ? headers : undefined;
}

const PROVIDER_BUILDERS: Partial<Record<ProviderId, ProviderRequestBuilder>> = {
  anthropic: (apiKey) => buildAnthropicRequest(apiKey),
  openai: (apiKey) =>
    buildOpenAICompatibleRequest({
      apiKey,
      baseURL: process.env.AI_GATEWAY_URL?.trim() || undefined,
      modelId: DEFAULT_MODEL_IDS.openai,
    }),
  openrouter: (apiKey) =>
    buildOpenAICompatibleRequest({
      apiKey,
      baseURL: OPENROUTER_BASE_URL,
      headers: buildOpenRouterHeaders(),
      modelId: DEFAULT_MODEL_IDS.openrouter,
    }),
  xai: (apiKey) =>
    buildOpenAICompatibleRequest({
      apiKey,
      baseURL: XAI_BASE_URL,
      modelId: DEFAULT_MODEL_IDS.xai,
    }),
};

function normalizeErrorReason(error: unknown): string {
  if (error instanceof TypeError) return "TRANSPORT_ERROR";
  if (error instanceof Error) {
    const name = error.name || "Error";
    const withoutSuffix = name.replace(/Error$/, "");
    const snake = withoutSuffix
      .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
      .replace(/[^A-Za-z0-9]+/g, "_")
      .replace(/_+/g, "_")
      .replace(/^_|_$/g, "")
      .toUpperCase();
    return snake.length > 0 ? snake : "UNKNOWN_ERROR";
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
  const providerId = service.trim().toLowerCase() as ProviderId;
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
    console.error("Provider key validation error", {
      message,
      provider: providerId,
      reason,
    });
    return { isValid: false, reason };
  }
}

/**
 * Require rate limiting for the request identifier.
 *
 * @param identifier Unique bucket key (user id or derived token/IP).
 * @returns NextResponse with 429 status if rate limit exceeded, otherwise null.
 */
async function requireRateLimit(identifier: string): Promise<NextResponse | null> {
  const ratelimitInstance = GET_RATELIMIT_INSTANCE();
  if (!ratelimitInstance) return null;
  const { success, limit, remaining, reset } =
    await ratelimitInstance.limit(identifier);
  if (!success) {
    return NextResponse.json(
      { code: "RATE_LIMIT", error: "Rate limit exceeded" },
      {
        headers: {
          "X-RateLimit-Limit": String(limit),
          "X-RateLimit-Remaining": String(remaining),
          "X-RateLimit-Reset": String(reset),
        },
        status: 429,
      }
    );
  }
  return null;
}

/**
 * Handle POST /api/keys/validate to verify a user-supplied API key.
 *
 * Orchestrates rate limiting, authentication, and provider validation.
 *
 * @param req Next.js request containing JSON body with { service, apiKey }.
 * @returns 200 with validation result; 400/401/429/500 on error.
 */
export async function POST(req: NextRequest) {
  try {
    const supabase = await createServerSupabase();
    const {
      data: { user },
      error,
    } = await supabase.auth.getUser();
    const identifier = user?.id ?? buildRateLimitKey(req);

    const rateLimitResponse = await requireRateLimit(identifier);
    if (rateLimitResponse) {
      return rateLimitResponse;
    }

    let service: string | undefined;
    let apiKey: string | undefined;
    try {
      const body = await req.json();
      service = body.service;
      apiKey = body.apiKey;
    } catch (parseError) {
      const message =
        parseError instanceof Error ? parseError.message : "Unknown JSON parse error";
      console.error("/api/keys/validate POST JSON parse error:", { message });
      return NextResponse.json(
        { code: "BAD_REQUEST", error: "Malformed JSON in request body" },
        { status: 400 }
      );
    }

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

    if (error || !user) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const result = await validateProviderKey(service, apiKey);
    return NextResponse.json(result, { status: 200 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    console.error("/api/keys/validate POST error:", { message });
    return NextResponse.json(
      { code: "INTERNAL_ERROR", error: "Internal server error" },
      { status: 500 }
    );
  }
}
