/**
 * @fileoverview Vitest: token counting and clamping edge cases.
 */

import { Tiktoken } from "js-tiktoken/lite";
import o200kBase from "js-tiktoken/ranks/o200k_base";
import { describe, expect, it } from "vitest";

import {
  CHARS_PER_TOKEN_HEURISTIC,
  clampMaxTokens,
  countPromptTokens,
  countTokens,
} from "../../tokens/budget";
import { DEFAULT_CONTEXT_LIMIT, getModelContextLimit } from "../../tokens/limits";

describe("countTokens", () => {
  it("returns 0 for empty input", () => {
    expect(countTokens([], "gpt-4o")).toBe(0);
  });

  it("counts tokens using o200k_base for gpt-4o/gpt-5 families", () => {
    const enc = new Tiktoken(o200kBase);
    const sample = "hello world";
    const expected = enc.encode(sample).length;
    expect(countTokens([sample], "gpt-4o")).toBe(expected);
    expect(countTokens([sample], "gpt-5-mini")).toBe(expected);
  });

  it("falls back to heuristic for unknown providers", () => {
    const s = "1234";
    // 4 chars → 1 token under heuristic
    expect(countTokens([s], "claude-3.5-sonnet")).toBe(
      Math.ceil(s.length / CHARS_PER_TOKEN_HEURISTIC)
    );
  });
});

describe("clampMaxTokens", () => {
  it("clamps to model limit minus prompt tokens", () => {
    const model = "gpt-4o";
    const limit = getModelContextLimit(model);
    const messages = [
      { content: "system", role: "system" as const },
      { content: "hello world", role: "user" as const },
    ];
    const promptTokens = countPromptTokens(messages, model);
    const desired = 999_999; // intentionally too large
    const result = clampMaxTokens(messages, desired, model);
    expect(result.maxTokens).toBe(Math.max(1, limit - promptTokens));
    expect(result.reasons).toContain("maxTokens_clamped_model_limit");
  });

  it("coerces invalid desiredMax to 1 with reason", () => {
    const model = "gpt-4o";
    const messages = [{ content: "test", role: "user" as const }];
    const result = clampMaxTokens(messages, 0, model);
    expect(result.maxTokens).toBe(1);
    expect(result.reasons).toContain("maxTokens_clamped_invalid_desired");
  });

  it("uses default context limit for unknown model", () => {
    const model = "unknown-model";
    const messages = [{ content: "hi", role: "user" as const }];
    const result = clampMaxTokens(messages, 100_000, model);
    // No clamping expected if desired < DEFAULT_CONTEXT_LIMIT
    expect(result.maxTokens).toBeGreaterThan(0);
    expect(getModelContextLimit(model)).toBe(DEFAULT_CONTEXT_LIMIT);
  });

  it("clamps down to 1 when prompt exhausts unknown model limit", () => {
    const model = "some-new-model";
    // Create a prompt larger than default context to force clamp
    const huge = "x".repeat(DEFAULT_CONTEXT_LIMIT * CHARS_PER_TOKEN_HEURISTIC + 1000);
    const messages = [{ content: huge, role: "user" as const }];
    const result = clampMaxTokens(messages, 1000, model);
    expect(result.maxTokens).toBe(1);
    expect(result.reasons).toContain("maxTokens_clamped_model_limit");
  });
});

describe("countPromptTokens invariants", () => {
  it("is order-insensitive for total count", () => {
    const model = "gpt-4o";
    const a = { content: "alpha beta", role: "system" as const };
    const b = { content: "gamma delta", role: "user" as const };
    const c = { content: "epsilon zeta", role: "assistant" as const };

    const ordered = countPromptTokens([a, b, c], model);
    const shuffled = countPromptTokens([c, a, b], model);
    expect(ordered).toBe(shuffled);
  });
});
