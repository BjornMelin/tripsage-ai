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
const defaultModelMapper: ModelMapper = (
  provider: ProviderId,
  modelHint?: string
): string => {
  if (!modelHint || modelHint.trim().length === 0) {
    // Sensible defaults per provider
    switch (provider) {
      case "openai":
        return "gpt-4o-mini";
      case "openrouter":
        return "openai/gpt-4o-mini";
      case "anthropic":
        return "claude-3-5-sonnet-20241022";
      case "xai":
        return "grok-3";
      default:
        return "gpt-4o-mini";
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

  // Try providers by preference order and build a model when key found.
  for (const provider of settings.preference) {
    // Fetch user's BYOK for this provider (never exposed to client).
    const apiKey = await getUserApiKey(userId, provider);
    if (!apiKey) continue;

    const modelId = defaultModelMapper(provider, modelHint);

    if (provider === "openai") {
      const openai = createOpenAI({ apiKey });
      return { provider, modelId, model: openai(modelId) };
    }

    if (provider === "openrouter") {
      const headers: Record<string, string> = {};
      const referer = settings.openrouterAttribution?.referer;
      const title = settings.openrouterAttribution?.title;
      if (referer) headers["HTTP-Referer"] = referer;
      if (title) headers["X-Title"] = title;

      const client = createOpenAI({
        apiKey,
        baseURL: "https://openrouter.ai/api/v1",
        headers: Object.keys(headers).length > 0 ? headers : undefined,
      });
      return {
        provider,
        modelId,
        model: client(modelId),
        headers: Object.keys(headers).length ? headers : undefined,
      };
    }

    if (provider === "anthropic") {
      // The anthropic() helper reads env by default; to support BYOK, use factory
      const a = createAnthropic({ apiKey });
      return { provider, modelId, model: a(modelId) };
    }

    if (provider === "xai") {
      // Use OpenAI-compatible provider for xAI to pass BYOK and base URL.
      // Avoid @ai-sdk/xai here to ensure user-specific keys are respected.
      const xai = createOpenAI({ apiKey, baseURL: "https://api.x.ai/v1" });
      return { provider, modelId, model: xai(modelId) };
    }
  }

  throw new Error("No provider key found for user; please add a provider API key.");
}

export type { ProviderResolution };
