import { describe, expect, it } from "vitest";
import {
  type ErrorDetails,
  ERROR_DETAILS_SCHEMA,
  type ErrorInfo,
  ERROR_INFO_SCHEMA,
  type ErrorReport,
  ERROR_REPORT_SCHEMA,
} from "../errors";

describe("Error Type Schemas", () => {
  describe("ERROR_INFO_SCHEMA", () => {
    it("should validate valid error info", () => {
      const validErrorInfo = {
        componentStack: "at Component (src/Component.tsx:10:5)",
        errorBoundary: "ErrorBoundary",
        errorBoundaryStack: "at ErrorBoundary (src/ErrorBoundary.tsx:25:10)",
      };

      const result = ERROR_INFO_SCHEMA.parse(validErrorInfo);
      expect(result).toEqual(validErrorInfo);
    });

    it("should validate error info with only required fields", () => {
      const minimalErrorInfo = {
        componentStack: "at Component (src/Component.tsx:10:5)",
      };

      const result = ERROR_INFO_SCHEMA.parse(minimalErrorInfo);
      expect(result).toEqual(minimalErrorInfo);
    });

    it("should reject invalid error info", () => {
      const invalidErrorInfo = {
        componentStack: 123, // Should be string
      };

      expect(() => ERROR_INFO_SCHEMA.parse(invalidErrorInfo)).toThrow();
    });
  });

  describe("ERROR_DETAILS_SCHEMA", () => {
    it("should validate valid error details", () => {
      const validErrorDetails = {
        digest: "abc123",
        message: "Cannot read property 'foo' of undefined",
        name: "TypeError",
        stack: "TypeError: Cannot read property 'foo' of undefined\n    at Component",
      };

      const result = ERROR_DETAILS_SCHEMA.parse(validErrorDetails);
      expect(result).toEqual(validErrorDetails);
    });

    it("should validate error details with only required fields", () => {
      const minimalErrorDetails = {
        message: "Something went wrong",
        name: "Error",
      };

      const result = ERROR_DETAILS_SCHEMA.parse(minimalErrorDetails);
      expect(result).toEqual(minimalErrorDetails);
    });

    it("should reject invalid error details", () => {
      const invalidErrorDetails = {
        name: "TypeError",
        // Missing required message field
      };

      expect(() => ERROR_DETAILS_SCHEMA.parse(invalidErrorDetails)).toThrow();
    });
  });

  describe("ERROR_REPORT_SCHEMA", () => {
    it("should validate complete error report", () => {
      const validErrorReport = {
        error: {
          digest: "abc123",
          message: "Cannot read property 'foo' of undefined",
          name: "TypeError",
          stack: "TypeError: Cannot read property 'foo' of undefined\n    at Component",
        },
        errorInfo: {
          componentStack: "at Component (src/Component.tsx:10:5)",
          errorBoundary: "ErrorBoundary",
        },
        sessionId: "session456",
        timestamp: "2024-01-01T00:00:00.000Z",
        url: "https://example.com/dashboard",
        userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        userId: "user123",
      };

      const result = ERROR_REPORT_SCHEMA.parse(validErrorReport);
      expect(result).toEqual(validErrorReport);
    });

    it("should validate minimal error report", () => {
      const minimalErrorReport = {
        error: {
          message: "Something went wrong",
          name: "Error",
        },
        timestamp: "2024-01-01T00:00:00.000Z",
        url: "https://example.com",
        userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      };

      const result = ERROR_REPORT_SCHEMA.parse(minimalErrorReport);
      expect(result).toEqual(minimalErrorReport);
    });

    it("should reject error report with invalid nested objects", () => {
      const invalidErrorReport = {
        error: {
          name: "TypeError",
          // Missing required message field
        },
        timestamp: "2024-01-01T00:00:00.000Z",
        url: "https://example.com",
        userAgent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      };

      expect(() => ERROR_REPORT_SCHEMA.parse(invalidErrorReport)).toThrow();
    });
  });

  describe("Type inference", () => {
    it("should infer correct types", () => {
      // This test ensures TypeScript types are correctly inferred
      const errorInfo: ErrorInfo = {
        componentStack: "at Component",
      };

      const errorDetails: ErrorDetails = {
        message: "Test error",
        name: "Error",
      };

      const errorReport: ErrorReport = {
        error: errorDetails,
        timestamp: "2024-01-01T00:00:00.000Z",
        url: "https://example.com",
        userAgent: "test-agent",
      };

      // If these assignments work without TypeScript errors, the types are correct
      expect(errorInfo.componentStack).toBe("at Component");
      expect(errorDetails.name).toBe("Error");
      expect(errorReport.error).toEqual(errorDetails);
    });
  });
});
