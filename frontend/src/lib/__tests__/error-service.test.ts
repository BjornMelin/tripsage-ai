import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ErrorService } from "../error-service";
import type { ErrorReport, ErrorServiceConfig } from "@/types/errors";

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};
Object.defineProperty(window, "localStorage", {
  value: mockLocalStorage,
});

// Mock sessionStorage
const mockSessionStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};
Object.defineProperty(window, "sessionStorage", {
  value: mockSessionStorage,
});

describe("ErrorService", () => {
  let errorService: ErrorService;
  let mockConfig: ErrorServiceConfig;

  beforeEach(() => {
    mockConfig = {
      enabled: true,
      endpoint: "https://api.example.com/errors",
      apiKey: "test-api-key",
      maxRetries: 2,
      enableLocalStorage: true,
    };

    errorService = new ErrorService(mockConfig);

    // Reset mocks
    vi.clearAllMocks();
    mockFetch.mockClear();
    mockLocalStorage.getItem.mockClear();
    mockLocalStorage.setItem.mockClear();
    mockSessionStorage.getItem.mockClear();
    mockSessionStorage.setItem.mockClear();
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  describe("createErrorReport", () => {
    beforeEach(() => {
      // Mock window.location and navigator
      Object.defineProperty(window, "location", {
        value: { href: "https://example.com/test" },
        writable: true,
      });
      Object.defineProperty(window, "navigator", {
        value: { userAgent: "Test User Agent" },
        writable: true,
      });
    });

    it("should create a basic error report", () => {
      const error = new Error("Test error");
      error.stack = "Error: Test error\n    at test (test.js:1:1)";

      const report = errorService.createErrorReport(error);

      expect(report).toEqual({
        error: {
          name: "Error",
          message: "Test error",
          stack: "Error: Test error\n    at test (test.js:1:1)",
          digest: undefined,
        },
        errorInfo: undefined,
        url: "https://example.com/test",
        userAgent: "Test User Agent",
        timestamp: expect.any(String),
      });

      // Validate timestamp format
      expect(new Date(report.timestamp).toISOString()).toBe(report.timestamp);
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
        userId: "user123",
        sessionId: "session456",
      };

      const report = errorService.createErrorReport(
        error,
        undefined,
        additionalInfo
      );

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
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
      });

      const errorReport: ErrorReport = {
        error: {
          name: "Error",
          message: "Test error",
        },
        url: "https://example.com",
        userAgent: "Test User Agent",
        timestamp: new Date().toISOString(),
      };

      await errorService.reportError(errorReport);

      expect(mockFetch).toHaveBeenCalledWith("https://api.example.com/errors", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-api-key",
        },
        body: JSON.stringify(errorReport),
      });
    });

    it("should not send request when disabled", async () => {
      const disabledService = new ErrorService({
        ...mockConfig,
        enabled: false,
      });
      const consoleErrorSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const errorReport: ErrorReport = {
        error: {
          name: "Error",
          message: "Test error",
        },
        url: "https://example.com",
        userAgent: "Test User Agent",
        timestamp: new Date().toISOString(),
      };

      await disabledService.reportError(errorReport);

      expect(mockFetch).not.toHaveBeenCalled();
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Error reported:",
        errorReport
      );

      consoleErrorSpy.mockRestore();
    });

    it("should store error locally when enabled", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
      });

      mockLocalStorage.getItem.mockReturnValue(null);
      Object.keys(localStorage).length = 0;

      const errorReport: ErrorReport = {
        error: {
          name: "Error",
          message: "Test error",
        },
        url: "https://example.com",
        userAgent: "Test User Agent",
        timestamp: new Date().toISOString(),
      };

      await errorService.reportError(errorReport);

      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        expect.stringMatching(/^error_\d+_[a-z0-9]+$/),
        JSON.stringify(errorReport)
      );
    });

    it("should validate error report with Zod", async () => {
      const consoleErrorSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const invalidErrorReport = {
        error: {
          name: "Error",
          // Missing required message field
        },
        url: "https://example.com",
        userAgent: "Test User Agent",
        timestamp: new Date().toISOString(),
      } as any;

      await errorService.reportError(invalidErrorReport);

      expect(mockFetch).not.toHaveBeenCalled();
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
      mockFetch
        .mockRejectedValueOnce(new Error("Network error"))
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          statusText: "OK",
        });

      const errorReport: ErrorReport = {
        error: {
          name: "Error",
          message: "Test error",
        },
        url: "https://example.com",
        userAgent: "Test User Agent",
        timestamp: new Date().toISOString(),
      };

      const reportPromise = errorService.reportError(errorReport);

      // Fast-forward past the retry delay
      await vi.advanceTimersByTimeAsync(1000);
      await reportPromise;

      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it("should give up after max retries", async () => {
      const consoleErrorSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      // All calls fail
      mockFetch.mockRejectedValue(new Error("Network error"));

      const errorReport: ErrorReport = {
        error: {
          name: "Error",
          message: "Test error",
        },
        url: "https://example.com",
        userAgent: "Test User Agent",
        timestamp: new Date().toISOString(),
      };

      const reportPromise = errorService.reportError(errorReport);

      // Fast-forward past all retry delays
      await vi.advanceTimersByTimeAsync(7000); // Sum of exponential backoff delays
      await reportPromise;

      // Should try initial + 2 retries = 3 total calls
      expect(mockFetch).toHaveBeenCalledTimes(3);
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to send error report after retries:",
        expect.any(Error)
      );

      consoleErrorSpy.mockRestore();
    });
  });

  describe("localStorage cleanup", () => {
    it("should clean up old errors", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        statusText: "OK",
      });

      // Mock 15 existing error keys
      const oldKeys = Array.from({ length: 15 }, (_, i) => `error_${i}_old`);

      Object.defineProperty(mockLocalStorage, "keys", {
        value: () => [...oldKeys, "other_key"],
      });

      // Mock Object.keys to return our test keys
      const originalObjectKeys = Object.keys;
      Object.keys = vi.fn().mockReturnValue([...oldKeys, "other_key"]);

      const errorReport: ErrorReport = {
        error: {
          name: "Error",
          message: "Test error",
        },
        url: "https://example.com",
        userAgent: "Test User Agent",
        timestamp: new Date().toISOString(),
      };

      await errorService.reportError(errorReport);

      // Should remove 5 oldest keys (keep 10 + 1 new = 11 total, but cleanup removes extras)
      expect(mockLocalStorage.removeItem).toHaveBeenCalledTimes(5);

      // Restore Object.keys
      Object.keys = originalObjectKeys;
    });
  });
});
