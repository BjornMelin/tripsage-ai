/**
 * @fileoverview Unit tests for the ChatPage component, verifying chat functionality,
 * message rendering, and SSE streaming behavior.
 */

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ChatPage from "../../chat/page";

/**
 * Creates a mock ReadableStream for simulating SSE responses in tests.
 *
 * @param chunks - Array of string chunks to enqueue in the stream.
 * @returns A ReadableStream that emits the provided chunks as Uint8Array.
 */
function makeSSEStream(chunks: string[]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      for (const c of chunks) {
        controller.enqueue(new TextEncoder().encode(c));
      }
      controller.close();
    },
  });
}

describe("ChatPage", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch as any;
    vi.resetAllMocks();
  });

  it("renders empty state initially and submits a prompt", async () => {
    // Stream raw text chunks (toTextStreamResponse)
    const stream = makeSSEStream(["Hello"]);

    global.fetch = vi.fn().mockResolvedValue({ ok: true, body: stream });

    render(<ChatPage />);

    expect(
      screen.getByText(/Start a conversation to see messages here/i)
    ).toBeInTheDocument();

    const input = screen.getByLabelText(/Chat prompt/i);
    fireEvent.change(input, { target: { value: "Hi there" } });
    fireEvent.submit(input.closest("form")!);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalled();
    });

    await waitFor(() => {
      // assistant message renders
      expect(screen.getByText("Hello")).toBeInTheDocument();
    });
  });
});
