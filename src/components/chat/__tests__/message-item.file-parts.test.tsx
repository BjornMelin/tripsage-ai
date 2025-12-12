/** @vitest-environment jsdom */

import type { UIMessage } from "ai";
import { describe, expect, it } from "vitest";
import { ChatMessageItem } from "@/components/chat/message-item";
import { fireEvent, render, screen } from "@/test/test-utils";

describe("ChatMessageItem file parts", () => {
  it("does not render inline image for invalid base64 data", () => {
    const message = {
      id: "m1",
      parts: [
        {
          data: "not-base64!!",
          mimeType: "image/png",
          type: "file",
        },
      ],
      role: "assistant",
    } as unknown as UIMessage;

    render(<ChatMessageItem message={message} />);

    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("Attachment")).toBeInTheDocument();
    expect(screen.getByText("image/png")).toBeInTheDocument();
  });

  it("hides inline image when load fails", () => {
    const message = {
      id: "m2",
      parts: [
        {
          data: "aGVsbG8=",
          mimeType: "image/png",
          type: "file",
        },
      ],
      role: "assistant",
    } as unknown as UIMessage;

    render(<ChatMessageItem message={message} />);

    const img = screen.getByRole("img", { name: "Attachment" });
    fireEvent.error(img);

    expect(img).toHaveStyle({ display: "none" });
  });
});
