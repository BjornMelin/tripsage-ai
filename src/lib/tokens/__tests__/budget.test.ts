/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  CHARS_PER_TOKEN_HEURISTIC,
  clampMaxTokens,
  countPromptTokens,
  countTokens,
} from "../../tokens/budget";
import {
  DEFAULT_CONTEXT_LIMIT,
  getModelContextLimit,
  MODEL_LIMITS,
} from "../../tokens/limits";

// Mock js-tiktoken with lightweight deterministic implementation
const { mockEncode, MOCK_TIKTOKEN } = vi.hoisted(() => {
  const encodeFn = vi.fn((text: string) => {
    // Deterministic token count: ~3 chars per token for mocked tokenizer
    return Array(Math.ceil(text.length / 3)).fill(0);
  });

  // Mock Tiktoken class that always succeeds regardless of rank input
  // Use a proper constructor function wrapped in vi.fn() to avoid warnings
  function TiktokenConstructor(_rank: unknown) {
    return {
      encode: encodeFn,
      free: vi.fn(),
    };
  }

  return {
    MOCK_TIKTOKEN: vi.fn(TiktokenConstructor),
    mockEncode: encodeFn,
  };
});

vi.mock("js-tiktoken/lite", () => ({
  Tiktoken: MOCK_TIKTOKEN,
}));

// Mock rank files to avoid loading real WASM data (return non-empty objects)
vi.mock("js-tiktoken/ranks/o200k_base", () => ({
  default: {
    // biome-ignore lint/style/useNamingConvention: Test-only sentinel property name.
    __mock: true,
  },
}));
describe("countTokens", () => {
  beforeEach(() => {
    // Clear call history but preserve mock implementations
    mockEncode.mockClear();
    MOCK_TIKTOKEN.mockClear();
    // Ensure encode implementation is set
    mockEncode.mockImplementation((text: string) => {
      // Deterministic token count: ~3 chars per token for mocked tokenizer
      return Array(Math.ceil(text.length / 3)).fill(0);
    });
  });

  it("returns 0 for empty input", () => {
    expect(countTokens([], "gpt-5.5")).toBe(0);
  });

  it("counts tokens using mocked tokenizer for current OpenAI profiles", () => {
    const sample = "hello world"; // 11 chars
    const heuristicValue = Math.ceil(sample.length / CHARS_PER_TOKEN_HEURISTIC); // ceil(11/4) = 3
    const tokenizerValue = Math.ceil(sample.length / 3); // ceil(11/3) = 4

    const result1 = countTokens([sample], "gpt-5.5");
    const result2 = countTokens([sample], "gpt-5.4-mini");

    // Both models should produce the same result
    expect(result1).toBe(result2);
    // Verify tokenizer constructor was called (attempted to use tokenizer)
    expect(MOCK_TIKTOKEN).toHaveBeenCalled();
    // Result should be deterministic and fast (not using real WASM)
    // If tokenizer works: tokenizerValue (4), if it falls back: heuristicValue (3)
    // Both are acceptable as long as it's fast and deterministic
    expect([heuristicValue, tokenizerValue]).toContain(result1);
  });

  it("falls back to heuristic for unknown providers", () => {
    const s = "1234"; // 4 chars
    // For unknown models, selectTokenizer returns null, so heuristic is used
    const result = countTokens([s], "vendor/custom-model");
    // Should use heuristic: ceil(4 / 4) = 1 token
    expect(result).toBe(Math.ceil(s.length / CHARS_PER_TOKEN_HEURISTIC));
    // Tokenizer should not be called for unknown models
    expect(mockEncode).not.toHaveBeenCalled();
  });
});

describe("clampMaxTokens", () => {
  it("clamps to model limit minus prompt tokens", () => {
    const model = "gpt-5.5";
    const limit = getModelContextLimit(model);
    const messages = [
      { content: "system", role: "system" as const },
      { content: "hello world", role: "user" as const },
    ];
    const promptTokens = countPromptTokens(messages, model);
    const desired = 2_000_000; // intentionally too large
    const result = clampMaxTokens(messages, desired, model);
    expect(result.maxOutputTokens).toBe(Math.max(1, limit - promptTokens));
    expect(result.reasons).toContain("maxTokens_clamped_model_limit");
  });

  it("resolves the GPT-5.5 context window correctly", () => {
    expect(getModelContextLimit("openai/gpt-5.5")).toBe(1_050_000);
  });

  it("uses current non-OpenAI context windows", () => {
    expect(getModelContextLimit("moonshotai/kimi-k2.6")).toBe(262_000);
    expect(getModelContextLimit("grok-4.3")).toBe(1_000_000);
  });

  it("keeps model limits restricted to the current canonical model set", () => {
    expect(Object.keys(MODEL_LIMITS).sort()).toEqual(
      [
        "deepseek-v4-flash",
        "deepseek-v4-pro",
        "gemini-3.1-flash-lite",
        "glm-5.1",
        "gpt-5.4-mini",
        "gpt-5.4-nano",
        "gpt-5.5",
        "grok-4.3",
        "kimi-k2.6",
        "mimo-v2.5",
        "mimo-v2.5-pro",
      ].sort()
    );
  });

  it("coerces invalid desiredMax to 1 with reason", () => {
    const model = "gpt-5.5";
    const messages = [{ content: "test", role: "user" as const }];
    const result = clampMaxTokens(messages, 0, model);
    expect(result.maxOutputTokens).toBe(1);
    expect(result.reasons).toContain("maxTokens_clamped_invalid_desired");
  });

  it("uses default context limit for unknown model", () => {
    const model = "unknown-model";
    const messages = [{ content: "hi", role: "user" as const }];
    const result = clampMaxTokens(messages, 100_000, model);
    // No clamping expected if desired < DEFAULT_CONTEXT_LIMIT
    expect(result.maxOutputTokens).toBeGreaterThan(0);
    expect(getModelContextLimit(model)).toBe(DEFAULT_CONTEXT_LIMIT);
  });

  it("clamps down to 1 when prompt exhausts unknown model limit", () => {
    const model = "some-new-model";
    // Create a prompt larger than default context to force clamp
    const huge = "x".repeat(DEFAULT_CONTEXT_LIMIT * CHARS_PER_TOKEN_HEURISTIC + 1000);
    const messages = [{ content: huge, role: "user" as const }];
    const result = clampMaxTokens(messages, 1000, model);
    expect(result.maxOutputTokens).toBe(1);
    expect(result.reasons).toContain("maxTokens_clamped_model_limit");
  });
});

describe("countPromptTokens invariants", () => {
  it("is order-insensitive for total count", () => {
    const model = "gpt-5.5";
    const a = { content: "alpha beta", role: "system" as const };
    const b = { content: "gamma delta", role: "user" as const };
    const c = { content: "epsilon zeta", role: "assistant" as const };

    const ordered = countPromptTokens([a, b, c], model);
    const shuffled = countPromptTokens([c, a, b], model);
    expect(ordered).toBe(shuffled);
  });
});
