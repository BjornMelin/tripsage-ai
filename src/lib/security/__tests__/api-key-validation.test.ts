/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { validateApiKeyInput } from "../api-key-validation";

describe("security/api-key-validation", () => {
  it("trims the input and returns ok for a plausible key", () => {
    const result = validateApiKeyInput("  sk-test_1234567890abcdef  ");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.apiKey).toBe("sk-test_1234567890abcdef");
    }
  });

  it("rejects empty input", () => {
    const result = validateApiKeyInput("");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toBe("API key is required.");
    }
  });

  it("rejects whitespace-only input", () => {
    const result = validateApiKeyInput("   ");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toBe("API key is required.");
    }
  });

  it("accepts a key exactly at the minimum length", () => {
    const result = validateApiKeyInput("a".repeat(20), { minLength: 20 });
    expect(result.ok).toBe(true);
  });

  it("rejects keys shorter than the minimum length", () => {
    const result = validateApiKeyInput("short-key", { minLength: 20 });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toBe("API key must be at least 20 characters.");
    }
  });

  it("rejects keys containing spaces", () => {
    const result = validateApiKeyInput("sk-test 1234567890abcdef");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toBe("API key cannot contain whitespace.");
    }
  });

  it("rejects keys containing tabs", () => {
    const result = validateApiKeyInput("sk-test\t1234567890abcdef");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toBe("API key cannot contain whitespace.");
    }
  });

  it("rejects keys containing newlines", () => {
    const result = validateApiKeyInput("sk-test\n1234567890abcdef");
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toBe("API key cannot contain whitespace.");
    }
  });

  it("accepts OpenRouter-formatted keys for the OpenRouter service", () => {
    expect(
      validateApiKeyInput(`sk-or-v1-${"a".repeat(32)}`, { service: "openrouter" }).ok
    ).toBe(true);
  });

  it("accepts Anthropic-formatted keys for the Anthropic service", () => {
    expect(
      validateApiKeyInput(`sk-ant-api03-${"a".repeat(32)}`, { service: "anthropic" }).ok
    ).toBe(true);
  });

  it("accepts OpenAI-formatted keys for the OpenAI service", () => {
    expect(
      validateApiKeyInput(`sk-proj-${"a".repeat(32)}`, { service: "openai" }).ok
    ).toBe(true);
  });

  it("accepts xAI-formatted keys for the xAI service", () => {
    expect(validateApiKeyInput(`xai-${"a".repeat(32)}`, { service: "xai" }).ok).toBe(
      true
    );
  });

  it("rejects an OpenRouter-formatted key when service is OpenAI", () => {
    const result = validateApiKeyInput(`sk-or-v1-${"a".repeat(32)}`, {
      service: "openai",
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toBe(
        "This looks like an OpenRouter key. Select OpenRouter as the provider."
      );
    }
  });

  it("rejects an Anthropic-formatted key when service is OpenAI", () => {
    const result = validateApiKeyInput(`sk-ant-api03-${"a".repeat(32)}`, {
      service: "openai",
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toBe(
        "This looks like an Anthropic key. Select Anthropic as the provider."
      );
    }
  });

  it("rejects an OpenAI-formatted key when service is OpenRouter", () => {
    const result = validateApiKeyInput(`sk-proj-${"a".repeat(32)}`, {
      service: "openrouter",
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toBe(
        "OpenRouter API keys must start with 'sk-or-' (e.g., 'sk-or-v1-...')."
      );
    }
  });

  it("rejects an xAI-formatted key when service is OpenAI", () => {
    const result = validateApiKeyInput(`xai-${"a".repeat(32)}`, { service: "openai" });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toBe("OpenAI API keys must start with 'sk-'.");
    }
  });

  it.each([
    ["anthropic", "Anthropic API keys must start with 'sk-ant-'."],
    ["openai", "OpenAI API keys must start with 'sk-'."],
    [
      "openrouter",
      "OpenRouter API keys must start with 'sk-or-' (e.g., 'sk-or-v1-...').",
    ],
    ["xai", "xAI API keys must start with 'xai-'."],
  ] as const)("rejects invalid key prefixes for %s", (service, expectedError) => {
    const result = validateApiKeyInput(`invalid-${"a".repeat(32)}`, { service });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toBe(expectedError);
    }
  });
});
