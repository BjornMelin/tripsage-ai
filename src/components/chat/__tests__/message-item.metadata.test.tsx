/** @vitest-environment jsdom */

import type { UIMessage } from "ai";
import { describe, expect, it } from "vitest";
import { ChatMessageItem } from "@/components/chat/message-item";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { render, screen } from "@/test/test-utils";

describe("ChatMessageItem metadata", () => {
  it("renders finish reason and token usage metadata", () => {
    const message = unsafeCast<UIMessage>({
      id: "m-meta",
      metadata: {
        abortReason: "timeout",
        finishReason: "stop",
        totalUsage: {
          inputTokens: 10,
          outputTokens: 5,
          totalTokens: 15,
        },
      },
      parts: [{ text: "Hello there", type: "text" }],
      role: "assistant",
    });

    render(<ChatMessageItem message={message} />);

    expect(screen.getByText(/Abort: timeout/)).toBeInTheDocument();
    expect(screen.getByText(/Finish: stop/)).toBeInTheDocument();
    expect(screen.getByText(/Tokens: 10 in/)).toBeInTheDocument();
  });

  it("renders only finish reason when other metadata is missing", () => {
    const message = unsafeCast<UIMessage>({
      id: "m-finish-only",
      metadata: {
        finishReason: "length",
      },
      parts: [{ text: "Done", type: "text" }],
      role: "assistant",
    });

    render(<ChatMessageItem message={message} />);

    expect(screen.getByText(/Finish: length/)).toBeInTheDocument();
    expect(screen.queryByText(/Abort:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Tokens:/)).not.toBeInTheDocument();
  });

  it("renders only token usage when finish/abort reasons are missing", () => {
    const message = unsafeCast<UIMessage>({
      id: "m-usage-only",
      metadata: {
        totalUsage: {
          inputTokens: 3,
          outputTokens: 2,
          totalTokens: 5,
        },
      },
      parts: [{ text: "Usage", type: "text" }],
      role: "assistant",
    });

    render(<ChatMessageItem message={message} />);

    expect(screen.getByText(/Tokens: 3 in/)).toBeInTheDocument();
    expect(screen.queryByText(/Abort:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Finish:/)).not.toBeInTheDocument();
  });

  it("omits metadata block when metadata is missing", () => {
    const message = unsafeCast<UIMessage>({
      id: "m-no-meta",
      parts: [{ text: "No metadata", type: "text" }],
      role: "assistant",
    });

    render(<ChatMessageItem message={message} />);

    expect(screen.queryByText(/Abort:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Finish:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Tokens:/)).not.toBeInTheDocument();
  });

  it("omits metadata when metadata is malformed", () => {
    const message = unsafeCast<UIMessage>({
      id: "m-malformed-meta",
      metadata: {
        finishReason: 123,
        totalUsage: "bad",
      },
      parts: [{ text: "Malformed", type: "text" }],
      role: "assistant",
    });

    render(<ChatMessageItem message={message} />);

    expect(screen.queryByText(/Abort:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Finish:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Tokens:/)).not.toBeInTheDocument();
  });
});
