/**
 * @fileoverview Provider registry and model resolution for AI SDK v6.
 * Centralizes BYOK key lookup via Supabase RPC and returns a ready
 * LanguageModel for downstream routes (no client-side secrets).
 */
import "server-only";

import { createAnthropic } from "@ai-sdk/anthropic";
import { createOpenAI } from "@ai-sdk/openai";
import { createXai } from "@ai-sdk/xai";
import { createGateway } from "ai";
import type {
  ModelMapper,
  ProviderId,
  ProviderResolution,
} from "@/lib/providers/types";
import {
  getUserAllowGatewayFallback,
  getUserApiKey,
  getUserGatewayBaseUrl,
  touchUserApiKey,
} from "@/lib/supabase/rpc";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/** Provider preference order for BYOK key resolution. */
const PROVIDER_PREFERENCE: ProviderId[] = ["openai", "openrouter", "anthropic", "xai"];

function extractHost(url: string | undefined): string | undefined {
  if (!url) return undefined;
  try {
    return new URL(url).host;
  } catch {
    // ignore parse errors for malformed URLs
    return undefined;
  }
}

/**
 * Map a generic model hint to a provider-specific id.
 * Keep conservative and simple; leave full mapping to callers/routes if needed.
 */
const DEFAULT_MODEL_MAPPER: ModelMapper = (
  provider: ProviderId,
  modelHint?: string
): string => {
  if (!modelHint || modelHint.trim().length === 0) {
    // Sensible defaults per provider
    switch (provider) {
      case "openai":
        return "gpt-5-mini";
      case "openrouter":
        return "openai/gpt-4o-mini";
      case "anthropic":
        return "claude-haiku-4-5";
      case "xai":
        return "grok-4-fast";
      default:
        return "grok-4-fast";
    }
  }
  // For OpenRouter, accept fully-qualified ids like "provider/model"
  if (provider === "openrouter") {
    return modelHint;
  }
  // For others, return hint as-is; callers supply proper ids.
  return modelHint;
};

/**
 * Resolve user's preferred provider and return a ready AI SDK model.
 *
 * @param userId Supabase auth user id; used to fetch BYOK keys server-side.
 * @param modelHint Optional generic model hint (e.g., "gpt-4o-mini").
 * @returns ProviderResolution including provider id, model id, and model instance.
 * @throws Error if no provider key is found for the user.
 */
export async function resolveProvider(
  userId: string,
  modelHint?: string
): Promise<ProviderResolution> {
  // 0) Per-user Gateway key (if present): highest precedence
  const userGatewayKey = await getUserApiKey(userId, "gateway");
  if (userGatewayKey) {
    const baseUrl =
      (await getUserGatewayBaseUrl(userId)) ?? "https://ai-gateway.vercel.sh/v1";
    const client = createGateway({
      apiKey: userGatewayKey,
      // biome-ignore lint/style/useNamingConvention: provider option name
      baseURL: baseUrl,
    });
    const modelId = DEFAULT_MODEL_MAPPER("openai", modelHint);
    return await withTelemetrySpan(
      "providers.resolve",
      {
        attributes: {
          baseUrlHost: extractHost(baseUrl) ?? "ai-gateway.vercel.sh",
          baseUrlSource: "user",
          modelId,
          path: "user-gateway",
          provider: "gateway",
        },
      },
      async () => ({
        model: client(modelId) as unknown as import("ai").LanguageModel,
        modelId,
        provider: "openai",
      })
    );
  }

  // 1) Check for BYOK keys concurrently (OpenAI, OpenRouter, Anthropic, xAI)
  const providers = PROVIDER_PREFERENCE;
  const keyResults = await Promise.all(
    providers.map(async (p) => ({ key: await getUserApiKey(userId, p), p }))
  );
  for (const { p: provider, key: apiKey } of keyResults) {
    if (!apiKey) continue;
    const modelId = DEFAULT_MODEL_MAPPER(provider, modelHint);
    if (provider === "openai") {
      const openai = createOpenAI({ apiKey });
      // Fire-and-forget: update last used timestamp (ignore errors)
      touchUserApiKey(userId, provider).catch(() => undefined);
      return await withTelemetrySpan(
        "providers.resolve",
        { attributes: { modelId, path: "user-provider", provider } },
        async () => ({
          model: openai(modelId) as unknown as import("ai").LanguageModel,
          modelId,
          provider,
        })
      );
    }
    if (provider === "openrouter") {
      const openrouter = createOpenAI({
        apiKey,
        // biome-ignore lint/style/useNamingConvention: provider option name
        baseURL: "https://openrouter.ai/api/v1",
      });
      // Fire-and-forget: update last used timestamp (ignore errors)
      touchUserApiKey(userId, provider).catch(() => undefined);
      return await withTelemetrySpan(
        "providers.resolve",
        { attributes: { modelId, path: "user-provider", provider } },
        async () => ({
          model: openrouter(modelId) as unknown as import("ai").LanguageModel,
          modelId,
          provider,
        })
      );
    }
    if (provider === "anthropic") {
      const a = createAnthropic({ apiKey });
      // Fire-and-forget: update last used timestamp (ignore errors)
      touchUserApiKey(userId, provider).catch(() => {
        // Ignore errors for fire-and-forget operation
      });
      return await withTelemetrySpan(
        "providers.resolve",
        { attributes: { modelId, path: "user-provider", provider } },
        async () => ({
          model: a(modelId) as unknown as import("ai").LanguageModel,
          modelId,
          provider,
        })
      );
    }
    if (provider === "xai") {
      const client = createXai({ apiKey });
      // Fire-and-forget: update last used timestamp (ignore errors)
      touchUserApiKey(userId, provider).catch(() => {
        // Ignore errors for fire-and-forget operation
      });
      return await withTelemetrySpan(
        "providers.resolve",
        { attributes: { modelId, path: "user-provider", provider } },
        async () => ({
          model: client(modelId) as unknown as import("ai").LanguageModel,
          modelId,
          provider,
        })
      );
    }
  }

  // Fallback to server-side API keys when BYOK is not available
  // Check in preference order for server-side keys
  const { getServerEnvVarWithFallback } = await import("@/lib/env/server");
  for (const provider of PROVIDER_PREFERENCE) {
    let serverApiKey: string | undefined;
    const modelId = DEFAULT_MODEL_MAPPER(provider, modelHint);

    if (provider === "openai") {
      serverApiKey = getServerEnvVarWithFallback("OPENAI_API_KEY", undefined);
      if (serverApiKey) {
        const openai = createOpenAI({ apiKey: serverApiKey });
        return { model: openai(modelId), modelId, provider };
      }
    }

    if (provider === "openrouter") {
      serverApiKey = getServerEnvVarWithFallback("OPENROUTER_API_KEY", undefined);
      if (serverApiKey) {
        const openrouter = createOpenAI({
          apiKey: serverApiKey,
          // biome-ignore lint/style/useNamingConvention: provider option name
          baseURL: "https://openrouter.ai/api/v1",
        });
        return { model: openrouter(modelId), modelId, provider };
      }
    }

    if (provider === "anthropic") {
      serverApiKey = getServerEnvVarWithFallback("ANTHROPIC_API_KEY", undefined);
      if (serverApiKey) {
        const a = createAnthropic({ apiKey: serverApiKey });
        return { model: a(modelId), modelId, provider };
      }
    }

    if (provider === "xai") {
      serverApiKey = getServerEnvVarWithFallback("XAI_API_KEY", undefined);
      if (serverApiKey) {
        const xai = createXai({ apiKey: serverApiKey });
        return { model: xai(modelId), modelId, provider };
      }
    }
  }

  // Final fallback: Vercel AI Gateway (if configured)
  // Gateway provides unified routing, budgets, retries, and observability
  const allowFallback = await getUserAllowGatewayFallback(userId);
  const gatewayApiKey = getServerEnvVarWithFallback("AI_GATEWAY_API_KEY", undefined);
  if (gatewayApiKey) {
    const gatewayUrl =
      getServerEnvVarWithFallback("AI_GATEWAY_URL", undefined) ??
      "https://ai-gateway.vercel.sh/v1";
    const modelId = DEFAULT_MODEL_MAPPER("openai", modelHint);
    const gateway = createGateway({
      apiKey: gatewayApiKey,
      // biome-ignore lint/style/useNamingConvention: provider option name
      baseURL: gatewayUrl,
    });
    if (allowFallback === false) {
      throw new Error(
        "User has disabled Gateway fallback; no per-user BYOK keys found."
      );
    }
    return await withTelemetrySpan(
      "providers.resolve",
      {
        attributes: {
          baseUrlHost: extractHost(gatewayUrl) ?? "ai-gateway.vercel.sh",
          baseUrlSource: "team",
          modelId,
          path: "team-gateway",
          provider: "gateway",
        },
      },
      async () => ({
        model: gateway(modelId) as unknown as import("ai").LanguageModel,
        modelId,
        provider: "openai",
      })
    );
  }

  throw new Error(
    "No provider key found for user and no server-side fallback keys configured; " +
      "please add a provider API key (BYOK) for one of: openai, openrouter, anthropic, xai, " +
      "or configure server-side fallback keys: OPENAI_API_KEY, OPENROUTER_API_KEY, " +
      "ANTHROPIC_API_KEY, XAI_API_KEY, or AI_GATEWAY_API_KEY."
  );
}

export type { ProviderResolution };
