import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  ErrorFallback,
  MinimalErrorFallback,
  PageErrorFallback,
} from "../error-fallback";

// Mock lucide-react icons
vi.mock("lucide-react", () => ({
  // biome-ignore lint/style/useNamingConvention: React component names from lucide-react library
  AlertTriangle: () => <div data-testid="alert-triangle-icon" />,
  Bug: () => <div data-testid="bug-icon" />,
  Home: () => <div data-testid="home-icon" />,
  RefreshCw: () => <div data-testid="refresh-icon" />,
}));

// Mock window.location
const MOCK_LOCATION = {
  href: "",
  reload: vi.fn(),
};
Object.defineProperty(window, "location", {
  value: MOCK_LOCATION,
  writable: true,
});

describe("Error Fallback Components", () => {
  const mockError = new Error("Test error message") as Error & {
    digest?: string;
  };
  const mockReset = vi.fn();
  const mockRetry = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    MOCK_LOCATION.reload.mockClear();
    MOCK_LOCATION.href = "";
  });

  describe("ErrorFallback", () => {
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

    it("should show error digest when available", () => {
      const errorWithDigest = { ...mockError, digest: "abc123" };

      render(<ErrorFallback error={errorWithDigest} reset={mockReset} />);

      expect(screen.getByText("Error ID: abc123")).toBeInTheDocument();
    });

    it("should render reset button when reset function provided", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} />);

      const resetButton = screen.getByRole("button", { name: /reset/i });
      expect(resetButton).toBeInTheDocument();

      fireEvent.click(resetButton);
      expect(mockReset).toHaveBeenCalledTimes(1);
    });

    it("should render try again button when retry function provided", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} retry={mockRetry} />);

      const tryAgainButton = screen.getByRole("button", { name: /try again/i });
      expect(tryAgainButton).toBeInTheDocument();

      fireEvent.click(tryAgainButton);
      expect(mockRetry).toHaveBeenCalledTimes(1);
    });

    it("should handle reload page button", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} />);

      const reloadButton = screen.getByRole("button", { name: /reload page/i });
      expect(reloadButton).toBeInTheDocument();

      fireEvent.click(reloadButton);
      expect(MOCK_LOCATION.reload).toHaveBeenCalledTimes(1);
    });

    it("should handle go home button", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} />);

      const homeButton = screen.getByRole("button", { name: /go home/i });
      expect(homeButton).toBeInTheDocument();

      fireEvent.click(homeButton);
      expect(MOCK_LOCATION.href).toBe("/");
    });

    it("should not render buttons when functions not provided", () => {
      render(<ErrorFallback error={mockError} />);

      expect(screen.queryByRole("button", { name: /reset/i })).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /try again/i })
      ).not.toBeInTheDocument();
    });
  });

  describe("MinimalErrorFallback", () => {
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

    it("should render restart button when reset function provided", () => {
      render(<MinimalErrorFallback error={mockError} reset={mockReset} />);

      const restartButton = screen.getByRole("button", {
        name: /restart application/i,
      });
      expect(restartButton).toBeInTheDocument();

      fireEvent.click(restartButton);
      expect(mockReset).toHaveBeenCalledTimes(1);
    });

    it("should not render restart button when reset function not provided", () => {
      render(<MinimalErrorFallback error={mockError} />);

      expect(
        screen.queryByRole("button", { name: /restart application/i })
      ).not.toBeInTheDocument();
    });

    it("should have full screen layout", () => {
      const { container } = render(
        <MinimalErrorFallback error={mockError} reset={mockReset} />
      );

      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveClass("min-h-screen");
    });
  });

  describe("PageErrorFallback", () => {
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

    it("should render try again button when reset function provided", () => {
      render(<PageErrorFallback error={mockError} reset={mockReset} />);

      const tryAgainButton = screen.getByRole("button", { name: /try again/i });
      expect(tryAgainButton).toBeInTheDocument();

      fireEvent.click(tryAgainButton);
      expect(mockReset).toHaveBeenCalledTimes(1);
    });

    it("should render go to dashboard button", () => {
      render(<PageErrorFallback error={mockError} reset={mockReset} />);

      const dashboardButton = screen.getByRole("button", {
        name: /go to dashboard/i,
      });
      expect(dashboardButton).toBeInTheDocument();

      fireEvent.click(dashboardButton);
      expect(MOCK_LOCATION.href).toBe("/");
    });

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

    it("should not show error stack in production mode", () => {
      const originalEnv = process.env.NODE_ENV;
      vi.stubEnv("NODE_ENV", "production");

      const errorWithStack = { ...mockError };
      errorWithStack.stack = "Error: Test error\n    at Component (Component.tsx:10:5)";

      render(<PageErrorFallback error={errorWithStack} reset={mockReset} />);

      expect(screen.queryByText("Error Details (Development)")).not.toBeInTheDocument();

      vi.stubEnv("NODE_ENV", originalEnv ?? "test");
    });

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

  describe("accessibility", () => {
    it("should have proper title text", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} />);
      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    });

    it("should have proper button roles", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} retry={mockRetry} />);

      const buttons = screen.getAllByRole("button");
      expect(buttons).toHaveLength(4); // Try Again, Reset, Reload Page, Go Home
    });

    it("should have accessible button text", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} retry={mockRetry} />);

      expect(screen.getByRole("button", { name: /try again/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /reset/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /reload page/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /go home/i })).toBeInTheDocument();
    });
  });

  describe("responsive design", () => {
    it("should have responsive classes", () => {
      const { container } = render(
        <PageErrorFallback error={mockError} reset={mockReset} />
      );

      expect(container.querySelector(".sm\\:flex-row")).toBeInTheDocument();
    });

    it("should have proper spacing classes", () => {
      render(<ErrorFallback error={mockError} reset={mockReset} />);
      // Spacing is applied to CardContent in the default fallback
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
