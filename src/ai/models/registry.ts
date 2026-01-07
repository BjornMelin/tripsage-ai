/**
 * @fileoverview Provider registry and model resolution for AI SDK v6. Centralizes BYOK key lookup via Supabase RPC and returns a ready LanguageModel for downstream routes (no client-side secrets).
 */

import "server-only";

import { createAnthropic } from "@ai-sdk/anthropic";
import { createOpenAI } from "@ai-sdk/openai";
import { createXai } from "@ai-sdk/xai";
import type { ModelMapper, ProviderId, ProviderResolution } from "@schemas/providers";
import { createGateway } from "ai";
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

/**
 * Extracts the host from a URL string.
 *
 * @param url - The URL string to parse.
 * @returns The host portion of the URL, or undefined if parsing fails.
 */
function extractHost(url: string | undefined): string | undefined {
  if (!url) return undefined;
  try {
    return new URL(url).host;
  } catch {
    // ignore parse errors for malformed URLs
    return undefined;
  }
}

type GatewayBaseUrlSource = "default" | "invalid_user_fallback" | "user";

function isPrivateGatewayHost(hostname: string): boolean {
  const host = hostname.toLowerCase();

  if (host === "localhost") return true;
  if (host.endsWith(".local")) return true;

  const ipv4Match = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/u.exec(host);
  if (ipv4Match) {
    const octets = [
      Number(ipv4Match[1]),
      Number(ipv4Match[2]),
      Number(ipv4Match[3]),
      Number(ipv4Match[4]),
    ];
    if (octets.some((octet) => !Number.isInteger(octet) || octet < 0 || octet > 255)) {
      return true;
    }
    const [a, b] = octets;
    if (a === 0 || a === 10 || a === 127) return true;
    if (a === 169 && b === 254) return true;
    if (a === 172 && b >= 16 && b <= 31) return true;
    if (a === 192 && b === 168) return true;
    return false;
  }

  const trimmed = host.replace(/^\[|\]$/gu, "");
  const ipv6 = trimmed.toLowerCase();

  // IPv6 loopback (::1 and fully unabbreviated 0:0:0:0:0:0:0:1 variants)
  if (ipv6 === "::1") return true;
  if (/^(0{1,4}:){7}0*1$/iu.test(ipv6)) return true;

  // Unique local addresses: fc00::/7 (fc00–fdff in the first hextet), case-insensitive
  const firstHextetMatch = /^([0-9a-f]{1,4}):/iu.exec(ipv6);
  if (firstHextetMatch) {
    const firstHextet = Number.parseInt(firstHextetMatch[1], 16);
    if (firstHextet >= 0xfc00 && firstHextet <= 0xfdff) {
      return true;
    }
  }

  // Link-local addresses (fe80::/10) – conservative prefix check on normalized string
  if (ipv6.startsWith("fe80")) return true;

  // IPv4-mapped / embedded IPv4 in IPv6, e.g. ::ffff:10.0.0.1
  if (ipv6.includes(".")) {
    const lastSegment = ipv6.split(":").pop() ?? "";
    const embeddedIpv4Match = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/u.exec(
      lastSegment
    );
    if (embeddedIpv4Match) {
      const a = Number(embeddedIpv4Match[1]);
      const b = Number(embeddedIpv4Match[2]);

      if (
        a === 10 || // 10.0.0.0/8
        (a === 172 && b >= 16 && b <= 31) || // 172.16.0.0 – 172.31.255.255
        (a === 192 && b === 168) || // 192.168.0.0/16
        a === 127 || // 127.0.0.0/8 (loopback)
        (a === 169 && b === 254) // 169.254.0.0/16 (link-local)
      ) {
        return true;
      }
    }
  }

  return false;
}

function resolveGatewayBaseUrl(rawBaseUrl: string | undefined): {
  baseUrl?: string;
  source: GatewayBaseUrlSource;
} {
  if (!rawBaseUrl) {
    return { baseUrl: undefined, source: "default" };
  }

  let parsed: URL;
  try {
    parsed = new URL(rawBaseUrl);
  } catch {
    providerRegistryLogger.warn("gateway_base_url_rejected", { reason: "invalid_url" });
    return { baseUrl: undefined, source: "invalid_user_fallback" };
  }

  if (parsed.protocol !== "https:") {
    providerRegistryLogger.warn("gateway_base_url_rejected", { reason: "non_https" });
    return { baseUrl: undefined, source: "invalid_user_fallback" };
  }

  if (parsed.username || parsed.password) {
    providerRegistryLogger.warn("gateway_base_url_rejected", { reason: "credentials" });
    return { baseUrl: undefined, source: "invalid_user_fallback" };
  }

  if (isPrivateGatewayHost(parsed.hostname)) {
    providerRegistryLogger.warn("gateway_base_url_rejected", {
      reason: "private_host",
    });
    return { baseUrl: undefined, source: "invalid_user_fallback" };
  }

  return { baseUrl: parsed.toString(), source: "user" };
}

function normalizeGatewayModelId(provider: ProviderId, modelId: string): string {
  const trimmed = modelId.trim();
  if (!trimmed) {
    return `${provider}/${DEFAULT_MODEL_MAPPER(provider)}`;
  }

  // If the caller already provided a provider-qualified id (e.g., "openai/gpt-4o-mini"),
  // keep it as-is to support direct gateway ids and OpenRouter-style hints.
  if (trimmed.includes("/")) return trimmed;

  return `${provider}/${trimmed}`;
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
    const rawBaseUrl = (await getUserGatewayBaseUrl(userId)) ?? undefined;
    const { baseUrl, source } = resolveGatewayBaseUrl(rawBaseUrl);

    const client = createGateway({
      apiKey: userGatewayKey,
      ...(baseUrl
        ? {
            // biome-ignore lint/style/useNamingConvention: provider option name
            baseURL: baseUrl,
          }
        : {}),
    });

    const resolvedModelId = DEFAULT_MODEL_MAPPER("openai", modelHint);
    const modelId = normalizeGatewayModelId("openai", resolvedModelId);
    return await withTelemetrySpan(
      "providers.resolve",
      {
        attributes: {
          baseUrlHost: extractHost(baseUrl) ?? "ai-gateway.vercel.sh",
          baseUrlSource: source,
          modelId,
          path: "user-gateway",
          provider: "gateway",
        },
      },
      async () => ({
        model: toLanguageModel(client(modelId), "openai", modelId),
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
      touchUserApiKey(userId, provider).catch((error) => {
        providerRegistryLogger.warn("touch_user_api_key_failed", {
          errorName: error instanceof Error ? error.name : "unknown_error",
          provider,
        });
      });
      return await withTelemetrySpan(
        "providers.resolve",
        { attributes: { modelId, path: "user-provider", provider } },
        async () => ({
          model: toLanguageModel(openai(modelId), provider, modelId),
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
      touchUserApiKey(userId, provider).catch((error) => {
        providerRegistryLogger.warn("touch_user_api_key_failed", {
          errorName: error instanceof Error ? error.name : "unknown_error",
          provider,
        });
      });
      return await withTelemetrySpan(
        "providers.resolve",
        { attributes: { modelId, path: "user-provider", provider } },
        async () => ({
          model: toLanguageModel(openrouter(modelId), provider, modelId),
          modelId,
          provider,
        })
      );
    }
    if (provider === "anthropic") {
      const a = createAnthropic({ apiKey });
      // Fire-and-forget: update last used timestamp (ignore errors)
      touchUserApiKey(userId, provider).catch((error) => {
        providerRegistryLogger.warn("touch_user_api_key_failed", {
          errorName: error instanceof Error ? error.name : "unknown_error",
          provider,
        });
      });
      return await withTelemetrySpan(
        "providers.resolve",
        { attributes: { modelId, path: "user-provider", provider } },
        async () => ({
          model: toLanguageModel(a(modelId), provider, modelId),
          modelId,
          provider,
        })
      );
    }
    if (provider === "xai") {
      const client = createXai({ apiKey });
      // Fire-and-forget: update last used timestamp (ignore errors)
      touchUserApiKey(userId, provider).catch((error) => {
        providerRegistryLogger.warn("touch_user_api_key_failed", {
          errorName: error instanceof Error ? error.name : "unknown_error",
          provider,
        });
      });
      return await withTelemetrySpan(
        "providers.resolve",
        { attributes: { modelId, path: "user-provider", provider } },
        async () => ({
          model: toLanguageModel(client(modelId), provider, modelId),
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
    const gatewayUrl = getServerEnvVarWithFallback("AI_GATEWAY_URL", undefined);
    const resolvedModelId = DEFAULT_MODEL_MAPPER("openai", modelHint);
    const modelId = normalizeGatewayModelId("openai", resolvedModelId);

    const gateway = createGateway({
      apiKey: gatewayApiKey,
      ...(gatewayUrl?.trim()
        ? {
            // biome-ignore lint/style/useNamingConvention: provider option name
            baseURL: gatewayUrl.trim(),
          }
        : {}),
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
        model: toLanguageModel(gateway(modelId), "openai", modelId),
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
