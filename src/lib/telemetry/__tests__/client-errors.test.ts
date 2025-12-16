/** @vitest-environment node */

import { SpanStatusCode, trace } from "@opentelemetry/api";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { recordClientErrorOnActiveSpan } from "../client-errors";

describe("recordClientErrorOnActiveSpan", () => {
  let mockSpan: {
    recordException: ReturnType<typeof vi.fn>;
    setAttribute: ReturnType<typeof vi.fn>;
    setStatus: ReturnType<typeof vi.fn>;
  };
  let getActiveSpanSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    mockSpan = {
      recordException: vi.fn(),
      setAttribute: vi.fn(),
      setStatus: vi.fn(),
    };

    getActiveSpanSpy = vi
      .spyOn(trace, "getActiveSpan")
      .mockReturnValue(mockSpan as unknown as ReturnType<typeof trace.getActiveSpan>);
  });

  afterEach(() => {
    getActiveSpanSpy.mockRestore();
  });

  it("records exception and marks the active span as error when present", () => {
    const error = new Error("Test error");
    error.name = "TestError";
    error.stack = "Error: Test error\n    at test (test.js:1:1)";

    recordClientErrorOnActiveSpan(error);

    expect(getActiveSpanSpy).toHaveBeenCalled();
    expect(mockSpan.recordException).toHaveBeenCalledTimes(1);
    const [capturedError] = mockSpan.recordException.mock.calls[0] ?? [];
    expect(capturedError).toBeInstanceOf(Error);
    expect((capturedError as Error).name).toBe("TestError");
    expect((capturedError as Error).message).toBe("Test error");
    expect(mockSpan.setStatus).toHaveBeenCalledWith({
      code: SpanStatusCode.ERROR,
      message: "Test error",
    });
  });

  it("is a no-op when there is no active span", () => {
    getActiveSpanSpy.mockReturnValueOnce(
      undefined as unknown as ReturnType<typeof trace.getActiveSpan>
    );

    const error = new Error("Test error");

    expect(() => recordClientErrorOnActiveSpan(error)).not.toThrow();
    expect(mockSpan.recordException).not.toHaveBeenCalled();
    expect(mockSpan.setAttribute).not.toHaveBeenCalled();
    expect(mockSpan.setStatus).not.toHaveBeenCalled();
  });

  it("redacts sensitive metadata keys", () => {
    const error = new Error("Test error");

    recordClientErrorOnActiveSpan(error, {
      context: "SearchForm",
      token: "secret-token",
      userId: "user-123",
    });

    expect(mockSpan.setAttribute).toHaveBeenCalledWith("error.context", "SearchForm");
    expect(mockSpan.setAttribute).toHaveBeenCalledWith("error.token", "[REDACTED]");
    expect(mockSpan.setAttribute).toHaveBeenCalledWith("error.userId", "[REDACTED]");
  });
});
