/**
 * @fileoverview Provider registry and model resolution for AI SDK v6. Centralizes BYOK key lookup via Supabase RPC and returns a ready LanguageModel for downstream routes (no client-side secrets).
 */

import "server-only";

import {
  DEFAULT_OPENAI_MODEL_ID,
  DEFAULT_OPENROUTER_MODEL_ID,
  DEFAULT_XAI_MODEL_ID,
} from "@ai/models/defaults";
import { createAnthropic } from "@ai-sdk/anthropic";
import { createOpenAI } from "@ai-sdk/openai";
import { createXai } from "@ai-sdk/xai";
import type { ModelMapper, ProviderId, ProviderResolution } from "@schemas/providers";
import { createGateway } from "ai";
import { validateGatewayBaseUrl } from "@/lib/ai/gateway-url";
import {
  getUserAllowGatewayFallback,
  getUserApiKey,
  getUserGatewayBaseUrl,
  touchUserApiKey,
} from "@/lib/supabase/rpc";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";

const providerRegistryLogger = createServerLogger("ai.providers");

/**
 * Provider preference order for BYOK key resolution.
 * Earlier providers in this array take precedence when multiple keys are available.
 */
const PROVIDER_PREFERENCE: ProviderId[] = ["openai", "openrouter", "anthropic", "xai"];

class RejectedGatewayBaseUrlError extends Error {
  constructor(readonly reason: string) {
    super(`Gateway base URL rejected: ${reason}`);
    this.name = "RejectedGatewayBaseUrlError";
  }
}

class MissingExplicitProviderModelError extends Error {
  constructor(provider: ProviderId) {
    super(
      `A model must be selected explicitly for ${provider}; no app-owned default is configured for this provider.`
    );
    this.name = "MissingExplicitProviderModelError";
  }
}

function resolveGatewayBaseUrl(
  rawBaseUrl: string | null | undefined,
  source: "team" | "user"
): { baseUrl?: string; host: string; source: "default" | "team" | "user" } {
  const validation = validateGatewayBaseUrl(rawBaseUrl, { source });
  if (!validation.ok) {
    providerRegistryLogger.warn("gateway_base_url_rejected", {
      reason: validation.reason,
      source,
    });
    throw new RejectedGatewayBaseUrlError(validation.reason);
  }
  return validation;
}

function normalizeGatewayModelId(provider: ProviderId, modelId: string): string {
  const trimmed = modelId.trim();
  if (!trimmed) {
    return `${provider}/${DEFAULT_MODEL_MAPPER(provider)}`;
  }

  // If the caller already provided a provider-qualified id (e.g., "openai/gpt-5.5"),
  // keep it as-is to support direct gateway ids and OpenRouter-style hints.
  if (trimmed.includes("/")) return trimmed;

  return `${provider}/${trimmed}`;
}

function stripProviderPrefix(provider: ProviderId, modelId: string): string {
  const trimmed = modelId.trim();
  if (provider === "openrouter") return trimmed;

  const prefix = `${provider}/`;
  if (trimmed.startsWith(prefix)) {
    return trimmed.slice(prefix.length);
  }
  return trimmed;
}

/**
 * Maps model hints to provider-specific identifiers with sensible defaults.
 *
 * @param provider - The provider identifier.
 * @param modelHint - The model hint to map.
 * @returns The provider-specific model identifier.
 */
const DEFAULT_MODEL_MAPPER: ModelMapper = (
  provider: ProviderId,
  modelHint?: string
): string => {
  const trimmedHint = modelHint?.trim();
  if (!trimmedHint) {
    // Sensible defaults per provider
    switch (provider) {
      case "openai":
        return DEFAULT_OPENAI_MODEL_ID;
      case "openrouter":
        return DEFAULT_OPENROUTER_MODEL_ID;
      case "anthropic":
        throw new MissingExplicitProviderModelError(provider);
      case "xai":
        return DEFAULT_XAI_MODEL_ID;
      default:
        return DEFAULT_XAI_MODEL_ID;
    }
  }
  // For OpenRouter, accept fully-qualified ids like "provider/model"
  if (provider === "openrouter") {
    return trimmedHint;
  }
  // For others, return hint as-is; callers supply proper ids.
  return stripProviderPrefix(provider, trimmedHint);
};

/**
 * Type-asserts and validates that a resolved model is a valid LanguageModel.
 *
 * @param model - The resolved model object from a provider client.
 * @param provider - The provider identifier for error reporting.
 * @param modelId - The model identifier for error reporting.
 * @returns The validated LanguageModel instance.
 * @throws Error if the model is not a valid LanguageModel.
 */
function toLanguageModel(
  model: unknown,
  provider: ProviderId,
  modelId: string
): import("ai").LanguageModel {
  if (!model || (typeof model !== "function" && typeof model !== "object")) {
    throw new Error(
      `Resolved model for ${provider}:${modelId} is not a language model`
    );
  }
  return model as import("ai").LanguageModel;
}

function createByokLanguageModel(
  provider: ProviderId,
  apiKey: string,
  modelId: string
): import("ai").LanguageModel {
  switch (provider) {
    case "openai":
      return createOpenAI({ apiKey }).responses(modelId);
    case "openrouter":
      return createOpenAI({
        apiKey,
        // biome-ignore lint/style/useNamingConvention: provider option name
        baseURL: "https://openrouter.ai/api/v1",
      }).chat(modelId);
    case "anthropic":
      return createAnthropic({ apiKey })(modelId);
    case "xai":
      return createXai({ apiKey })(modelId);
    default: {
      const _exhaustiveCheck: never = provider;
      throw new Error(`Unsupported provider: ${provider}`);
    }
  }
}

function getSafeErrorName(error: unknown): string {
  return error instanceof Error ? error.name : typeof error;
}

/**
 * Resolves a BYOK provider and returns a ready AI SDK model.
 */
async function resolveByokProvider(
  provider: ProviderId,
  apiKey: string,
  modelId: string,
  userId: string
): Promise<ProviderResolution> {
  // Fire-and-forget: update last used timestamp (ignore errors)
  touchUserApiKey(userId, provider).catch((error) => {
    providerRegistryLogger.warn("touch_user_api_key_failed", {
      errorName: getSafeErrorName(error),
      provider,
    });
  });

  return await withTelemetrySpan(
    "providers.resolve",
    { attributes: { modelId, path: "user-provider", provider } },
    async () => ({
      credentialSource: "user-provider",
      model: toLanguageModel(
        createByokLanguageModel(provider, apiKey, modelId),
        provider,
        modelId
      ),
      modelId,
      provider,
    })
  );
}

/**
 * Resolve user's preferred provider and return a ready AI SDK model.
 *
 * @param userId Supabase auth user id; used to fetch BYOK keys server-side.
 * @param modelHint Optional generic model hint (e.g., "gpt-5.5").
 * @returns ProviderResolution including provider id, model id, and model instance.
 * @throws Error if no provider key is found for the user.
 */
export async function resolveProvider(
  userId: string,
  modelHint?: string
): Promise<ProviderResolution> {
  // 0) Per-user Gateway key (if present): highest precedence
  try {
    const userGatewayKey = await getUserApiKey(userId, "gateway");
    if (userGatewayKey) {
      const rawBaseUrl = (await getUserGatewayBaseUrl(userId)) ?? undefined;
      const gatewayBaseUrl = resolveGatewayBaseUrl(rawBaseUrl, "user");

      const client = createGateway({
        apiKey: userGatewayKey,
        ...(gatewayBaseUrl.baseUrl
          ? {
              // biome-ignore lint/style/useNamingConvention: provider option name
              baseURL: gatewayBaseUrl.baseUrl,
            }
          : {}),
      });

      const resolvedModelId = DEFAULT_MODEL_MAPPER("openai", modelHint);
      const modelId = normalizeGatewayModelId("openai", resolvedModelId);
      return await withTelemetrySpan(
        "providers.resolve",
        {
          attributes: {
            baseUrlHost: gatewayBaseUrl.host,
            baseUrlSource: gatewayBaseUrl.source,
            credentialSource: "user-gateway",
            modelId,
            path: "user-gateway",
            provider: "gateway",
          },
        },
        async () => ({
          credentialSource: "user-gateway",
          model: toLanguageModel(client(modelId), "openai", modelId),
          modelId,
          provider: "openai",
        })
      );
    }
  } catch (error) {
    providerRegistryLogger.warn("gateway_lookup_failed", {
      errorName: getSafeErrorName(error),
    });
  }

  // 1) Check for BYOK keys in preference order (OpenAI, OpenRouter, Anthropic, xAI)
  const providers = PROVIDER_PREFERENCE;
  for (const provider of providers) {
    try {
      const apiKey = await getUserApiKey(userId, provider);
      if (apiKey) {
        const modelId = DEFAULT_MODEL_MAPPER(provider, modelHint);
        return await resolveByokProvider(provider, apiKey, modelId, userId);
      }
    } catch (error) {
      if (error instanceof MissingExplicitProviderModelError) {
        throw error;
      }
      providerRegistryLogger.warn("byok_lookup_failed", {
        errorName: getSafeErrorName(error),
        provider,
      });
      if (provider === "openai") {
        throw new Error("OpenAI BYOK lookup failed; refusing Gateway fallback.");
      }
    }
  }

  const { getServerEnvVarWithFallback } = await import("@/lib/env/server");

  // App-owned fallback: Vercel AI Gateway (if configured and allowed).
  // Gateway provides unified routing, budgets, retries, and observability.
  const gatewayApiKey = getServerEnvVarWithFallback("AI_GATEWAY_API_KEY", undefined);
  if (gatewayApiKey) {
    let allowFallback: boolean | null = null;
    try {
      allowFallback = await getUserAllowGatewayFallback(userId);
    } catch (error) {
      providerRegistryLogger.warn("gateway_fallback_preference_lookup_failed", {
        errorName: getSafeErrorName(error),
      });
      allowFallback = null;
    }

    const gatewayUrl = getServerEnvVarWithFallback("AI_GATEWAY_URL", undefined);
    if (allowFallback !== true) {
      throw new Error(
        "User has not enabled Gateway fallback; no per-user BYOK keys found."
      );
    }

    const gatewayBaseUrl = resolveGatewayBaseUrl(gatewayUrl, "team");
    const resolvedModelId = DEFAULT_MODEL_MAPPER("openai", modelHint);
    const modelId = normalizeGatewayModelId("openai", resolvedModelId);

    const gateway = createGateway({
      apiKey: gatewayApiKey,
      ...(gatewayBaseUrl.baseUrl
        ? {
            // biome-ignore lint/style/useNamingConvention: provider option name
            baseURL: gatewayBaseUrl.baseUrl,
          }
        : {}),
    });
    return await withTelemetrySpan(
      "providers.resolve",
      {
        attributes: {
          baseUrlHost: gatewayBaseUrl.host,
          baseUrlSource: gatewayBaseUrl.source,
          credentialSource: "team-gateway",
          modelId,
          path: "team-gateway",
          provider: "gateway",
        },
      },
      async () => ({
        credentialSource: "team-gateway",
        model: toLanguageModel(gateway(modelId), "openai", modelId),
        modelId,
        provider: "openai",
      })
    );
  }

  // Break-glass fallback: direct server-side provider keys. This is intentionally
  // after team Gateway so app-owned traffic keeps Gateway reporting/fallbacks.
  for (const provider of PROVIDER_PREFERENCE) {
    let serverApiKey: string | undefined;
    let modelId: string;
    try {
      modelId = DEFAULT_MODEL_MAPPER(provider, modelHint);
    } catch (error) {
      if (error instanceof MissingExplicitProviderModelError) {
        continue;
      }
      throw error;
    }

    if (provider === "openai") {
      serverApiKey = getServerEnvVarWithFallback("OPENAI_API_KEY", undefined);
    } else if (provider === "openrouter") {
      serverApiKey = getServerEnvVarWithFallback("OPENROUTER_API_KEY", undefined);
    } else if (provider === "anthropic") {
      serverApiKey = getServerEnvVarWithFallback("ANTHROPIC_API_KEY", undefined);
    } else if (provider === "xai") {
      serverApiKey = getServerEnvVarWithFallback("XAI_API_KEY", undefined);
    }

    if (serverApiKey) {
      return await withTelemetrySpan(
        "providers.resolve",
        {
          attributes: {
            credentialSource: "server-provider",
            modelId,
            path: "server-provider",
            provider,
          },
        },
        async () => ({
          credentialSource: "server-provider",
          model: createByokLanguageModel(provider, serverApiKey, modelId),
          modelId,
          provider,
        })
      );
    }
  }

  throw new Error(
    "No provider key found for user and no server-side fallback keys configured; " +
      "please add a provider API key (BYOK) for one of: openai, openrouter, anthropic, xai, " +
      "or configure server-side fallback keys: OPENAI_API_KEY, OPENROUTER_API_KEY, " +
      "ANTHROPIC_API_KEY, XAI_API_KEY, or AI_GATEWAY_API_KEY."
  );
}
