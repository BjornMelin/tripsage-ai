/** @vitest-environment jsdom */

import type { UIMessage } from "ai";
import { describe, expect, it, vi } from "vitest";
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

  it("renders reasoning-file data URLs as metadata without exposing base64", () => {
    const message = unsafeCast<UIMessage>({
      id: "m5",
      parts: [
        {
          mediaType: "image/png",
          type: "reasoning-file",
          url: "data:image/png;base64,aGVsbG8=",
        },
      ],
      role: "assistant",
    });

    const { container } = render(<ChatMessageItem message={message} />);

    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText("Attachment")).toBeInTheDocument();
    expect(screen.getByText("image/png")).toBeInTheDocument();
    expect(container).not.toHaveTextContent("aGVsbG8=");
  });

  it("uses distinct keys for identical file and reasoning-file parts", () => {
    const message = unsafeCast<UIMessage>({
      id: "m6",
      parts: [
        {
          mediaType: "application/pdf",
          type: "file",
          url: "https://example.com/shared.pdf",
        },
        {
          mediaType: "application/pdf",
          type: "reasoning-file",
          url: "https://example.com/shared.pdf",
        },
      ],
      role: "assistant",
    });
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {
      // Capture duplicate-key warnings without writing to stderr.
    });

    try {
      render(<ChatMessageItem message={message} />);

      expect(screen.getAllByText("Attachment")).toHaveLength(2);
      expect(consoleError.mock.calls.flat().join(" ")).not.toContain(
        "Encountered two children with the same key"
      );
    } finally {
      consoleError.mockRestore();
    }
  });
});
