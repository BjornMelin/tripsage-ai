/** @vitest-environment jsdom */

import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ChatPage from "../../chat/page";

// Mock Streamdown-backed Response to avoid rehype/ESM issues in node test runner
vi.mock("@/components/ai-elements/response", () => ({
  Response: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="response">{children}</div>
  ),
}));

/**
 * Creates a mock ReadableStream for simulating SSE responses in tests.
 *
 * @param chunks - Array of string chunks to enqueue in the stream.
 * @returns A ReadableStream that emits the provided chunks as Uint8Array.
 */
function _makeSSEStream(chunks: string[]): ReadableStream<Uint8Array> {
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
    global.fetch = originalFetch;
    vi.resetAllMocks();
  });

  it("renders empty state and input controls", () => {
    render(<ChatPage />);
    expect(
      screen.getByText(/Start a conversation to see messages here/i)
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/Chat prompt/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Submit/i })).toBeInTheDocument();
  });
});
