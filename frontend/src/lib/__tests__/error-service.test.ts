/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ErrorReport, ErrorServiceConfig } from "@/lib/schemas/errors";
import { ErrorService } from "../error-service";

// Mock fetch
const MOCK_FETCH = vi.fn();
global.fetch = MOCK_FETCH;

// Mock localStorage and sessionStorage for node environment
let mockLocalStorage: Storage;
let mockSessionStorage: Storage;

describe("ErrorService", () => {
  let errorService: ErrorService;
  let mockConfig: ErrorServiceConfig;

  beforeEach(() => {
    // Setup storage mocks for node environment
    mockLocalStorage = {
      clear: vi.fn(),
      getItem: vi.fn(),
      key: vi.fn(),
      length: 0,
      removeItem: vi.fn(),
      setItem: vi.fn(),
    } as Storage;
    (globalThis as unknown as { localStorage: Storage }).localStorage =
      mockLocalStorage;

    mockSessionStorage = {
      clear: vi.fn(),
      getItem: vi.fn(),
      key: vi.fn(),
      length: 0,
      removeItem: vi.fn(),
      setItem: vi.fn(),
    } as Storage;
    (globalThis as unknown as { sessionStorage: Storage }).sessionStorage =
      mockSessionStorage;

    // Mock window.location and navigator for node environment
    // ErrorService uses window.location.href and navigator.userAgent directly
    (globalThis as unknown as { window: Window; navigator: Navigator }).window = {
      location: { href: "http://localhost:3000/test" },
    } as unknown as Window;
    (globalThis as unknown as { navigator: Navigator }).navigator = {
      userAgent: "test-user-agent",
    } as unknown as Navigator;

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
    MOCK_FETCH.mockClear();
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
      MOCK_FETCH.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
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

      await errorService.reportError(errorReport);

      expect(MOCK_FETCH).toHaveBeenCalledWith("https://api.example.com/errors", {
        body: JSON.stringify(errorReport),
        headers: {
          Authorization: "Bearer test-api-key",
          "Content-Type": "application/json",
        },
        method: "POST",
      });
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

      expect(MOCK_FETCH).not.toHaveBeenCalled();
      expect(consoleErrorSpy).toHaveBeenCalledWith("Error reported:", errorReport);

      consoleErrorSpy.mockRestore();
    });

    it("should store error locally when enabled", async () => {
      if (!mockLocalStorage) {
        // Skip if not in jsdom environment
        return;
      }

      MOCK_FETCH.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
      });

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

      expect(MOCK_FETCH).not.toHaveBeenCalled();
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
      // First call fails, second succeeds
      MOCK_FETCH.mockRejectedValueOnce(
        new Error("Network error")
      ).mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
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

      const reportPromise = errorService.reportError(errorReport);

      // Fast-forward past the retry delay
      await vi.advanceTimersByTimeAsync(1000);
      await reportPromise;

      expect(MOCK_FETCH).toHaveBeenCalledTimes(2);
    });

    it("should give up after max retries", async () => {
      const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {
        // Suppress console.error during test
      });

      // All calls fail
      MOCK_FETCH.mockRejectedValue(new Error("Network error"));

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
      expect(MOCK_FETCH).toHaveBeenCalledTimes(3);
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

      MOCK_FETCH.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
      });

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
});
