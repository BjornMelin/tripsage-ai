/**
 * @fileoverview Types for AI provider registry and resolution.
 */
import type { LanguageModel } from "ai";

export type ProviderId = "openai" | "openrouter" | "anthropic" | "xai";

/** Settings for provider resolution and attribution. */
export interface ProviderSettings {
  /** Preference order for provider selection. */
  preference: ProviderId[];
  /** Optional OpenRouter attribution headers. */
  openrouterAttribution?: {
    referer?: string;
    title?: string;
  };
}

/** Result of resolving a model for a user. */
export interface ProviderResolution {
  /** AI SDK LanguageModel, ready to pass to streamText/generateText. */
  model: LanguageModel;
  /** Optional HTTP headers to include on requests (e.g., OpenRouter attribution). */
  headers?: Record<string, string>;
  /** Optional conservative token budget for downstream routing. */
  maxTokens?: number;
  /** Selected provider id. */
  provider: ProviderId;
  /** Resolved model identifier (provider-specific). */
  modelId: string;
}

/** Map a generic model hint to a provider-specific model id. */
export type ModelMapper = (provider: ProviderId, modelHint?: string) => string;
