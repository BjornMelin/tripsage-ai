/**
 * @fileoverview API key input validation helpers.
 */

export type ApiKeyValidationResult =
  | { ok: true; apiKey: string }
  | { ok: false; apiKey: string; error: string };

export type ApiKeyService = "openai" | "openrouter" | "anthropic" | "xai";

const DEFAULT_API_KEY_MIN_LENGTH = 20;
const API_KEY_ALLOWED_PATTERN = /^[^\s]+$/;

const OPENAI_PREFIX = "sk-";
const OPENROUTER_PREFIX = "sk-or-";
const ANTHROPIC_PREFIX = "sk-ant-";
const XAI_PREFIX = "xai-";

function getExpectedApiKeyPrefix(service: ApiKeyService): string {
  switch (service) {
    case "anthropic":
      return ANTHROPIC_PREFIX;
    case "openai":
      return OPENAI_PREFIX;
    case "openrouter":
      return OPENROUTER_PREFIX;
    case "xai":
      return XAI_PREFIX;
  }
}

function getPrefixMismatchError(service: ApiKeyService, apiKey: string): string {
  if (service === "openai") {
    if (apiKey.startsWith(OPENROUTER_PREFIX)) {
      return "This looks like an OpenRouter key. Select OpenRouter as the provider.";
    }
    if (apiKey.startsWith(ANTHROPIC_PREFIX)) {
      return "This looks like an Anthropic key. Select Anthropic as the provider.";
    }
    return `OpenAI API keys must start with '${OPENAI_PREFIX}'.`;
  }

  if (service === "openrouter") {
    return `OpenRouter API keys must start with '${OPENROUTER_PREFIX}' (e.g., 'sk-or-v1-...').`;
  }

  const expectedPrefix = getExpectedApiKeyPrefix(service);
  return `${getServiceDisplayName(service)} API keys must start with '${expectedPrefix}'.`;
}

function getServiceDisplayName(service: ApiKeyService): string {
  switch (service) {
    case "anthropic":
      return "Anthropic";
    case "openai":
      return "OpenAI";
    case "openrouter":
      return "OpenRouter";
    case "xai":
      return "xAI";
  }
}

/**
 * Validate a user-provided API key input for basic client-side sanity checks.
 *
 * @param rawApiKey - Raw user input (may include surrounding whitespace).
 * @param options - Optional validation options.
 * @param options.minLength - Minimum length (defaults to DEFAULT_API_KEY_MIN_LENGTH).
 * @param options.service - When provided, performs a lightweight provider-specific prefix check.
 * @returns An ApiKeyValidationResult containing the trimmed apiKey and ok/error fields.
 */
export function validateApiKeyInput(
  rawApiKey: string,
  options?: { minLength?: number; service?: ApiKeyService }
): ApiKeyValidationResult {
  const apiKey = rawApiKey.trim();
  if (apiKey.length === 0) {
    return { apiKey, error: "API key is required.", ok: false };
  }

  const minLength = options?.minLength ?? DEFAULT_API_KEY_MIN_LENGTH;
  if (apiKey.length < minLength) {
    return {
      apiKey,
      error: `API key must be at least ${minLength} characters.`,
      ok: false,
    };
  }

  if (!API_KEY_ALLOWED_PATTERN.test(apiKey)) {
    return { apiKey, error: "API key cannot contain whitespace.", ok: false };
  }

  const service = options?.service;
  if (service) {
    if (service === "openai") {
      const hasWrongProviderPrefix =
        apiKey.startsWith(OPENROUTER_PREFIX) || apiKey.startsWith(ANTHROPIC_PREFIX);
      if (hasWrongProviderPrefix || !apiKey.startsWith(OPENAI_PREFIX)) {
        return { apiKey, error: getPrefixMismatchError(service, apiKey), ok: false };
      }
    } else if (!apiKey.startsWith(getExpectedApiKeyPrefix(service))) {
      return { apiKey, error: getPrefixMismatchError(service, apiKey), ok: false };
    }
  }

  return { apiKey, ok: true };
}
