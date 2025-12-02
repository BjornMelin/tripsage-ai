/** @vitest-environment node */

import { describe, expect, it } from "vitest";

import { sanitizeToolOutput } from "../message-item";

describe("sanitizeToolOutput", () => {
  it("redacts sensitive keys and truncates long strings", () => {
    const sanitized = sanitizeToolOutput({
      apiKey: "secret-key-1234567890",
      nested: { value: "x".repeat(250) },
      token: "abcdef",
    });

    expect((sanitized as Record<string, unknown>).apiKey).toBe("[REDACTED]");
    expect((sanitized as Record<string, unknown>).token).toBe("[REDACTED]");
    const nested = (sanitized as { nested: { value: string } }).nested.value;
    expect(nested.endsWith("…")).toBe(true);
    expect(nested.length).toBeLessThanOrEqual(201);
  });

  it("truncates strings at exactly 200 characters", () => {
    const longString = "a".repeat(250);
    const sanitized = sanitizeToolOutput({ data: longString });

    const result = (sanitized as { data: string }).data;
    expect(result).toBe(`${"a".repeat(200)}…`);
    expect(result.length).toBe(201);
  });

  it("redacts apiKey and token case-insensitively", () => {
    const sanitized = sanitizeToolOutput({
      ApiKey: "key123",
      apikey: "key789",
      TOKEN: "token456",
    });

    expect((sanitized as Record<string, unknown>).ApiKey).toBe("[REDACTED]");
    expect((sanitized as Record<string, unknown>).TOKEN).toBe("[REDACTED]");
    expect((sanitized as Record<string, unknown>).apikey).toBe("[REDACTED]");
  });

  it("redacts sensitive keys in nested objects", () => {
    const sanitized = sanitizeToolOutput({
      config: {
        apiKey: "secret",
        password: "pass123",
        secret: "shh",
      },
      data: "safe",
    });

    const config = (sanitized as { config: Record<string, unknown> }).config;
    expect(config.apiKey).toBe("[REDACTED]");
    expect(config.password).toBe("[REDACTED]");
    expect(config.secret).toBe("[REDACTED]");
    expect((sanitized as { data: string }).data).toBe("safe");
  });

  it("preserves arrays", () => {
    const sanitized = sanitizeToolOutput({
      items: [1, 2, 3],
      tags: ["a", "b", "c"],
    });

    expect((sanitized as { items: number[] }).items).toEqual([1, 2, 3]);
    expect((sanitized as { tags: string[] }).tags).toEqual(["a", "b", "c"]);
  });

  it("preserves null and undefined", () => {
    const sanitized = sanitizeToolOutput({
      nullValue: null,
      undefinedValue: undefined,
    });

    expect((sanitized as Record<string, unknown>).nullValue).toBeNull();
    expect((sanitized as Record<string, unknown>).undefinedValue).toBeUndefined();
  });
});
