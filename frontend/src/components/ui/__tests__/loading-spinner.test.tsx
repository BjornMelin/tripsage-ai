import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { render } from "@/test/test-utils";
import { LoadingSpinner } from "../loading-spinner";

describe("LoadingSpinner", () => {
  it("renders default spinner", () => {
    render(<LoadingSpinner data-testid="spinner" />);

    const spinner = screen.getByTestId("spinner");
    expect(spinner).toBeInTheDocument();
    expect(spinner).toHaveAttribute("role", "status");
    expect(spinner).toHaveAttribute("aria-label", "Loading");
  });

  it("renders different variants", () => {
    const { rerender } = render(
      <LoadingSpinner variant="dots" data-testid="spinner" />
    );
    let spinner = screen.getByTestId("spinner");
    expect(spinner).toBeInTheDocument();

    rerender(<LoadingSpinner variant="bars" data-testid="spinner" />);
    spinner = screen.getByTestId("spinner");
    expect(spinner).toBeInTheDocument();

    rerender(<LoadingSpinner variant="pulse" data-testid="spinner" />);
    spinner = screen.getByTestId("spinner");
    expect(spinner).toBeInTheDocument();
  });

  it("applies different sizes", () => {
    const { rerender } = render(<LoadingSpinner size="sm" data-testid="spinner" />);
    let spinner = screen.getByTestId("spinner");
    expect(spinner).toHaveClass("h-4", "w-4");

    rerender(<LoadingSpinner size="lg" data-testid="spinner" />);
    spinner = screen.getByTestId("spinner");
    expect(spinner).toHaveClass("h-8", "w-8");

    rerender(<LoadingSpinner size="xl" data-testid="spinner" />);
    spinner = screen.getByTestId("spinner");
    expect(spinner).toHaveClass("h-12", "w-12");
  });

  it("applies different colors", () => {
    const { rerender } = render(<LoadingSpinner color="white" data-testid="spinner" />);
    let spinner = screen.getByTestId("spinner");
    expect(spinner).toHaveClass("text-white");

    rerender(<LoadingSpinner color="destructive" data-testid="spinner" />);
    spinner = screen.getByTestId("spinner");
    expect(spinner).toHaveClass("text-destructive");

    rerender(<LoadingSpinner color="success" data-testid="spinner" />);
    spinner = screen.getByTestId("spinner");
    expect(spinner).toHaveClass("text-green-600");
  });

  it("applies custom className", () => {
    render(<LoadingSpinner className="custom-spinner" data-testid="spinner" />);

    const spinner = screen.getByTestId("spinner");
    expect(spinner).toHaveClass("custom-spinner");
  });

  it("renders dots variant with correct structure", () => {
    const { container } = render(<LoadingSpinner variant="dots" />);

    const dots = container.querySelectorAll(".dots-spinner");
    expect(dots).toHaveLength(3);
  });

  it("renders bars variant with correct structure", () => {
    const { container } = render(<LoadingSpinner variant="bars" />);

    const bars = container.querySelectorAll(".bars-spinner");
    expect(bars).toHaveLength(5);
  });

  it("forwards ref correctly", () => {
    const ref = { current: null as HTMLDivElement | null };
    render(<LoadingSpinner ref={ref} data-testid="spinner" />);

    expect(ref.current).toBeInstanceOf(HTMLElement);
  });
});
