import { act, renderHook } from "@testing-library/react";
import type { MockInstance } from "vitest";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { errorService } from "@/lib/error-service";
import { useErrorHandler } from "../use-error-handler";

// Mock the error service
vi.mock("@/lib/error-service", () => ({
  errorService: {
    createErrorReport: vi.fn(),
    reportError: vi.fn(),
  },
}));

// Console spy setup moved to beforeEach to avoid global suppression issues
let consoleSpy: MockInstance;

// Mock sessionStorage - setup in beforeEach to avoid issues in node env
let mockSessionStorage: {
  getItem: ReturnType<typeof vi.fn>;
  setItem: ReturnType<typeof vi.fn>;
};

describe("useErrorHandler", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Setup sessionStorage mock in beforeEach (only in jsdom environment)
    if (typeof window !== "undefined") {
      mockSessionStorage = {
        getItem: vi.fn(),
        setItem: vi.fn(),
      };
      Object.defineProperty(window, "sessionStorage", {
        configurable: true,
        value: mockSessionStorage,
        writable: true,
      });
    }

    // Create fresh spy for each test
    consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {
      // Empty implementation for mocking
    });

    if (mockSessionStorage) {
      mockSessionStorage.getItem.mockClear();
      mockSessionStorage.setItem.mockClear();
    }

    // Mock createErrorReport to return a valid report
    vi.mocked(errorService.createErrorReport).mockReturnValue({
      error: {
        message: "Test error",
        name: "Error",
      },
      timestamp: new Date().toISOString(),
      url: "https://example.com",
      userAgent: "Test User Agent",
    });

    // Mock reportError to return a resolved promise
    vi.mocked(errorService.reportError).mockResolvedValue(undefined);
  });

  afterEach(() => {
    // Restore console after each test
    consoleSpy.mockRestore();
  });

  describe("handleError", () => {
    it("should handle basic error", () => {
      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");

      act(() => {
        result.current.handleError(testError);
      });

      expect(errorService.createErrorReport).toHaveBeenCalledWith(
        testError,
        undefined,
        expect.objectContaining({
          sessionId: expect.any(String),
        })
      );
      expect(errorService.reportError).toHaveBeenCalled();
    });

    it("should handle error with additional info", () => {
      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");
      const additionalInfo = {
        action: "buttonClick",
        component: "TestComponent",
      };

      act(() => {
        result.current.handleError(testError, additionalInfo);
      });

      expect(errorService.createErrorReport).toHaveBeenCalledWith(
        testError,
        undefined,
        expect.objectContaining({
          action: "buttonClick",
          component: "TestComponent",
          sessionId: expect.any(String),
        })
      );
    });

    it("should log error in development mode", () => {
      // Mock the environment check
      const originalEnv = process.env.NODE_ENV;
      vi.stubEnv("NODE_ENV", "development");

      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");
      const additionalInfo = { test: "info" };

      act(() => {
        result.current.handleError(testError, additionalInfo);
      });

      expect(consoleSpy).toHaveBeenCalledWith(
        "Error handled by useErrorHandler:",
        testError,
        additionalInfo
      );

      // Restore original env
      vi.stubEnv("NODE_ENV", originalEnv);
    });

    it("should not log error in production mode", () => {
      // Mock the environment check
      const originalEnv = process.env.NODE_ENV;
      vi.stubEnv("NODE_ENV", "production");

      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");

      act(() => {
        result.current.handleError(testError);
      });

      expect(consoleSpy).not.toHaveBeenCalled();

      // Restore original env
      vi.stubEnv("NODE_ENV", originalEnv);
    });

    it("should generate session ID when not present", () => {
      mockSessionStorage.getItem.mockReturnValue(null);

      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");

      act(() => {
        result.current.handleError(testError);
      });

      expect(mockSessionStorage.setItem).toHaveBeenCalledWith(
        "session_id",
        expect.stringMatching(/^session_[A-Za-z0-9-]+$/)
      );
    });

    it("should use existing session ID", () => {
      mockSessionStorage.getItem.mockReturnValue("existing_session_123");

      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");

      act(() => {
        result.current.handleError(testError);
      });

      expect(errorService.createErrorReport).toHaveBeenCalledWith(
        testError,
        undefined,
        expect.objectContaining({
          sessionId: "existing_session_123",
        })
      );
    });

    it("should handle user store when available", () => {
      (window as Window & { userStore?: { user: { id: string } } }).userStore = {
        user: { id: "test_user_456" },
      };

      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");

      act(() => {
        result.current.handleError(testError);
      });

      expect(errorService.createErrorReport).toHaveBeenCalledWith(
        testError,
        undefined,
        expect.objectContaining({
          userId: "test_user_456",
        })
      );

      // Cleanup
      (window as Window & { userStore?: { user: { id: string } } }).userStore =
        undefined;
    });

    it("should handle missing user store gracefully", () => {
      (window as Window & { userStore?: { user: { id: string } } }).userStore =
        undefined;

      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");

      act(() => {
        result.current.handleError(testError);
      });

      expect(errorService.createErrorReport).toHaveBeenCalledWith(
        testError,
        undefined,
        expect.not.objectContaining({
          userId: expect.anything(),
        })
      );
    });
  });

  describe("handleAsyncError", () => {
    it("should handle successful async operation", async () => {
      const { result } = renderHook(() => useErrorHandler());
      const asyncOperation = vi.fn().mockResolvedValue("success");

      let returnValue: unknown;
      await act(async () => {
        returnValue = await result.current.handleAsyncError(asyncOperation);
      });

      expect(asyncOperation).toHaveBeenCalled();
      expect(returnValue).toBe("success");
      expect(errorService.createErrorReport).not.toHaveBeenCalled();
    });

    it("should handle async operation that throws error", async () => {
      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Async error");
      const asyncOperation = vi.fn().mockRejectedValue(testError);

      await act(async () => {
        try {
          await result.current.handleAsyncError(asyncOperation);
        } catch (error) {
          expect(error).toBe(testError);
        }
      });

      expect(asyncOperation).toHaveBeenCalled();
      expect(errorService.createErrorReport).toHaveBeenCalledWith(
        testError,
        undefined,
        expect.objectContaining({
          context: "async_operation",
          sessionId: expect.any(String),
        })
      );
      expect(errorService.reportError).toHaveBeenCalled();
    });

    it("should call fallback function when error occurs", async () => {
      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Async error");
      const asyncOperation = vi.fn().mockRejectedValue(testError);
      const fallback = vi.fn();

      await act(async () => {
        try {
          await result.current.handleAsyncError(asyncOperation, fallback);
        } catch (_error) {
          // Expected to throw
        }
      });

      expect(fallback).toHaveBeenCalled();
    });

    it("should not call fallback when no error occurs", async () => {
      const { result } = renderHook(() => useErrorHandler());
      const asyncOperation = vi.fn().mockResolvedValue("success");
      const fallback = vi.fn();

      await act(async () => {
        await result.current.handleAsyncError(asyncOperation, fallback);
      });

      expect(fallback).not.toHaveBeenCalled();
    });

    it("should re-throw error after handling", async () => {
      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Async error");
      const asyncOperation = vi.fn().mockRejectedValue(testError);

      await act(async () => {
        await expect(result.current.handleAsyncError(asyncOperation)).rejects.toThrow(
          "Async error"
        );
      });
    });
  });

  describe("hook stability", () => {
    it("should return stable function references", () => {
      const { result, rerender } = renderHook(() => useErrorHandler());

      const firstHandleError = result.current.handleError;
      const firstHandleAsyncError = result.current.handleAsyncError;

      rerender();

      expect(result.current.handleError).toBe(firstHandleError);
      expect(result.current.handleAsyncError).toBe(firstHandleAsyncError);
    });
  });

  describe("error handling edge cases", () => {
    it("should handle sessionStorage errors gracefully", () => {
      mockSessionStorage.getItem.mockImplementation(() => {
        throw new Error("SessionStorage error");
      });

      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");

      act(() => {
        result.current.handleError(testError);
      });

      expect(errorService.createErrorReport).toHaveBeenCalledWith(
        testError,
        undefined,
        expect.not.objectContaining({
          sessionId: expect.anything(),
        })
      );
    });

    it("should handle window access errors gracefully", () => {
      // Mock window.userStore to throw error
      const originalUserStore = window.userStore;
      Object.defineProperty(window, "userStore", {
        configurable: true,
        get: () => {
          throw new Error("Window access error");
        },
      });

      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");

      act(() => {
        result.current.handleError(testError);
      });

      expect(errorService.createErrorReport).toHaveBeenCalled();
      expect(errorService.createErrorReport).toHaveBeenCalledWith(
        testError,
        undefined,
        expect.not.objectContaining({
          userId: expect.anything(),
        })
      );

      // Restore original
      Object.defineProperty(window, "userStore", {
        configurable: true,
        value: originalUserStore,
      });
    });
  });
});
