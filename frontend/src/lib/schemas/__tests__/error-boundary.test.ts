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
      error: {
        name: "Error",
        message: "Test error",
        stack: "Error stack",
        digest: "abc123",
      },
      errorInfo: {
        componentStack: "Component stack",
      },
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
      error: {
        name: "Error",
        message: "Route error",
        digest: "def456",
      },
      reset: () => {},
    };

    expect(() => routeErrorPropsSchema.parse(validProps)).not.toThrow();
  });

  it("validates error without digest", () => {
    const propsWithoutDigest = {
      error: {
        name: "Error",
        message: "Route error",
      },
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
      error: {
        name: "Global Error",
        message: "Critical error",
        digest: "ghi789",
      },
      reset: () => {},
    };

    expect(() => globalErrorPropsSchema.parse(validProps)).not.toThrow();
  });
});

describe("loadingStateSchema", () => {
  it("validates valid loading state", () => {
    const validState = {
      isLoading: true,
      error: null,
      data: { test: "data" },
    };

    expect(() => loadingStateSchema.parse(validState)).not.toThrow();
  });

  it("validates loading state with error", () => {
    const stateWithError = {
      isLoading: false,
      error: "Failed to load",
      data: null,
    };

    expect(() => loadingStateSchema.parse(stateWithError)).not.toThrow();
  });

  it("requires isLoading boolean", () => {
    const invalidState = {
      isLoading: 1, // should be boolean
      error: null,
      data: null,
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
      count: 3,
    };

    expect(() => skeletonPropsSchema.parse(validProps)).not.toThrow();
  });

  it("validates minimal props", () => {
    const minimalProps = {};

    expect(() => skeletonPropsSchema.parse(minimalProps)).not.toThrow();
  });

  it("validates valid variants", () => {
    const variants = ["default", "circular", "rectangular", "text"] as const;

    variants.forEach((variant) => {
      const props = { variant };
      expect(() => skeletonPropsSchema.parse(props)).not.toThrow();
    });
  });

  it("rejects invalid variant", () => {
    const invalidProps = {
      variant: "invalid",
    };

    expect(() => skeletonPropsSchema.parse(invalidProps)).toThrow();
  });

  it("validates count range", () => {
    // Valid counts
    expect(() => skeletonPropsSchema.parse({ count: 1 })).not.toThrow();
    expect(() => skeletonPropsSchema.parse({ count: 10 })).not.toThrow();
    expect(() => skeletonPropsSchema.parse({ count: 20 })).not.toThrow();

    // Invalid counts
    expect(() => skeletonPropsSchema.parse({ count: 0 })).toThrow();
    expect(() => skeletonPropsSchema.parse({ count: 21 })).toThrow();
    expect(() => skeletonPropsSchema.parse({ count: -1 })).toThrow();
  });

  it("accepts string and number dimensions", () => {
    const propsWithStringDimensions = {
      width: "100px",
      height: "50px",
    };

    const propsWithNumberDimensions = {
      width: 100,
      height: 50,
    };

    expect(() => skeletonPropsSchema.parse(propsWithStringDimensions)).not.toThrow();
    expect(() => skeletonPropsSchema.parse(propsWithNumberDimensions)).not.toThrow();
  });
});
