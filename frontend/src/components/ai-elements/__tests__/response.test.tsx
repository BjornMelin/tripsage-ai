import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// Mock streamdown to avoid CSS imports (KaTeX) in test environment
vi.mock("streamdown", () => ({
  Streamdown: ({ children, ...props }: { children?: React.ReactNode }) => (
    <div data-testid="mock-streamdown" {...props}>
      {children}
    </div>
  ),
}));

import { Response } from "@/components/ai-elements/response";

/**
 * Test suite for Response component.
 * Focuses on integration with Streamdown markdown renderer.
 */
describe("ai-elements/response", () => {
  /**
   * Verifies Response component renders markdown content through mocked Streamdown.
   * Ensures the component passes children to the underlying renderer correctly.
   */
  it("renders content through Streamdown mock", () => {
    const { getByTestId } = render(
      <Response>{"**bold** and `code` with a [link](https://example.com)"}</Response>
    );
    const wrapper = getByTestId("mock-streamdown");
    expect(wrapper).toBeInTheDocument();
    expect(wrapper.textContent).toContain("bold");
  });
});
