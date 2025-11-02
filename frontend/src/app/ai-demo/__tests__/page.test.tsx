/**
 * @fileoverview SSE parsing tests for AI demo page UI message stream handling.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AIDemoPage from "../../ai-demo/page";

describe("AIDemoPage UI message stream parsing", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("accumulates text from fragmented UI message stream and ignores non-text events", async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        const chunks = [
          'data: {"type":"text","text":"Hello"}\n\n',
          'data: {"type":"text","text":" Wo',
          'rld"}\n\n',
          'data: {"type":"tool","name":"noop"}\n\n',
          "not-json\n\n",
        ];
        for (const c of chunks) controller.enqueue(encoder.encode(c));
        controller.close();
      },
    });

    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(stream as any, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }) as any
    );

    render(<AIDemoPage />);

    // Submit with empty prompt; route ignores
    const submit = screen.getByRole("button", { name: /submit/i });
    fireEvent.click(submit);

    // Wait for accumulated output
    const pre = await screen.findByText(/Hello World/);
    expect(pre).toBeInTheDocument();
  });
});
