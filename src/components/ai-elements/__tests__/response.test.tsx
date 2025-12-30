/** @vitest-environment jsdom */

import { render, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Response } from "@/components/ai-elements/response";

// jsdom does not implement SVG getBBox which Mermaid uses during layout.
if (!SVGElement.prototype.getBBox) {
  Object.defineProperty(SVGElement.prototype, "getBBox", {
    configurable: true,
    value: () => ({ height: 0, width: 0, x: 0, y: 0 }),
  });
}

/**
 * Test suite for Response component.
 * Focuses on integration with Streamdown markdown renderer.
 */
describe("ai-elements/response", () => {
  it("does not interpret raw HTML tags", () => {
    const { container } = render(
      <Response>{`Hello <script>alert('xss')</script> world`}</Response>
    );

    expect(container.querySelector("script")).toBeNull();
    expect(container.innerHTML).not.toContain("<script");
    expect(container.textContent).toContain("Hello alert('xss') world");
  });

  it("blocks javascript: links", () => {
    const { container } = render(
      <Response>{"[danger](javascript:alert(1))"}</Response>
    );

    expect(container.querySelector("a")).toBeNull();

    const blocked = container.querySelector('span[title^="Blocked URL:"]');
    expect(blocked).not.toBeNull();
    expect(blocked?.textContent).toContain("danger");
    expect(blocked?.textContent).toContain("[blocked]");
    expect(blocked?.getAttribute("title")).toContain("javascript:alert(1)");
  });

  it("adds rel+target to safe http(s) links", () => {
    const { container } = render(<Response>{"[ok](https://example.com)"}</Response>);

    const link = container.querySelector("a");
    expect(link).not.toBeNull();
    expect(link?.getAttribute("href")).toBe("https://example.com/");
    expect(link?.getAttribute("target")).toBe("_blank");
    expect(link?.getAttribute("rel")).toBe("noopener noreferrer");
  });

  it("renders KaTeX math", () => {
    const { container } = render(
      <Response>{["$$", "E=mc^2", "$$"].join("\n")}</Response>
    );

    expect(container.querySelector(".katex")).not.toBeNull();
  });

  it("renders fenced code blocks", async () => {
    const { container } = render(
      <Response>{["```ts", "const a = 1", "```"].join("\n")}</Response>
    );

    await waitFor(() =>
      expect(container.querySelector('[data-streamdown="code-block"]')).not.toBeNull()
    );

    expect(
      container.querySelector('[data-streamdown="code-block"]')?.textContent
    ).toContain("const a = 1");
  });

  it("renders Mermaid diagrams", async () => {
    const { container } = render(
      <Response>{["```mermaid", "graph TD;", "A-->B;", "```"].join("\n")}</Response>
    );

    await waitFor(() =>
      expect(
        container.querySelector('[data-streamdown="mermaid-block"]')
      ).not.toBeNull()
    );
  });
});
