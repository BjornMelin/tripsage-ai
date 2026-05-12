/**
 * @fileoverview Central model defaults for AI SDK provider resolution.
 */

import { MODEL_PROFILES, type ModelProfileId } from "@/lib/tokens/limits";

/** Re-export canonical model profile definitions and profile id type for provider defaults. */
export { MODEL_PROFILES, type ModelProfileId };

/** Default profile used for cost-conscious app-owned generation. */
export const DEFAULT_MODEL_PROFILE_ID = "standard" satisfies ModelProfileId;

/** Cost-conscious OpenAI default for app-owned standard generation. */
export const DEFAULT_OPENAI_MODEL_ID =
  MODEL_PROFILES[DEFAULT_MODEL_PROFILE_ID].directModelId;

/** Gateway model id format for AI SDK Gateway routing. */
export const DEFAULT_GATEWAY_MODEL_ID =
  MODEL_PROFILES[DEFAULT_MODEL_PROFILE_ID].gatewayModelId;

/** OpenRouter exposes OpenAI models with provider-qualified ids. */
export const DEFAULT_OPENROUTER_MODEL_ID = `openai/${DEFAULT_OPENAI_MODEL_ID}`;

/** xAI default used only when xAI is the resolved BYOK/server provider. */
export const DEFAULT_XAI_MODEL_ID = "grok-4.3";

/** Default model for admin-created planning-agent configurations. */
export const DEFAULT_AGENT_MODEL_ID = MODEL_PROFILES.planning.directModelId;
