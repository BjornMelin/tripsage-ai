/** @vitest-environment jsdom */

import type { UIMessage } from "ai";
import { describe, expect, it } from "vitest";
import { ChatMessageItem } from "@/components/chat/message-item";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { fireEvent, render, screen } from "@/test/test-utils";

describe("ChatMessageItem tool provider metadata", () => {
  it("renders provider metadata for tool parts and redacts sensitive keys", () => {
    const message = unsafeCast<UIMessage>({
      id: "m-tool-meta",
      parts: [
        {
          callProviderMetadata: {
            openai: {
              token: "SECRET_TOKEN",
              traceId: "trace-123",
            },
          },
          input: { query: "SFO to JFK" },
          state: "input-streaming",
          toolCallId: "tool-call-1",
          toolName: "webSearch",
          type: "dynamic-tool",
        },
      ],
      role: "assistant",
    });

    render(<ChatMessageItem message={message} />);

    // Expand tool details to reveal code blocks
    fireEvent.click(screen.getByRole("button", { name: /webSearch/i }));

    expect(screen.getByText("Provider metadata")).toBeInTheDocument();
    expect(screen.queryByText(/SECRET_TOKEN/)).not.toBeInTheDocument();
    expect(screen.getByText(/\[REDACTED\]/)).toBeInTheDocument();
  });
});
