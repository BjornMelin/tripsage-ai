import {
  errorBoundarySchema as errorBoundaryPropsSchema,
  errorStateSchema,
  globalErrorPropsSchema,
  errorLoadingStateSchema as loadingStateSchema,
  routeErrorPropsSchema,
  errorSkeletonPropsSchema as skeletonPropsSchema,
} from "@schemas/ui/error-boundary";
import { describe, expect, it } from "vitest";

describe("errorBoundaryPropsSchema", () => {
  it.concurrent("validates valid props", () => {
    const validProps = {
      children: "test",
      fallback: () => null,
      onError: (error: Error) => console.log(error),
    };

    expect(() => errorBoundaryPropsSchema.parse(validProps)).not.toThrow();
  });

  it.concurrent("validates minimal props", () => {
    const minimalProps = {
      children: "test",
    };

    expect(() => errorBoundaryPropsSchema.parse(minimalProps)).not.toThrow();
  });
});

describe("errorStateSchema", () => {
  it.concurrent("validates valid error state", () => {
    const validState = {
      error: new Error("Test error"),
      errorInfo: { componentStack: "Component stack" },
      hasError: true,
    };

    expect(() => errorStateSchema.parse(validState)).not.toThrow();
  });

  it.concurrent("validates state with null error", () => {
    const stateWithNullError = {
      error: null,
      errorInfo: null,
      hasError: false,
    };

    expect(() => errorStateSchema.parse(stateWithNullError)).not.toThrow();
  });

  it.concurrent("requires hasError boolean", () => {
    const invalidState = {
      error: null,
      errorInfo: null,
      hasError: "true", // should be boolean
    };

    expect(() => errorStateSchema.parse(invalidState)).toThrow();
  });
});

describe("routeErrorPropsSchema", () => {
  it.concurrent("validates valid route error props", () => {
    const validProps = {
      error: new Error("Route error"),
      reset: () => {
        // Empty reset function for test
      },
    };

    expect(() => routeErrorPropsSchema.parse(validProps)).not.toThrow();
  });

  it.concurrent("validates error without digest", () => {
    const propsWithoutDigest = {
      error: new Error("Route error"),
      reset: () => {
        // Empty reset function for test
      },
    };

    expect(() => routeErrorPropsSchema.parse(propsWithoutDigest)).not.toThrow();
  });

  it.concurrent("requires reset function", () => {
    const invalidProps = {
      error: {
        message: "Route error",
        name: "Error",
      },
      // missing reset function
    };

    expect(() => routeErrorPropsSchema.parse(invalidProps)).toThrow();
  });
});

describe("globalErrorPropsSchema", () => {
  it.concurrent("validates valid global error props", () => {
    const validProps = {
      error: new Error("Critical error"),
      reset: () => {
        // Empty reset function for test
      },
    };

    expect(() => globalErrorPropsSchema.parse(validProps)).not.toThrow();
  });
});

describe("loadingStateSchema", () => {
  it.concurrent("accepts minimal valid loading state", () => {
    const validState = {
      isLoading: true,
    };

    expect(() => loadingStateSchema.parse(validState)).not.toThrow();
  });

  it.concurrent("honors optional fields and defaults", () => {
    const state = {
      isLoading: false,
      loadingText: "Saving",
      showSpinner: false,
    };

    expect(() => loadingStateSchema.parse(state)).not.toThrow();
  });

  it.concurrent("requires isLoading boolean", () => {
    const invalidState = {
      isLoading: 1, // should be boolean
    };

    expect(() => loadingStateSchema.parse(invalidState)).toThrow();
  });
});

describe("skeletonPropsSchema", () => {
  it.concurrent("validates valid skeleton props", () => {
    const validProps = {
      animation: "wave" as const,
      className: "custom-class",
      height: 50,
      variant: "circular" as const,
      width: "100px",
    };

    expect(() => skeletonPropsSchema.parse(validProps)).not.toThrow();
  });

  it.concurrent("validates minimal props", () => {
    const minimalProps = {};
    expect(() => skeletonPropsSchema.parse(minimalProps)).not.toThrow();
  });

  it.concurrent("validates allowed variants", () => {
    const variants = ["circular", "rectangular", "text"] as const;

    variants.forEach((variant) => {
      const props = { variant };
      expect(() => skeletonPropsSchema.parse(props)).not.toThrow();
    });
  });

  it.concurrent("rejects invalid variant", () => {
    const invalidProps = { variant: "invalid" } as { variant: string };
    expect(() => skeletonPropsSchema.parse(invalidProps)).toThrow();
  });

  it.concurrent("accepts string and number dimensions", () => {
    const propsWithStringDimensions = { height: "50px", width: "100px" };
    const propsWithNumberDimensions = { height: 50, width: 100 };
    expect(() => skeletonPropsSchema.parse(propsWithStringDimensions)).not.toThrow();
    expect(() => skeletonPropsSchema.parse(propsWithNumberDimensions)).not.toThrow();
  });
});
