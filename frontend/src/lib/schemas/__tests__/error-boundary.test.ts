/**
 * @fileoverview Unit tests for error boundary Zod schemas, validating component props,
 * error states, loading states, skeleton configurations, and route error handling
 * with type checking and edge case coverage.
 */

import { describe, expect, it } from "vitest";
import {
  errorBoundaryPropsSchema,
  errorStateSchema,
  globalErrorPropsSchema,
  loadingStateSchema,
  routeErrorPropsSchema,
  skeletonPropsSchema,
} from "../error-boundary";

describe("errorBoundaryPropsSchema", () => {
  it("validates valid props", () => {
    const validProps = {
      children: "test",
      fallback: () => null,
      onError: (error: Error) => console.log(error),
    };

    expect(() => errorBoundaryPropsSchema.parse(validProps)).not.toThrow();
  });

  it("validates minimal props", () => {
    const minimalProps = {
      children: "test",
    };

    expect(() => errorBoundaryPropsSchema.parse(minimalProps)).not.toThrow();
  });
});

describe("errorStateSchema", () => {
  it("validates valid error state", () => {
    const validState = {
      hasError: true,
      error: new Error("Test error"),
      errorInfo: { componentStack: "Component stack" },
    };

    expect(() => errorStateSchema.parse(validState)).not.toThrow();
  });

  it("validates state with null error", () => {
    const stateWithNullError = {
      hasError: false,
      error: null,
      errorInfo: null,
    };

    expect(() => errorStateSchema.parse(stateWithNullError)).not.toThrow();
  });

  it("requires hasError boolean", () => {
    const invalidState = {
      hasError: "true", // should be boolean
      error: null,
      errorInfo: null,
    };

    expect(() => errorStateSchema.parse(invalidState)).toThrow();
  });
});

describe("routeErrorPropsSchema", () => {
  it("validates valid route error props", () => {
    const validProps = {
      error: new Error("Route error"),
      reset: () => {},
    };

    expect(() => routeErrorPropsSchema.parse(validProps)).not.toThrow();
  });

  it("validates error without digest", () => {
    const propsWithoutDigest = {
      error: new Error("Route error"),
      reset: () => {},
    };

    expect(() => routeErrorPropsSchema.parse(propsWithoutDigest)).not.toThrow();
  });

  it("requires reset function", () => {
    const invalidProps = {
      error: {
        name: "Error",
        message: "Route error",
      },
      // missing reset function
    };

    expect(() => routeErrorPropsSchema.parse(invalidProps)).toThrow();
  });
});

describe("globalErrorPropsSchema", () => {
  it("validates valid global error props", () => {
    const validProps = {
      error: new Error("Critical error"),
      reset: () => {},
    };

    expect(() => globalErrorPropsSchema.parse(validProps)).not.toThrow();
  });
});

describe("loadingStateSchema", () => {
  it("accepts minimal valid loading state", () => {
    const validState = {
      isLoading: true,
    };

    expect(() => loadingStateSchema.parse(validState)).not.toThrow();
  });

  it("honors optional fields and defaults", () => {
    const state = {
      isLoading: false,
      loadingText: "Saving",
      showSpinner: false,
    };

    expect(() => loadingStateSchema.parse(state)).not.toThrow();
  });

  it("requires isLoading boolean", () => {
    const invalidState = {
      isLoading: 1, // should be boolean
    };

    expect(() => loadingStateSchema.parse(invalidState)).toThrow();
  });
});

describe("skeletonPropsSchema", () => {
  it("validates valid skeleton props", () => {
    const validProps = {
      className: "custom-class",
      variant: "circular" as const,
      width: "100px",
      height: 50,
      animation: "wave" as const,
    };

    expect(() => skeletonPropsSchema.parse(validProps)).not.toThrow();
  });

  it("validates minimal props", () => {
    const minimalProps = {};
    expect(() => skeletonPropsSchema.parse(minimalProps)).not.toThrow();
  });

  it("validates allowed variants", () => {
    const variants = ["circular", "rectangular", "text"] as const;

    variants.forEach((variant) => {
      const props = { variant };
      expect(() => skeletonPropsSchema.parse(props)).not.toThrow();
    });
  });

  it("rejects invalid variant", () => {
    const invalidProps = { variant: "invalid" } as any;
    expect(() => skeletonPropsSchema.parse(invalidProps)).toThrow();
  });

  it("accepts string and number dimensions", () => {
    const propsWithStringDimensions = { width: "100px", height: "50px" };
    const propsWithNumberDimensions = { width: 100, height: 50 };
    expect(() => skeletonPropsSchema.parse(propsWithStringDimensions)).not.toThrow();
    expect(() => skeletonPropsSchema.parse(propsWithNumberDimensions)).not.toThrow();
  });
});
