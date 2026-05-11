/**
 * @fileoverview Central model defaults for AI SDK provider resolution.
 */

export const MODEL_PROFILES = {
  planning: {
    directModelId: "gpt-5.5",
    gatewayModelId: "openai/gpt-5.5",
    maxContextTokens: 1_000_000,
    maxOutputTokens: 128_000,
  },
  standard: {
    directModelId: "gpt-5.4-mini",
    gatewayModelId: "openai/gpt-5.4-mini",
    maxContextTokens: 400_000,
    maxOutputTokens: 128_000,
  },
  utility: {
    directModelId: "gpt-5.4-nano",
    gatewayModelId: "openai/gpt-5.4-nano",
    maxContextTokens: 400_000,
    maxOutputTokens: 128_000,
  },
} as const;

export type ModelProfileId = keyof typeof MODEL_PROFILES;

export const DEFAULT_MODEL_PROFILE_ID = "standard" satisfies ModelProfileId;

/** Cost-conscious OpenAI default for app-owned standard generation. */
export const DEFAULT_OPENAI_MODEL_ID =
  MODEL_PROFILES[DEFAULT_MODEL_PROFILE_ID].directModelId;

/** Gateway model id format for AI SDK Gateway routing. */
export const DEFAULT_GATEWAY_MODEL_ID =
  MODEL_PROFILES[DEFAULT_MODEL_PROFILE_ID].gatewayModelId;

/** OpenRouter exposes OpenAI models with provider-qualified ids. */
export const DEFAULT_OPENROUTER_MODEL_ID = `openai/${DEFAULT_OPENAI_MODEL_ID}`;

/** Current Anthropic model used only for explicit-key validation examples. */
export const ANTHROPIC_VALIDATION_MODEL_ID = "claude-sonnet-4.6";

/** xAI default used only when xAI is the resolved BYOK/server provider. */
export const DEFAULT_XAI_MODEL_ID = "grok-4.3";

/** Default model for admin-created planning-agent configurations. */
export const DEFAULT_AGENT_MODEL_ID = MODEL_PROFILES.planning.directModelId;
