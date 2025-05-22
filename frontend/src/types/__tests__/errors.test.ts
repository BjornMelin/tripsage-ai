import { describe, it, expect } from "vitest";
import { z } from "zod";
import {
  ErrorInfoSchema,
  ErrorDetailsSchema,
  ErrorReportSchema,
  type ErrorInfo,
  type ErrorDetails,
  type ErrorReport,
} from "../errors";

describe("Error Type Schemas", () => {
  describe("ErrorInfoSchema", () => {
    it("should validate valid error info", () => {
      const validErrorInfo = {
        componentStack: "at Component (src/Component.tsx:10:5)",
        errorBoundary: "ErrorBoundary",
        errorBoundaryStack: "at ErrorBoundary (src/ErrorBoundary.tsx:25:10)",
      };

      const result = ErrorInfoSchema.parse(validErrorInfo);
      expect(result).toEqual(validErrorInfo);
    });

    it("should validate error info with only required fields", () => {
      const minimalErrorInfo = {
        componentStack: "at Component (src/Component.tsx:10:5)",
      };

      const result = ErrorInfoSchema.parse(minimalErrorInfo);
      expect(result).toEqual(minimalErrorInfo);
    });

    it("should reject invalid error info", () => {
      const invalidErrorInfo = {
        componentStack: 123, // Should be string
      };

      expect(() => ErrorInfoSchema.parse(invalidErrorInfo)).toThrow();
    });
  });

  describe("ErrorDetailsSchema", () => {
    it("should validate valid error details", () => {
      const validErrorDetails = {
        name: "TypeError",
        message: "Cannot read property 'foo' of undefined",
        stack:
          "TypeError: Cannot read property 'foo' of undefined\n    at Component",
        digest: "abc123",
      };

      const result = ErrorDetailsSchema.parse(validErrorDetails);
      expect(result).toEqual(validErrorDetails);
    });

    it("should validate error details with only required fields", () => {
      const minimalErrorDetails = {
        name: "Error",
        message: "Something went wrong",
      };

      const result = ErrorDetailsSchema.parse(minimalErrorDetails);
      expect(result).toEqual(minimalErrorDetails);
    });

    it("should reject invalid error details", () => {
      const invalidErrorDetails = {
        name: "TypeError",
        // Missing required message field
      };

      expect(() => ErrorDetailsSchema.parse(invalidErrorDetails)).toThrow();
    });
  });

  describe("ErrorReportSchema", () => {
    it("should validate complete error report", () => {
      const validErrorReport = {
        error: {
          name: "TypeError",
          message: "Cannot read property 'foo' of undefined",
          stack:
            "TypeError: Cannot read property 'foo' of undefined\n    at Component",
          digest: "abc123",
        },
        errorInfo: {
          componentStack: "at Component (src/Component.tsx:10:5)",
          errorBoundary: "ErrorBoundary",
        },
        url: "https://example.com/dashboard",
        userAgent:
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        timestamp: "2024-01-01T00:00:00.000Z",
        userId: "user123",
        sessionId: "session456",
      };

      const result = ErrorReportSchema.parse(validErrorReport);
      expect(result).toEqual(validErrorReport);
    });

    it("should validate minimal error report", () => {
      const minimalErrorReport = {
        error: {
          name: "Error",
          message: "Something went wrong",
        },
        url: "https://example.com",
        userAgent:
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        timestamp: "2024-01-01T00:00:00.000Z",
      };

      const result = ErrorReportSchema.parse(minimalErrorReport);
      expect(result).toEqual(minimalErrorReport);
    });

    it("should reject error report with invalid nested objects", () => {
      const invalidErrorReport = {
        error: {
          name: "TypeError",
          // Missing required message field
        },
        url: "https://example.com",
        userAgent:
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        timestamp: "2024-01-01T00:00:00.000Z",
      };

      expect(() => ErrorReportSchema.parse(invalidErrorReport)).toThrow();
    });
  });

  describe("Type inference", () => {
    it("should infer correct types", () => {
      // This test ensures TypeScript types are correctly inferred
      const errorInfo: ErrorInfo = {
        componentStack: "at Component",
      };

      const errorDetails: ErrorDetails = {
        name: "Error",
        message: "Test error",
      };

      const errorReport: ErrorReport = {
        error: errorDetails,
        url: "https://example.com",
        userAgent: "test-agent",
        timestamp: "2024-01-01T00:00:00.000Z",
      };

      // If these assignments work without TypeScript errors, the types are correct
      expect(errorInfo.componentStack).toBe("at Component");
      expect(errorDetails.name).toBe("Error");
      expect(errorReport.error).toEqual(errorDetails);
    });
  });
});
