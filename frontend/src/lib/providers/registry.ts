/**
 * @fileoverview Provider registry and model resolution for AI SDK v6.
 * Centralizes BYOK key lookup via Supabase RPC and returns a ready
 * LanguageModel for downstream routes (no client-side secrets).
 */
import "server-only";

import { createAnthropic } from "@ai-sdk/anthropic";
import { createOpenAI } from "@ai-sdk/openai";
import type {
  ModelMapper,
  ProviderId,
  ProviderResolution,
} from "@/lib/providers/types";
import { getProviderSettings } from "@/lib/settings";
import { getUserApiKey } from "@/lib/supabase/rpc";

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
        return "x-ai/grok-4-fast";
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
 * @returns ProviderResolution including model and optional headers.
 * @throws Error if no provider key is found for the user.
 */
export async function resolveProvider(
  userId: string,
  modelHint?: string
): Promise<ProviderResolution> {
  const settings = getProviderSettings();

  // Check for BYOK keys first (BYOK users get direct provider access, bypassing Gateway)
  for (const provider of settings.preference) {
    // Fetch user's BYOK for this provider (never exposed to client).
    const apiKey = await getUserApiKey(userId, provider);
    if (!apiKey) continue;

    const modelId = DEFAULT_MODEL_MAPPER(provider, modelHint);

    if (provider === "openai") {
      const openai = createOpenAI({ apiKey });
      return { model: openai(modelId), modelId, provider };
    }

    if (provider === "openrouter") {
      const headers: Record<string, string> = {};
      const referer = settings.openrouterAttribution?.referer;
      const title = settings.openrouterAttribution?.title;
      if (referer) headers["HTTP-Referer"] = referer;
      if (title) headers["X-Title"] = title;

      const client = createOpenAI({
        apiKey,
        // biome-ignore lint/style/useNamingConvention: API parameter name
        baseURL: "https://openrouter.ai/api/v1",
        headers: Object.keys(headers).length > 0 ? headers : undefined,
      });
      return {
        headers: Object.keys(headers).length ? headers : undefined,
        model: client(modelId),
        modelId,
        provider,
      };
    }

    if (provider === "anthropic") {
      // The anthropic() helper reads env by default; to support BYOK, use factory
      const a = createAnthropic({ apiKey });
      return { model: a(modelId), modelId, provider };
    }

    if (provider === "xai") {
      // Use OpenAI-compatible provider for xAI to pass BYOK and base URL.
      // Avoid @ai-sdk/xai here to ensure user-specific keys are respected.
      const xai = createOpenAI({
        apiKey,
        // biome-ignore lint/style/useNamingConvention: API parameter name
        baseURL: "https://api.x.ai/v1",
      });
      return { model: xai(modelId), modelId, provider };
    }
  }

  // Default to Vercel AI Gateway for non-BYOK users (primary/default path per architecture)
  // Gateway provides unified routing, budgets, retries, and observability
  const gatewayApiKey = process.env.AI_GATEWAY_API_KEY;
  if (gatewayApiKey) {
    const modelId = DEFAULT_MODEL_MAPPER("openai", modelHint);
    const gateway = createOpenAI({
      apiKey: gatewayApiKey,
      // biome-ignore lint/style/useNamingConvention: API parameter name
      baseURL: "https://ai-gateway.vercel.sh/v1",
    });
    return {
      model: gateway(modelId),
      modelId,
      provider: "openai",
    };
  }

  throw new Error(
    "No provider key found for user and AI_GATEWAY_API_KEY not configured; " +
      "please add a provider API key for one of the supported providers: " +
      "openai, openrouter, anthropic, xai, or configure AI_GATEWAY_API_KEY."
  );
}

export type { ProviderResolution };
