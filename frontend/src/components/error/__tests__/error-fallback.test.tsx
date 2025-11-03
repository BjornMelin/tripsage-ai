/**
 * @fileoverview Unit tests for ErrorFallback component, covering default UI,
 * error message display, button functionality, and accessibility features.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  ErrorFallback,
  MinimalErrorFallback,
  PageErrorFallback,
} from "../error-fallback";

/** Mock lucide-react icons */
vi.mock("lucide-react", () => ({
  // biome-ignore lint/style/useNamingConvention: React component names from lucide-react library
  AlertTriangle: () => <div data-testid="alert-triangle-icon" />,
  Bug: () => <div data-testid="bug-icon" />,
  Home: () => <div data-testid="home-icon" />,
  RefreshCw: () => <div data-testid="refresh-icon" />,
}));

/** Mock window.location */
const MockLocation = {
  href: "",
  reload: vi.fn(),
};
Object.defineProperty(window, "location", {
  value: MockLocation,
  writable: true,
});

/** Test suite for ErrorFallback component */
describe("Error Fallback Components", () => {
  const mockError = new Error("Test error message") as Error & {
    digest?: string;
  };
  const mockReset = vi.fn();
  const mockRetry = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    MockLocation.reload.mockClear();
    MockLocation.href = "";
  });

  /** Test suite for ErrorFallback component */
  describe("ErrorFallback", () => {
    /** Test that the default error fallback UI is rendered */
    it("should render default error fallback UI", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} />);

      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
      expect(
        screen.getByText(
          "We apologize for the inconvenience. An unexpected error has occurred."
        )
      ).toBeInTheDocument();
      expect(screen.getByTestId("alert-triangle-icon")).toBeInTheDocument();
    });

    /** Test that the error message is shown in development mode */
    it("should show error message in development mode", () => {
      const originalEnv = process.env.NODE_ENV;
      vi.stubEnv("NODE_ENV", "development");

      render(<ErrorFallback error={mockError} reset={mockReset} />);

      expect(screen.getByText("Test error message")).toBeInTheDocument();
      expect(screen.getByTestId("bug-icon")).toBeInTheDocument();

      vi.stubEnv("NODE_ENV", originalEnv ?? "test");
    });

    it("should not show error message in production mode", () => {
      const originalEnv = process.env.NODE_ENV;
      vi.stubEnv("NODE_ENV", "production");

      render(<ErrorFallback error={mockError} reset={mockReset} />);

      expect(screen.queryByText("Test error message")).not.toBeInTheDocument();
      expect(screen.queryByTestId("bug-icon")).not.toBeInTheDocument();

      vi.stubEnv("NODE_ENV", originalEnv ?? "test");
    });

    /** Test that the error digest is shown when available */
    it("should show error digest when available", () => {
      const errorWithDigest = { ...mockError, digest: "abc123" };

      render(<ErrorFallback error={errorWithDigest} reset={mockReset} />);

      expect(screen.getByText("Error ID: abc123")).toBeInTheDocument();
    });

    /** Test that the reset button is rendered when a reset function is provided */
    it("should render reset button when reset function provided", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} />);

      const resetButton = screen.getByRole("button", { name: /reset/i });
      expect(resetButton).toBeInTheDocument();

      fireEvent.click(resetButton);
      expect(mockReset).toHaveBeenCalledTimes(1);
    });

    /** Test that the try again button is rendered when a retry function is provided */
    it("should render try again button when retry function provided", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} retry={mockRetry} />);

      const tryAgainButton = screen.getByRole("button", { name: /try again/i });
      expect(tryAgainButton).toBeInTheDocument();

      fireEvent.click(tryAgainButton);
      expect(mockRetry).toHaveBeenCalledTimes(1);
    });

    /** Test that the reload page button is handled */
    it("should handle reload page button", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} />);

      const reloadButton = screen.getByRole("button", { name: /reload page/i });
      expect(reloadButton).toBeInTheDocument();

      fireEvent.click(reloadButton);
      expect(MockLocation.reload).toHaveBeenCalledTimes(1);
    });

    /** Test that the go home button is handled */
    it("should handle go home button", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} />);

      const homeButton = screen.getByRole("button", { name: /go home/i });
      expect(homeButton).toBeInTheDocument();

      fireEvent.click(homeButton);
      expect(MockLocation.href).toBe("/");
    });

    /** Test that no buttons are rendered when no functions are provided */
    it("should not render buttons when functions not provided", () => {
      render(<ErrorFallback error={mockError} />);

      expect(screen.queryByRole("button", { name: /reset/i })).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /try again/i })
      ).not.toBeInTheDocument();
    });
  });

  describe("MinimalErrorFallback", () => {
    /** Test that the minimal error UI is rendered */
    it("should render minimal error UI", () => {
      render(<MinimalErrorFallback error={mockError} reset={mockReset} />);

      expect(screen.getByText("Application Error")).toBeInTheDocument();
      expect(
        screen.getByText(
          "The application has encountered an unexpected error and needs to restart."
        )
      ).toBeInTheDocument();
      expect(screen.getByTestId("alert-triangle-icon")).toBeInTheDocument();
    });

    /** Test that the restart button is rendered when a reset function is provided */
    it("should render restart button when reset function provided", () => {
      render(<MinimalErrorFallback error={mockError} reset={mockReset} />);

      const restartButton = screen.getByRole("button", {
        name: /restart application/i,
      });
      expect(restartButton).toBeInTheDocument();

      fireEvent.click(restartButton);
      expect(mockReset).toHaveBeenCalledTimes(1);
    });

    /** Test that no restart button is rendered when no reset function is provided */
    it("should not render restart button when reset function not provided", () => {
      render(<MinimalErrorFallback error={mockError} />);

      expect(
        screen.queryByRole("button", { name: /restart application/i })
      ).not.toBeInTheDocument();
    });

    /** Test that the component has a full screen layout */
    it("should have full screen layout", () => {
      const { container } = render(
        <MinimalErrorFallback error={mockError} reset={mockReset} />
      );

      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveClass("min-h-screen");
    });
  });

  describe("PageErrorFallback", () => {
    /** Test that the page error UI is rendered */
    it("should render page error UI", () => {
      render(<PageErrorFallback error={mockError} reset={mockReset} />);

      expect(screen.getByText("Page Error")).toBeInTheDocument();
      expect(
        screen.getByText(
          "This page has encountered an error and cannot be displayed properly."
        )
      ).toBeInTheDocument();
      expect(screen.getByTestId("alert-triangle-icon")).toBeInTheDocument();
    });

    /** Test that the try again button is rendered when a reset function is provided */
    it("should render try again button when reset function provided", () => {
      render(<PageErrorFallback error={mockError} reset={mockReset} />);

      const tryAgainButton = screen.getByRole("button", { name: /try again/i });
      expect(tryAgainButton).toBeInTheDocument();

      fireEvent.click(tryAgainButton);
      expect(mockReset).toHaveBeenCalledTimes(1);
    });

    /** Test that the go to dashboard button is rendered */
    it("should render go to dashboard button", () => {
      render(<PageErrorFallback error={mockError} reset={mockReset} />);

      const dashboardButton = screen.getByRole("button", {
        name: /go to dashboard/i,
      });
      expect(dashboardButton).toBeInTheDocument();

      fireEvent.click(dashboardButton);
      expect(MockLocation.href).toBe("/");
    });

    /** Test that the error stack is shown in development mode */
    it("should show error stack in development mode", () => {
      const originalEnv = process.env.NODE_ENV;
      vi.stubEnv("NODE_ENV", "development");

      const errorWithStack = { ...mockError };
      errorWithStack.stack = "Error: Test error\n    at Component (Component.tsx:10:5)";

      render(<PageErrorFallback error={errorWithStack} reset={mockReset} />);

      expect(screen.getByText("Error Details (Development)")).toBeInTheDocument();

      // Click details to expand
      fireEvent.click(screen.getByText("Error Details (Development)"));
      expect(screen.getByText(/Error: Test error/)).toBeInTheDocument();

      vi.stubEnv("NODE_ENV", originalEnv ?? "test");
    });

    /** Test that the error stack is not shown in production mode */
    it("should not show error stack in production mode", () => {
      const originalEnv = process.env.NODE_ENV;
      vi.stubEnv("NODE_ENV", "production");

      const errorWithStack = { ...mockError };
      errorWithStack.stack = "Error: Test error\n    at Component (Component.tsx:10:5)";

      render(<PageErrorFallback error={errorWithStack} reset={mockReset} />);

      expect(screen.queryByText("Error Details (Development)")).not.toBeInTheDocument();

      vi.stubEnv("NODE_ENV", originalEnv ?? "test");
    });

    /** Test that the try again button is not rendered when no reset function is provided */
    it("should not render try again button when reset function not provided", () => {
      render(<PageErrorFallback error={mockError} />);

      expect(
        screen.queryByRole("button", { name: /try again/i })
      ).not.toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /go to dashboard/i })
      ).toBeInTheDocument();
    });
  });

  /** Test suite for accessibility */
  describe("accessibility", () => {
    /** Test that the component has a proper title text */
    it("should have proper title text", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} />);
      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    });

    /** Test that the component has proper button roles */
    it("should have proper button roles", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} retry={mockRetry} />);

      const buttons = screen.getAllByRole("button");
      expect(buttons).toHaveLength(4); // Try Again, Reset, Reload Page, Go Home
    });

    /** Test that the component has accessible button text */
    it("should have accessible button text", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} retry={mockRetry} />);

      expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /reset/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /reload page/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /go home/i })).toBeInTheDocument();
    });
  });

  /** Test suite for responsive design */
  describe("responsive design", () => {
    /** Test that the component has responsive classes */
    it("should have responsive classes", () => {
      const { container } = render(
        <PageErrorFallback error={mockError} reset={mockReset} />
      );

      expect(container.querySelector(".sm\\:flex-row")).toBeInTheDocument();
    });

    /** Test that the component has proper spacing classes */
    it("should have proper spacing classes", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} />);
      /** Spacing is applied to CardContent in the default fallback */
      expect(
        screen
          .getByText(
            "We apologize for the inconvenience. An unexpected error has occurred."
          )
          .closest(".space-y-4")
      ).toBeInTheDocument();
    });
  });
});
