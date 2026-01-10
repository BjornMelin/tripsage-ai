/** @vitest-environment jsdom */

import { render, screen } from "@testing-library/react";
import type React from "react";
import { describe, expect, it } from "vitest";
import { Shimmer } from "@/components/ai-elements/shimmer";

describe("ai-elements/shimmer", () => {
  it("renders shimmer text", () => {
    render(<Shimmer>Thinking…</Shimmer>);
    expect(screen.getByText("Thinking…")).toBeInTheDocument();
  });

  it("supports custom `as` components", () => {
    const Custom = (props: React.ComponentPropsWithoutRef<"span">) => (
      <span data-testid="custom" {...props} />
    );

    render(
      <Shimmer as={Custom} className="custom-class">
        Thinking…
      </Shimmer>
    );

    const custom = screen.getByTestId("custom");
    expect(custom).toBeInTheDocument();
    expect(custom).toHaveTextContent("Thinking…");
    expect(custom).toHaveClass("custom-class");
  });
});
