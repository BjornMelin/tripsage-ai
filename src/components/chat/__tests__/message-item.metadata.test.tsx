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
});
