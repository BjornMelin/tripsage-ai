/** @vitest-environment jsdom */

import type { UIMessage } from "ai";
import { describe, expect, it } from "vitest";
import { ChatMessageItem } from "@/components/chat/message-item";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { fireEvent, render, screen } from "@/test/test-utils";

describe("ChatMessageItem file parts", () => {
  it("does not render inline image for invalid base64 data", () => {
    const message = unsafeCast<UIMessage>({
      id: "m1",
      parts: [
        {
          data: "not-base64!!",
          mimeType: "image/png",
          type: "file",
        },
      ],
      role: "assistant",
    });

    render(<ChatMessageItem message={message} />);

    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("Attachment")).toBeInTheDocument();
    expect(screen.getByText("image/png")).toBeInTheDocument();
  });

  it("hides inline image when load fails", () => {
    const message = unsafeCast<UIMessage>({
      id: "m2",
      parts: [
        {
          data: "aGVsbG8=",
          mimeType: "image/png",
          type: "file",
        },
      ],
      role: "assistant",
    });

    render(<ChatMessageItem message={message} />);

    const img = screen.getByRole("img", { name: "Attachment" });
    fireEvent.error(img);

    expect(img).toHaveStyle({ display: "none" });
  });

  it("does not render inline image for unsafe file URLs", () => {
    const message = unsafeCast<UIMessage>({
      id: "m3",
      parts: [
        {
          mimeType: "image/png",
          name: "Unsafe image",
          type: "file",
          url: "javascript:alert(1)",
        },
      ],
      role: "assistant",
    });

    render(<ChatMessageItem message={message} />);

    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("Unsafe image")).toBeInTheDocument();
    expect(screen.getByText("image/png")).toBeInTheDocument();
  });

  it("renders SVG file parts as attachments instead of inline images", () => {
    const message = unsafeCast<UIMessage>({
      id: "m4",
      parts: [
        {
          data: "PHN2ZyBvbmxvYWQ9ImFsZXJ0KDEpIj48L3N2Zz4=",
          mimeType: "image/svg+xml",
          name: "vector.svg",
          type: "file",
        },
      ],
      role: "assistant",
    });

    render(<ChatMessageItem message={message} />);

    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("vector.svg")).toBeInTheDocument();
    expect(screen.getByText("image/svg+xml")).toBeInTheDocument();
  });
});
