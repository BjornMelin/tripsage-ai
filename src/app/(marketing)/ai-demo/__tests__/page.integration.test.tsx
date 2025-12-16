/** @vitest-environment jsdom */

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { afterEach, describe, expect, it } from "vitest";
import Page from "@/app/(marketing)/ai-demo/page";
import { server } from "@/test/msw/server";

describe("AI Demo Page", () => {
  afterEach(() => {
    server.resetHandlers();
  });

  it("renders prompt input and conversation area", () => {
    render(<Page />);
    expect(screen.getByPlaceholderText(/say hello to ai sdk v6/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /submit/i })).toBeInTheDocument();
  });

  it(
    "submits prompt and streams response successfully",
    { timeout: 10000 },
    async () => {
      // Override handler with successful streaming response
      server.use(
        http.post("/api/ai/stream", () => {
          const encoder = new TextEncoder();
          const stream = new ReadableStream({
            start(controller) {
              controller.enqueue(
                encoder.encode('data: {"type":"text","text":"Hello"}\n\n')
              );
              controller.close();
            },
          });
          return new HttpResponse(stream, {
            headers: { "Content-Type": "text/event-stream" },
            status: 200,
          });
        })
      );

      render(<Page />);
      const textarea = screen.getByPlaceholderText(/say hello to ai sdk v6/i);
      const submit = screen.getByRole("button", { name: /submit/i });

      act(() => {
        fireEvent.change(textarea, { target: { value: "Test input" } });
        fireEvent.click(submit);
      });

      await waitFor(
        () => {
          expect(screen.getByText(/Hello/)).toBeInTheDocument();
        },
        { timeout: 2000 }
      );
    }
  );

  it("handles fetch errors gracefully", { timeout: 10000 }, async () => {
    // Override handler to simulate network error
    server.use(
      http.post("/api/ai/stream", () => {
        return HttpResponse.error();
      })
    );

    render(<Page />);
    const textarea = screen.getByPlaceholderText(/say hello to ai sdk v6/i);
    const submit = screen.getByRole("button", { name: /submit/i });

    act(() => {
      fireEvent.change(textarea, { target: { value: "Test input" } });
      fireEvent.click(submit);
    });

    await waitFor(
      () => {
        expect(screen.getByText(/failed to stream response/i)).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });

  it("handles HTTP error responses", { timeout: 10000 }, async () => {
    // Override handler to simulate 500 error
    server.use(
      http.post("/api/ai/stream", () => {
        return new HttpResponse(null, {
          status: 500,
          statusText: "Internal Server Error",
        });
      })
    );

    render(<Page />);
    const textarea = screen.getByPlaceholderText(/say hello to ai sdk v6/i);
    const submit = screen.getByRole("button", { name: /submit/i });

    act(() => {
      fireEvent.change(textarea, { target: { value: "Test input" } });
      fireEvent.click(submit);
    });

    await waitFor(
      () => {
        expect(screen.getByText(/failed to stream response/i)).toBeInTheDocument();
        expect(screen.getByText(/HTTP 500/i)).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });
});
