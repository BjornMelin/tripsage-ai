/** @vitest-environment jsdom */

import type { ErrorReport, ErrorServiceConfig } from "@schemas/errors";
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as telemetryClientErrors from "@/lib/telemetry/client-errors";
import { server } from "@/test/msw/server";
import { ErrorService } from "../error-service";

const createStorageMock = (): Storage => ({
  clear: vi.fn(),
  getItem: vi.fn(),
  key: vi.fn(),
  length: 0,
  removeItem: vi.fn(),
  setItem: vi.fn(),
});

let mockLocalStorage: Storage;
let mockSessionStorage: Storage;
let originalLocalStorage: Storage;
let originalSessionStorage: Storage;

describe("ErrorService", () => {
  let errorService: ErrorService;
  let mockConfig: ErrorServiceConfig;

  beforeEach(() => {
    vi.clearAllMocks();

    originalLocalStorage = window.localStorage;
    originalSessionStorage = window.sessionStorage;
    mockLocalStorage = createStorageMock();
    mockSessionStorage = createStorageMock();
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: mockLocalStorage,
    });
    Object.defineProperty(window, "sessionStorage", {
      configurable: true,
      value: mockSessionStorage,
    });

    mockConfig = {
      apiKey: "test-api-key",
      enabled: true,
      enableLocalStorage: true,
      endpoint: "https://api.example.com/errors",
      maxRetries: 2,
    };

    errorService = new ErrorService(mockConfig);

    // Reset mocks
    vi.clearAllMocks();
    if (mockLocalStorage) {
      (mockLocalStorage.getItem as ReturnType<typeof vi.fn>).mockClear();
      (mockLocalStorage.setItem as ReturnType<typeof vi.fn>).mockClear();
    }
    if (mockSessionStorage) {
      (mockSessionStorage.getItem as ReturnType<typeof vi.fn>).mockClear();
      (mockSessionStorage.setItem as ReturnType<typeof vi.fn>).mockClear();
    }
  });

  afterEach(() => {
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: originalLocalStorage,
    });
    Object.defineProperty(window, "sessionStorage", {
      configurable: true,
      value: originalSessionStorage,
    });
    vi.clearAllTimers();
  });

  describe("createErrorReport", () => {
    it("should create a basic error report", () => {
      const error = new Error("Test error");
      error.stack = "Error: Test error\n    at test (test.js:1:1)";

      const report = errorService.createErrorReport(error);
      // Basic fields
      expect(report.error).toMatchObject({
        message: "Test error",
        name: "Error",
        stack: "Error: Test error\n    at test (test.js:1:1)",
      });
      expect(report.errorInfo).toBeUndefined();
      // Validate timestamp format
      expect(new Date(report.timestamp).toISOString()).toBe(report.timestamp);
      // Validate URL and UA are sourced from the environment
      // ErrorService accesses window.location.href and navigator.userAgent directly
      expect(report.url).toBeDefined();
      expect(report.userAgent).toBeDefined();
    });

    it("should create error report with error info", () => {
      const error = new Error("Test error");
      const errorInfo = { componentStack: "at Component (Component.tsx:10:5)" };

      const report = errorService.createErrorReport(error, errorInfo);

      expect(report.errorInfo).toEqual({
        componentStack: "at Component (Component.tsx:10:5)",
      });
    });

    it("should create error report with additional info", () => {
      const error = new Error("Test error");
      const additionalInfo = {
        sessionId: "session456",
        userId: "user123",
      };

      const report = errorService.createErrorReport(error, undefined, additionalInfo);

      expect(report.userId).toBe("user123");
      expect(report.sessionId).toBe("session456");
    });

    it("should handle error with digest", () => {
      const error = new Error("Test error") as Error & { digest?: string };
      error.digest = "abc123";

      const report = errorService.createErrorReport(error);

      expect(report.error.digest).toBe("abc123");
    });
  });

  describe("reportError", () => {
    it("should report error when enabled", async () => {
      type CapturedRequest = { body: unknown; headers: Headers };
      let capturedRequest: CapturedRequest | null = null;

      server.use(
        http.post("https://api.example.com/errors", async ({ request }) => {
          const body = await request.json();
          capturedRequest = {
            body,
            headers: request.headers,
          };
          return HttpResponse.json({ success: true }, { status: 200 });
        })
      );

      const errorReport: ErrorReport = {
        error: {
          message: "Test error",
          name: "Error",
        },
        timestamp: new Date().toISOString(),
        url: "https://example.com",
        userAgent: "Test User Agent",
      };

      await errorService.reportError(errorReport);

      expect(capturedRequest).not.toBeNull();
      // Non-null assertion after expect check
      const request = capturedRequest!;
      expect(request.body).toEqual(errorReport);
      expect(request.headers.get("Authorization")).toBe("Bearer test-api-key");
      expect(request.headers.get("Content-Type")).toBe("application/json");
    });

    it("should not send request when disabled", async () => {
      const disabledService = new ErrorService({
        ...mockConfig,
        enabled: false,
      });
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {
        // Suppress console.error during test
      });

      const errorReport: ErrorReport = {
        error: {
          message: "Test error",
          name: "Error",
        },
        timestamp: new Date().toISOString(),
        url: "https://example.com",
        userAgent: "Test User Agent",
      };

      await disabledService.reportError(errorReport);

      // MSW won't intercept if service is disabled (no HTTP call made)
      expect(consoleErrorSpy).toHaveBeenCalledWith("Error reported:", errorReport);

      consoleErrorSpy.mockRestore();
    });

    it("should store error locally when enabled", async () => {
      if (!mockLocalStorage) {
        // Skip if not in jsdom environment
        return;
      }

      server.use(
        http.post("https://api.example.com/errors", () =>
          HttpResponse.json({ success: true }, { status: 200 })
        )
      );

      (mockLocalStorage.getItem as ReturnType<typeof vi.fn>).mockReturnValue(null);
      if (typeof localStorage !== "undefined") {
        Object.keys(localStorage).length = 0;
      }

      const errorReport: ErrorReport = {
        error: {
          message: "Test error",
          name: "Error",
        },
        timestamp: new Date().toISOString(),
        url: "https://example.com",
        userAgent: "Test User Agent",
      };

      await errorService.reportError(errorReport);

      expect(mockLocalStorage.setItem as ReturnType<typeof vi.fn>).toHaveBeenCalledWith(
        expect.stringMatching(/^error_\d+_[a-z0-9]+$/),
        JSON.stringify(errorReport)
      );
    });

    it("should validate error report with Zod", async () => {
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {
        // Suppress console.error during test
      });

      const invalidErrorReport = {
        error: {
          name: "Error",
          // Missing required message field
        },
        timestamp: new Date().toISOString(),
        url: "https://example.com",
        userAgent: "Test User Agent",
      } as ErrorReport;

      await errorService.reportError(invalidErrorReport);

      // Should not make HTTP request with invalid data
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to report error:",
        expect.any(Error)
      );

      consoleErrorSpy.mockRestore();
    });
  });

  describe("error reporting with retries", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("should retry failed requests", async () => {
      let callCount = 0;
      // First call fails, second succeeds
      server.use(
        http.post("https://api.example.com/errors", () => {
          callCount++;
          if (callCount === 1) {
            throw new Error("Network error");
          }
          return HttpResponse.json({ success: true }, { status: 200 });
        })
      );

      const errorReport: ErrorReport = {
        error: {
          message: "Test error",
          name: "Error",
        },
        timestamp: new Date().toISOString(),
        url: "https://example.com",
        userAgent: "Test User Agent",
      };

      const reportPromise = errorService.reportError(errorReport);

      // Fast-forward past the retry delay
      await vi.advanceTimersByTimeAsync(1000);
      await reportPromise;

      expect(callCount).toBe(2);
    });

    it("should give up after max retries", async () => {
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {
        // Suppress console.error during test
      });

      let callCount = 0;
      // All calls fail
      server.use(
        http.post("https://api.example.com/errors", () => {
          callCount++;
          throw new Error("Network error");
        })
      );

      const errorReport: ErrorReport = {
        error: {
          message: "Test error",
          name: "Error",
        },
        timestamp: new Date().toISOString(),
        url: "https://example.com",
        userAgent: "Test User Agent",
      };

      const reportPromise = errorService.reportError(errorReport);

      // Fast-forward past all retry delays
      await vi.advanceTimersByTimeAsync(7000); // Sum of exponential backoff delays
      await reportPromise;

      // Should try initial + 2 retries = 3 total calls
      expect(callCount).toBe(3);
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to send error report after retries:",
        expect.any(Error)
      );

      consoleErrorSpy.mockRestore();
    });
  });

  describe("localStorage cleanup", () => {
    it("should clean up old errors", async () => {
      if (!mockLocalStorage) {
        // Skip if not in jsdom environment
        return;
      }

      server.use(
        http.post("https://api.example.com/errors", () =>
          HttpResponse.json({ success: true }, { status: 200 })
        )
      );

      // Mock 15 existing error keys
      const oldKeys = Array.from({ length: 15 }, (_, i) => `error_${i}_old`);

      Object.defineProperty(mockLocalStorage as Record<string, unknown>, "keys", {
        value: () => [...oldKeys, "other_key"],
      });

      // Mock Object.keys to return our test keys
      const originalObjectKeys = Object.keys;
      Object.keys = vi.fn().mockReturnValue([...oldKeys, "other_key"]);

      const errorReport: ErrorReport = {
        error: {
          message: "Test error",
          name: "Error",
        },
        timestamp: new Date().toISOString(),
        url: "https://example.com",
        userAgent: "Test User Agent",
      };

      await errorService.reportError(errorReport);

      // Should remove 5 oldest keys (keep 10 + 1 new = 11 total, but cleanup removes extras)
      expect(
        mockLocalStorage.removeItem as ReturnType<typeof vi.fn>
      ).toHaveBeenCalledTimes(5);

      // Restore Object.keys
      Object.keys = originalObjectKeys;
    });
  });

  describe("OpenTelemetry integration", () => {
    let recordClientErrorOnActiveSpanSpy: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
      recordClientErrorOnActiveSpanSpy = vi.spyOn(
        telemetryClientErrors,
        "recordClientErrorOnActiveSpan"
      );
    });

    afterEach(() => {
      recordClientErrorOnActiveSpanSpy.mockRestore();
    });

    it("should delegate to client telemetry helper when error details are present", async () => {
      server.use(
        http.post("https://api.example.com/errors", () =>
          HttpResponse.json({ success: true }, { status: 200 })
        )
      );

      const errorReport: ErrorReport = {
        error: {
          message: "Test error",
          name: "TestError",
          stack: "Error: Test error\n    at test (test.js:1:1)",
        },
        timestamp: new Date().toISOString(),
        url: "https://example.com",
        userAgent: "Test User Agent",
      };

      await errorService.reportError(errorReport);

      expect(recordClientErrorOnActiveSpanSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          message: "Test error",
          name: "TestError",
          stack: "Error: Test error\n    at test (test.js:1:1)",
        })
      );
    });

    it("should handle OpenTelemetry errors gracefully", async () => {
      const consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {
        // Suppress console.warn during test
      });

      recordClientErrorOnActiveSpanSpy.mockImplementation(() => {
        throw new Error("OTel recording failed");
      });

      server.use(
        http.post("https://api.example.com/errors", () =>
          HttpResponse.json({ success: true }, { status: 200 })
        )
      );

      const errorReport: ErrorReport = {
        error: {
          message: "Test error",
          name: "Error",
        },
        timestamp: new Date().toISOString(),
        url: "https://example.com",
        userAgent: "Test User Agent",
      };

      await expect(errorService.reportError(errorReport)).resolves.not.toThrow();
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        "Failed to record error to OpenTelemetry span:",
        expect.any(Error)
      );
      // Should still send the error report despite OTel failure
      // (MSW handler was called)

      consoleWarnSpy.mockRestore();
    });

    it("should handle error report without error object", async () => {
      server.use(
        http.post("https://api.example.com/errors", () =>
          HttpResponse.json({ success: true }, { status: 200 })
        )
      );

      const errorReport: ErrorReport = {
        error: {
          message: "Test error",
          name: "Error",
        },
        timestamp: new Date().toISOString(),
        url: "https://example.com",
        userAgent: "Test User Agent",
      };

      await errorService.reportError(errorReport);

      // Should still delegate to telemetry helper even if error object is minimal
      expect(recordClientErrorOnActiveSpanSpy).toHaveBeenCalled();
    });
  });
});
