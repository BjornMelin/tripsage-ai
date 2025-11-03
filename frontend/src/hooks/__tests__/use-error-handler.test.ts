import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { errorService } from "@/lib/error-service";
import { useErrorHandler } from "../use-error-handler";

// Mock the error service
vi.mock("@/lib/error-service", () => ({
  errorService: {
    createErrorReport: vi.fn(),
    reportError: vi.fn(),
  },
}));

// Mock console.error
const CONSOLE_ERROR_SPY = vi.spyOn(console, "error").mockImplementation(() => {});

// Mock sessionStorage
const MOCK_SESSION_STORAGE = {
  getItem: vi.fn(),
  setItem: vi.fn(),
};
Object.defineProperty(window, "sessionStorage", {
  value: MOCK_SESSION_STORAGE,
});

describe("useErrorHandler", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    CONSOLE_ERROR_SPY.mockClear();
    MOCK_SESSION_STORAGE.getItem.mockClear();
    MOCK_SESSION_STORAGE.setItem.mockClear();

    // Mock createErrorReport to return a valid report
    (errorService.createErrorReport as any).mockReturnValue({
      error: {
        message: "Test error",
        name: "Error",
      },
      timestamp: new Date().toISOString(),
      url: "https://example.com",
      userAgent: "Test User Agent",
    });

    // Mock reportError to return a resolved promise
    (errorService.reportError as any).mockResolvedValue(undefined);
  });

  describe("handleError", () => {
    it("should handle basic error", async () => {
      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");

      await act(async () => {
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

    it("should handle error with additional info", async () => {
      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");
      const additionalInfo = {
        action: "buttonClick",
        component: "TestComponent",
      };

      await act(async () => {
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

    it("should log error in development mode", async () => {
      // Mock the environment check
      const originalEnv = process.env.NODE_ENV;
      (process.env as any).NODE_ENV = "development";

      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");
      const additionalInfo = { test: "info" };

      await act(async () => {
        result.current.handleError(testError, additionalInfo);
      });

      expect(CONSOLE_ERROR_SPY).toHaveBeenCalledWith(
        "Error handled by useErrorHandler:",
        testError,
        additionalInfo
      );

      // Restore original env
      (process.env as any).NODE_ENV = originalEnv;
    });

    it("should not log error in production mode", async () => {
      // Mock the environment check
      const originalEnv = process.env.NODE_ENV;
      (process.env as any).NODE_ENV = "production";

      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");

      await act(async () => {
        result.current.handleError(testError);
      });

      expect(CONSOLE_ERROR_SPY).not.toHaveBeenCalled();

      // Restore original env
      (process.env as any).NODE_ENV = originalEnv;
    });

    it("should generate session ID when not present", async () => {
      MOCK_SESSION_STORAGE.getItem.mockReturnValue(null);

      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");

      await act(async () => {
        result.current.handleError(testError);
      });

      expect(MOCK_SESSION_STORAGE.setItem).toHaveBeenCalledWith(
        "session_id",
        expect.stringMatching(/^session_\d+_[a-z0-9]+$/)
      );
    });

    it("should use existing session ID", async () => {
      MOCK_SESSION_STORAGE.getItem.mockReturnValue("existing_session_123");

      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");

      await act(async () => {
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

    it("should handle user store when available", async () => {
      (window as any).userStore = {
        user: { id: "test_user_456" },
      };

      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");

      await act(async () => {
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
      (window as any).userStore = undefined;
    });

    it("should handle missing user store gracefully", async () => {
      (window as any).userStore = undefined;

      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");

      await act(async () => {
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

      let returnValue;
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
    it("should handle sessionStorage errors gracefully", async () => {
      MOCK_SESSION_STORAGE.getItem.mockImplementation(() => {
        throw new Error("SessionStorage error");
      });

      const { result } = renderHook(() => useErrorHandler());
      const testError = new Error("Test error");

      await act(async () => {
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

    it("should handle window access errors gracefully", async () => {
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

      await act(async () => {
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
