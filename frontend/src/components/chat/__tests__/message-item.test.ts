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
});
