/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ZodIssue } from "zod";
import { setupReactQueryMocks } from "@/test/mocks/react-query";

setupReactQueryMocks();

const infoSpy = vi.fn();
const errorSpy = vi.fn();

async function loadHelpers() {
  vi.resetModules();
  infoSpy.mockClear();
  errorSpy.mockClear();

  vi.doMock("@/lib/telemetry/logger", () => ({
    createServerLogger: () => ({
      error: errorSpy,
      info: infoSpy,
      warn: vi.fn(),
    }),
  }));

  const mod = await import("@/lib/next/route-helpers");
  return { errorResponse: mod.errorResponse, withRequestSpan: mod.withRequestSpan };
}

describe("withRequestSpan", () => {
  beforeEach(() => {
    infoSpy.mockClear();
    errorSpy.mockClear();
  });

  it("executes function and logs span", async () => {
    const { withRequestSpan } = await loadHelpers();
    const fn = vi.fn().mockResolvedValue("result");

    const result = await withRequestSpan("test.operation", { count: 42 }, fn);

    expect(result).toBe("result");
    expect(fn).toHaveBeenCalledTimes(1);
    expect(infoSpy).toHaveBeenCalledWith(
      "agent.span",
      expect.objectContaining({
        count: 42,
        durationMs: expect.any(Number),
        name: "test.operation",
      })
    );
  });

  it("measures execution duration", async () => {
    const { withRequestSpan } = await loadHelpers();
    const fn = vi.fn().mockResolvedValue("done");

    let calls = 0;
    const hrStub = vi.spyOn(process.hrtime, "bigint").mockImplementation(() => {
      calls += 1;
      return calls === 1 ? BigInt(0) : BigInt(10_000_000); // 10ms
    });

    await withRequestSpan("slow.operation", {}, fn);

    const logged = infoSpy.mock.calls[0]?.[1];
    expect(logged?.durationMs).toBeCloseTo(10, 3);

    hrStub.mockRestore();
  });

  it("logs span when function throws", async () => {
    const { withRequestSpan } = await loadHelpers();
    const fn = vi.fn().mockRejectedValue(new Error("boom"));

    await expect(withRequestSpan("fail", { attr: "t" }, fn)).rejects.toThrow("boom");

    expect(infoSpy).toHaveBeenCalledWith(
      "agent.span",
      expect.objectContaining({ attr: "t", name: "fail" })
    );
  });
});

describe("errorResponse", () => {
  beforeEach(() => {
    infoSpy.mockClear();
    errorSpy.mockClear();
  });

  it("returns standardized error response", async () => {
    const { errorResponse } = await loadHelpers();
    const response = errorResponse({
      error: "invalid_request",
      reason: "Missing required field",
      status: 400,
    });

    expect(response.status).toBe(400);
    expect(response.headers.get("content-type")).toBe("application/json");
  });

  it("includes issues when provided", async () => {
    const { errorResponse } = await loadHelpers();
    const issues: ZodIssue[] = [
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

  it("redacts secrets when logging errors", async () => {
    const { errorResponse } = await loadHelpers();
    const secret = "sk-abcdefghijklmnopqrstuvwxyz123456";
    const err = new Error(`token=${secret}`);

    errorResponse({
      err,
      error: "internal",
      reason: "Server error",
      status: 500,
    });

    expect(errorSpy).toHaveBeenCalledWith(
      "agent.error",
      expect.objectContaining({
        error: "internal",
        reason: "Server error",
      })
    );
    const log = errorSpy.mock.calls[0]?.[1];
    expect((log as { message?: string })?.message).not.toContain(secret);
    expect((log as { message?: string })?.message).toContain("[REDACTED]");
  });

  it("handles non-Error err payloads", async () => {
    const { errorResponse } = await loadHelpers();
    errorResponse({
      err: "string error",
      error: "internal",
      reason: "Unknown error",
      status: 500,
    });
    expect(errorSpy).toHaveBeenCalled();
  });
});
