/** @vitest-environment jsdom */

import { render } from "@testing-library/react";
import type { ComponentProps } from "react";
import type { Streamdown as StreamdownComponent } from "streamdown";
import { describe, expect, it, vi } from "vitest";

type StreamdownProps = ComponentProps<typeof StreamdownComponent>;

// Mock streamdown to avoid CSS imports (KaTeX) in test environment
vi.mock("streamdown", () => {
  const raw = () => undefined;
  const katex = () => undefined;
  const harden = () => undefined;

  return {
    defaultRehypePlugins: {
      harden: [harden, {}],
      katex,
      raw,
    },
    defaultRemarkPlugins: {},
    Streamdown: ({ children, ...props }: StreamdownProps) => {
      const rehypePlugins = Array.isArray(props.rehypePlugins)
        ? props.rehypePlugins
        : [];
      const hasRaw = rehypePlugins.includes(raw);

      return (
        <div
          data-testid="mock-streamdown"
          data-has-raw={String(hasRaw)}
          data-props={JSON.stringify(Object.keys(props))}
        >
          {children}
        </div>
      );
    },
  };
});

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

  it("passes expected props to Streamdown", () => {
    const { getByTestId } = render(<Response>hello</Response>);
    const wrapper = getByTestId("mock-streamdown");
    const rawProps = wrapper.getAttribute("data-props");
    expect(rawProps).toBeTruthy();
    const parsed = JSON.parse(rawProps ?? "null");
    expect(Array.isArray(parsed)).toBe(true);
    const propKeys = Array.isArray(parsed) ? parsed : [];
    expect(propKeys.every((key) => typeof key === "string")).toBe(true);
    const stringKeys = propKeys.filter((key): key is string => typeof key === "string");
    expect(stringKeys).toEqual(
      expect.arrayContaining(["controls", "mode", "shikiTheme"])
    );
  });

  it("disables raw HTML rendering by default", () => {
    const { getByTestId } = render(<Response>hello</Response>);
    const wrapper = getByTestId("mock-streamdown");
    expect(wrapper.getAttribute("data-has-raw")).toBe("false");
  });
});
