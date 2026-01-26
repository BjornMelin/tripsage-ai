/** @vitest-environment jsdom */

import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Markdown } from "./Markdown";

type AnyRecord = Record<string, unknown>;

let lastStreamdownProps: AnyRecord | null = null;

function CaptureStreamdownProps(props: AnyRecord): void {
  lastStreamdownProps = props;
}

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
  const mockPlugin = () => undefined;

  return {
    defaultRehypePlugins: {
      harden: [mockPlugin, {}],
      raw: mockPlugin,
      sanitize: mockPlugin,
    },
    // Minimal plugin objects for the wrapper to compose with.
    defaultRemarkPlugins: { gfm: mockPlugin },
    Streamdown: (props: AnyRecord & { children?: string }) => {
      // Capture props for assertions (functions are not serializable).
      CaptureStreamdownProps(props);
      return (
        <div data-testid="streamdown" data-mode={String(props.mode)}>
          {props.children}
        </div>
      );
    },
  };
});

describe("markdown/Markdown", () => {
  const getLastProps = () => {
    expect(lastStreamdownProps).not.toBeNull();
    return lastStreamdownProps as AnyRecord;
  };

  beforeEach(() => {
    vi.unstubAllEnvs();
    lastStreamdownProps = null;
  });

  it("adds a caret only while streaming and animating", () => {
    render(
      <Markdown content="hello" mode="streaming" isAnimating={true} className="x" />
    );

    const props = getLastProps();
    expect(props.caret).toBe("block");
    expect(props.parseIncompleteMarkdown).toBe(true);
  });

  it("disables controls while streaming and animating", () => {
    render(
      <Markdown
        content="hello"
        mode="streaming"
        isAnimating={true}
        controls={{ code: true, mermaid: true, table: true }}
      />
    );

    const props = getLastProps();
    expect(props.controls).toBe(false);
  });

  it("includes raw + sanitize plugins only in trusted profile", () => {
    render(<Markdown content="<b>ok</b>" mode="static" securityProfile="ai" />);
    let props = getLastProps();
    expect(Array.isArray(props.rehypePlugins)).toBe(true);
    expect((props.rehypePlugins as unknown[]).length).toBe(1);

    render(<Markdown content="<b>ok</b>" mode="static" securityProfile="trusted" />);
    props = getLastProps();
    expect((props.rehypePlugins as unknown[]).length).toBe(3);
  });

  it("forces safe anchor semantics and disables Streamdown link safety UI", () => {
    render(<Markdown content={"[ok](https://example.com)"} mode="static" />);

    const props = getLastProps();
    expect(props.linkSafety).toEqual({ enabled: false });
    expect(typeof (props.components as AnyRecord | undefined)?.a).toBe("function");
  });
});
