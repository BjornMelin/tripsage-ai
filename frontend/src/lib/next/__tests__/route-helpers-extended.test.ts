/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { z } from "zod";
import { errorResponse, withRequestSpan } from "@/lib/next/route-helpers";

type ValidationIssue = z.core.$ZodIssue;

describe("withRequestSpan", () => {
  beforeEach(() => {
    vi.spyOn(console, "debug").mockImplementation(() => {
      /* noop */
    });
  });

  it("executes function and logs span", async () => {
    const fn = vi.fn().mockResolvedValue("result");
    const result = await withRequestSpan(
      "test.operation",
      { count: 42, key: "value" },
      fn
    );

    expect(result).toBe("result");
    expect(fn).toHaveBeenCalledTimes(1);
    expect(console.debug).toHaveBeenCalledWith(
      "agent.span",
      expect.objectContaining({
        count: 42,
        durationMs: expect.any(Number),
        key: "value",
        name: "test.operation",
      })
    );
  });

  it("measures execution duration", async () => {
    vi.useFakeTimers();
    const fn = vi.fn().mockResolvedValue("done");

    const promise = withRequestSpan("slow.operation", {}, fn);
    await vi.advanceTimersByTimeAsync(10);
    await promise;

    const call = (console.debug as ReturnType<typeof vi.fn>).mock.calls[0]?.[1];
    expect(call?.durationMs).toBeGreaterThanOrEqual(9);
    vi.useRealTimers();
  });

  it("propagates errors", async () => {
    const error = new Error("Test error");
    const fn = vi.fn().mockRejectedValue(error);

    await expect(withRequestSpan("error.operation", {}, fn)).rejects.toThrow(
      "Test error"
    );

    expect(console.debug).toHaveBeenCalled();
  });

  it("logs span even when function throws", async () => {
    const error = new Error("Boom");
    const fn = vi.fn().mockRejectedValue(error);

    await expect(
      withRequestSpan("failing.operation", { attr: "test" }, fn)
    ).rejects.toThrow();

    expect(console.debug).toHaveBeenCalledWith(
      "agent.span",
      expect.objectContaining({
        attr: "test",
        name: "failing.operation",
      })
    );
  });
});

describe("errorResponse", () => {
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {
      /* noop */
    });
  });

  it("returns standardized error response", () => {
    const response = errorResponse({
      error: "invalid_request",
      reason: "Missing required field",
      status: 400,
    });

    expect(response.status).toBe(400);
    expect(response.headers.get("content-type")).toBe("application/json");
  });

  it("includes error and reason in response body", async () => {
    const response = errorResponse({
      error: "rate_limit_exceeded",
      reason: "Too many requests",
      status: 429,
    });

    const body = await response.json();
    expect(body).toEqual({
      error: "rate_limit_exceeded",
      reason: "Too many requests",
    });
  });

  it("includes issues when provided", async () => {
    const issues: ValidationIssue[] = [
      {
        code: "custom",
        message: "destination is required",
        params: { field: "destination" },
        path: ["destination"],
      },
    ];

    const response = errorResponse({
      error: "invalid_request",
      issues,
      reason: "Request validation failed",
      status: 400,
    });

    const body = await response.json();
    expect(body).toEqual({
      error: "invalid_request",
      issues,
      reason: "Request validation failed",
    });
  });

  it("logs error with redaction when err provided", () => {
    // Use a key that matches the regex pattern sk-[a-zA-Z0-9]{20,}
    const longKey = "sk-abcdefghijklmnopqrstuvwxyz1234567890";
    const error = new Error(`API key: ${longKey}`);
    errorResponse({
      err: error,
      error: "internal",
      reason: "Server error",
      status: 500,
    });

    expect(console.error).toHaveBeenCalledWith(
      "agent.error",
      expect.objectContaining({
        error: "internal",
        reason: "Server error",
      })
    );
    const logCall = (console.error as ReturnType<typeof vi.fn>).mock.calls[0];
    const message = logCall?.[1]?.message as string;
    expect(message).toBeDefined();
    expect(message).toContain("[REDACTED]");
    expect(message).not.toContain(longKey);
  });

  it("does not log when err is not provided", () => {
    errorResponse({
      error: "not_found",
      reason: "Resource not found",
      status: 404,
    });

    expect(console.error).not.toHaveBeenCalled();
  });

  it("redacts sensitive information from error messages", () => {
    const error = new Error("Token: abc123secret");
    errorResponse({
      err: error,
      error: "auth_error",
      reason: "Authentication failed",
      status: 401,
    });

    const logCall = (console.error as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(logCall?.[1]?.message).not.toContain("abc123secret");
    expect(logCall?.[1]?.message).toContain("[REDACTED]");
  });

  it("handles non-Error objects", () => {
    errorResponse({
      err: "string error",
      error: "internal",
      reason: "Unknown error",
      status: 500,
    });

    expect(console.error).toHaveBeenCalled();
  });
});
