/** @vitest-environment node */

import { agentConfigRequestSchema } from "@schemas/configuration";
import { describe, expect, it } from "vitest";

describe("agentConfigRequestSchema", () => {
  it("accepts current provider-owned model identifiers", () => {
    expect(agentConfigRequestSchema.safeParse({ model: "gpt-5.5" }).success).toBe(true);
    expect(
      agentConfigRequestSchema.safeParse({ model: "openai/gpt-5.5" }).success
    ).toBe(true);
    expect(
      agentConfigRequestSchema.safeParse({
        model: "anthropic/claude-sonnet-4.6",
      }).success
    ).toBe(true);
  });

  it("rejects URLs and whitespace in model identifiers", () => {
    expect(
      agentConfigRequestSchema.safeParse({ model: "https://example.com/model" }).success
    ).toBe(false);
    expect(agentConfigRequestSchema.safeParse({ model: "gpt 5.5" }).success).toBe(
      false
    );
    expect(agentConfigRequestSchema.safeParse({ model: "openai/" }).success).toBe(
      false
    );
    expect(
      agentConfigRequestSchema.safeParse({ model: "openai//gpt-5.5" }).success
    ).toBe(false);
  });

  it("applies OpenAI temperature limits to provider-qualified GPT models", () => {
    const result = agentConfigRequestSchema.safeParse({
      model: "openai/gpt-5.5",
      temperature: 1.75,
    });

    expect(result.success).toBe(false);
  });

  it("accepts step timeout when total timeout is present", () => {
    const result = agentConfigRequestSchema.safeParse({
      stepTimeoutSeconds: 10,
      timeoutSeconds: 30,
    });

    expect(result.success).toBe(true);
  });

  it("rejects step timeout when total timeout is missing", () => {
    const result = agentConfigRequestSchema.safeParse({
      stepTimeoutSeconds: 10,
    });

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toContain("stepTimeoutSeconds");
      expect(result.error.issues[0]?.message).toContain(
        "less than or equal to total timeout"
      );
    }
  });

  it("rejects step timeout greater than total timeout", () => {
    const result = agentConfigRequestSchema.safeParse({
      stepTimeoutSeconds: 40,
      timeoutSeconds: 30,
    });

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues[0]?.path).toContain("stepTimeoutSeconds");
    }
  });

  it("accepts step timeout equal to total timeout", () => {
    const result = agentConfigRequestSchema.safeParse({
      stepTimeoutSeconds: 30,
      timeoutSeconds: 30,
    });

    expect(result.success).toBe(true);
  });

  it("accepts minimum and maximum step timeout bounds", () => {
    const minResult = agentConfigRequestSchema.safeParse({
      stepTimeoutSeconds: 5,
      timeoutSeconds: 5,
    });
    const maxResult = agentConfigRequestSchema.safeParse({
      stepTimeoutSeconds: 300,
      timeoutSeconds: 300,
    });

    expect(minResult.success).toBe(true);
    expect(maxResult.success).toBe(true);
  });

  it("rejects out-of-range step timeout bounds", () => {
    const minResult = agentConfigRequestSchema.safeParse({
      stepTimeoutSeconds: 4,
      timeoutSeconds: 30,
    });
    const maxResult = agentConfigRequestSchema.safeParse({
      stepTimeoutSeconds: 301,
      timeoutSeconds: 301,
    });

    expect(minResult.success).toBe(false);
    expect(maxResult.success).toBe(false);
  });
});
