import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ErrorReport, ErrorServiceConfig } from "@/types/errors";
import { ErrorService } from "../error-service";

// Mock fetch
const MOCK_FETCH = vi.fn();
global.fetch = MOCK_FETCH;

// Mock localStorage
const MOCK_LOCAL_STORAGE = {
  clear: vi.fn(),
  getItem: vi.fn(),
  key: vi.fn(),
  length: 0,
  removeItem: vi.fn(),
  setItem: vi.fn(),
};
Object.defineProperty(window, "localStorage", {
  value: MOCK_LOCAL_STORAGE,
});

// Mock sessionStorage
const MOCK_SESSION_STORAGE = {
  clear: vi.fn(),
  getItem: vi.fn(),
  key: vi.fn(),
  length: 0,
  removeItem: vi.fn(),
  setItem: vi.fn(),
};
Object.defineProperty(window, "sessionStorage", {
  value: MOCK_SESSION_STORAGE,
});

describe("ErrorService", () => {
  let errorService: ErrorService;
  let mockConfig: ErrorServiceConfig;

  beforeEach(() => {
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
    MOCK_LOCAL_STORAGE.getItem.mockClear();
    MOCK_LOCAL_STORAGE.setItem.mockClear();
    MOCK_SESSION_STORAGE.getItem.mockClear();
    MOCK_SESSION_STORAGE.setItem.mockClear();
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  describe("createErrorReport", () => {
    // Use JSDOM-provided window.location and navigator to avoid redefining
    // non-configurable properties under vmThreads pool.

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
      expect(report.url).toBe(window.location.href);
      expect(report.userAgent).toBe(window.navigator.userAgent);
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
      MOCK_FETCH.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
      });

      MOCK_LOCAL_STORAGE.getItem.mockReturnValue(null);
      Object.keys(localStorage).length = 0;

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

      expect(MOCK_LOCAL_STORAGE.setItem).toHaveBeenCalledWith(
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
      MOCK_FETCH.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
      });

      // Mock 15 existing error keys
      const oldKeys = Array.from({ length: 15 }, (_, i) => `error_${i}_old`);

      Object.defineProperty(MOCK_LOCAL_STORAGE, "keys", {
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
      expect(MOCK_LOCAL_STORAGE.removeItem).toHaveBeenCalledTimes(5);

      // Restore Object.keys
      Object.keys = originalObjectKeys;
    });
  });
});
