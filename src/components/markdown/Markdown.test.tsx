/** @vitest-environment jsdom */

import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Markdown } from "./Markdown";

type AnyRecord = Record<string, unknown>;

vi.mock("@streamdown/code", () => ({
  code: { name: "shiki", type: "code-highlighter" },
}));

vi.mock("@streamdown/math", () => ({
  math: { name: "katex", type: "math" },
}));

vi.mock("@streamdown/mermaid", () => ({
  mermaid: { language: "mermaid", name: "mermaid", type: "diagram" },
}));

vi.mock("streamdown", () => {
  let lastProps: AnyRecord | null = null;

  const mockPlugin = () => undefined;

  return {
    defaultRehypePlugins: {
      harden: [mockPlugin, {}],
      raw: mockPlugin,
      sanitize: mockPlugin,
    },
    // Minimal plugin objects for the wrapper to compose with.
    defaultRemarkPlugins: { gfm: mockPlugin },
    getLastStreamdownProps: () => lastProps,
    Streamdown: (props: AnyRecord & { children?: string }) => {
      // Capture props for assertions (functions are not serializable).
      lastProps = props;
      return (
        <div data-testid="streamdown" data-mode={String(props.mode)}>
          {props.children}
        </div>
      );
    },
  };
});

describe("markdown/Markdown", () => {
  const getLastProps = async () => {
    // Import from the mocked module to access the captured props.
    const mod = (await import("streamdown")) as unknown as {
      getLastStreamdownProps: () => AnyRecord | null;
    };
    const props = mod.getLastStreamdownProps();
    expect(props).not.toBeNull();
    return props as AnyRecord;
  };

  beforeEach(() => {
    vi.unstubAllEnvs();
  });

  it("adds a caret only while streaming and animating", async () => {
    render(
      <Markdown content="hello" mode="streaming" isAnimating={true} className="x" />
    );

    const props = await getLastProps();
    expect(props.caret).toBe("block");
    expect(props.parseIncompleteMarkdown).toBe(true);
  });

  it("disables controls while streaming and animating", async () => {
    render(
      <Markdown
        content="hello"
        mode="streaming"
        isAnimating={true}
        controls={{ code: true, mermaid: true, table: true }}
      />
    );

    const props = await getLastProps();
    expect(props.controls).toBe(false);
  });

  it("includes raw + sanitize plugins only in trusted profile", async () => {
    render(<Markdown content="<b>ok</b>" mode="static" securityProfile="ai" />);
    let props = await getLastProps();
    expect(Array.isArray(props.rehypePlugins)).toBe(true);
    expect((props.rehypePlugins as unknown[]).length).toBe(1);

    render(<Markdown content="<b>ok</b>" mode="static" securityProfile="trusted" />);
    props = await getLastProps();
    expect((props.rehypePlugins as unknown[]).length).toBe(3);
  });

  it("forces safe anchor semantics and disables Streamdown link safety UI", async () => {
    render(<Markdown content={"[ok](https://example.com)"} mode="static" />);

    const props = await getLastProps();
    expect(props.linkSafety).toEqual({ enabled: false });
    expect(typeof (props.components as AnyRecord | undefined)?.a).toBe("function");
  });
});
