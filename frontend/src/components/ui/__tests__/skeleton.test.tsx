import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Skeleton } from "../skeleton";

describe("Skeleton", () => {
  it("renders a basic skeleton", () => {
    render(<Skeleton data-testid="skeleton" />);

    const skeleton = screen.getByTestId("skeleton");
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveAttribute("role", "status");
    expect(skeleton).toHaveAttribute("aria-label", "Loading content...");
  });

  it("applies custom width and height", () => {
    render(<Skeleton width="200px" height="100px" data-testid="skeleton" />);

    const skeleton = screen.getByTestId("skeleton");
    expect(skeleton).toHaveStyle({
      width: "200px",
      height: "100px",
    });
  });

  it("applies numeric width and height", () => {
    render(<Skeleton width={300} height={150} data-testid="skeleton" />);

    const skeleton = screen.getByTestId("skeleton");
    expect(skeleton).toHaveStyle({
      width: "300px",
      height: "150px",
    });
  });

  it("renders multiple lines", () => {
    const { container } = render(<Skeleton lines={3} data-testid="skeleton" />);

    const skeleton = screen.getByTestId("skeleton");
    expect(skeleton).toBeInTheDocument();

    // Should have multiple skeleton divs for lines
    const skeletonLines = container.querySelectorAll(".skeleton");
    expect(skeletonLines).toHaveLength(3);
  });

  it("applies custom className", () => {
    render(<Skeleton className="custom-class" data-testid="skeleton" />);

    const skeleton = screen.getByTestId("skeleton");
    expect(skeleton).toHaveClass("custom-class");
  });

  it("disables animation when animate is false", () => {
    render(<Skeleton animate={false} data-testid="skeleton" />);

    const skeleton = screen.getByTestId("skeleton");
    // When animation is disabled, it should have empty animation class
    expect(skeleton).toHaveClass("skeleton");
    // Check that animate-pulse is not applied when animation=none
    expect(skeleton.className).not.toMatch(/animate-pulse/);
  });

  it("applies different variants", () => {
    const { rerender } = render(
      <Skeleton variant="light" data-testid="skeleton" />
    );
    let skeleton = screen.getByTestId("skeleton");
    expect(skeleton).toHaveClass("bg-slate-50");

    rerender(<Skeleton variant="medium" data-testid="skeleton" />);
    skeleton = screen.getByTestId("skeleton");
    expect(skeleton).toHaveClass("bg-slate-200");

    rerender(<Skeleton variant="rounded" data-testid="skeleton" />);
    skeleton = screen.getByTestId("skeleton");
    expect(skeleton).toHaveClass("rounded-full");
  });

  it("applies wave animation", () => {
    render(<Skeleton animation="wave" data-testid="skeleton" />);

    const skeleton = screen.getByTestId("skeleton");
    expect(skeleton).toHaveClass("animate-[wave_1.5s_ease-in-out_infinite]");
  });

  it("forwards ref correctly", () => {
    const ref = { current: null };
    render(<Skeleton ref={ref} data-testid="skeleton" />);

    expect(ref.current).toBeInstanceOf(HTMLDivElement);
  });

  it("supports accessibility attributes", () => {
    render(
      <Skeleton aria-label="Custom loading message" data-testid="skeleton" />
    );

    const skeleton = screen.getByTestId("skeleton");
    expect(skeleton).toHaveAttribute("aria-label", "Custom loading message");
  });
});
