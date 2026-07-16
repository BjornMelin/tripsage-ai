/** @vitest-environment jsdom */

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/(marketing)/ai-demo/page";
import { server } from "@/test/msw/server";

describe("AI Demo Page", () => {
  afterEach(() => {
    server.resetHandlers();
  });

  it("renders prompt input and conversation area", () => {
    render(<Page />);
    expect(screen.getByPlaceholderText(/say hello to ai sdk v7/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /submit/i })).toBeInTheDocument();
  });

  it("submits prompt and streams response successfully", {
    timeout: 10000,
  }, async () => {
    // Override handler with successful streaming response
    server.use(
      http.post("/api/ai/stream", () => {
        const encoder = new TextEncoder();
        const stream = new ReadableStream({
          start(controller) {
            controller.enqueue(
              encoder.encode(
                'data: {"type":"text-delta","id":"demo","delta":"Hello "}\n\n'
              )
            );
            controller.enqueue(
              encoder.encode(
                'data: {"type":"text-delta","id":"demo","delta":"world"}\n\n'
              )
            );
            controller.enqueue(encoder.encode("data: [DONE]\n\n"));
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
    const textarea = screen.getByPlaceholderText(/say hello to ai sdk v7/i);
    const submit = screen.getByRole("button", { name: /submit/i });

    act(() => {
      fireEvent.change(textarea, { target: { value: "Test input" } });
      fireEvent.click(submit);
    });

    await waitFor(
      () => {
        expect(screen.getByText(/Hello world/)).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });

  it("fails when the stream reaches EOF without a terminal marker", {
    timeout: 10000,
  }, async () => {
    const telemetryPayload = vi.fn();
    server.use(
      http.post("/api/ai/stream", () => {
        const encoder = new TextEncoder();
        const stream = new ReadableStream({
          start(controller) {
            controller.enqueue(
              encoder.encode(
                'data: {"type":"text-delta","id":"demo","delta":"Hello"}\n\n'
              )
            );
            controller.close();
          },
        });
        return new HttpResponse(stream, {
          headers: { "Content-Type": "text/event-stream" },
          status: 200,
        });
      }),
      http.post("/api/telemetry/ai-demo", async ({ request }) => {
        telemetryPayload(await request.json());
        return HttpResponse.json({ ok: true });
      })
    );

    render(<Page />);
    const textarea = screen.getByPlaceholderText(/say hello to ai sdk v7/i);
    const submit = screen.getByRole("button", { name: /submit/i });

    act(() => {
      fireEvent.change(textarea, { target: { value: "Test input" } });
      fireEvent.click(submit);
    });

    await waitFor(
      () => {
        expect(
          screen.getByText(/failed to stream response: ai stream ended unexpectedly/i)
        ).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
    expect(screen.queryByText("Hello")).not.toBeInTheDocument();
    await waitFor(() => {
      expect(telemetryPayload).toHaveBeenCalledWith({
        detail: "AI stream ended unexpectedly",
        status: "error",
      });
    });
  });

  it("accepts a native finish chunk as a terminal marker", {
    timeout: 10000,
  }, async () => {
    server.use(
      http.post("/api/ai/stream", () => {
        return new HttpResponse(
          'data: {"type":"text-delta","id":"demo","delta":"Finished"}\n\n' +
            'data: {"type":"finish","finishReason":"stop"}\n\n',
          {
            headers: { "Content-Type": "text/event-stream" },
            status: 200,
          }
        );
      })
    );

    render(<Page />);
    const textarea = screen.getByPlaceholderText(/say hello to ai sdk v7/i);

    act(() => {
      fireEvent.change(textarea, { target: { value: "Test input" } });
      fireEvent.click(screen.getByRole("button", { name: /submit/i }));
    });

    await waitFor(() => {
      expect(screen.getByText("Finished")).toBeInTheDocument();
    });
  });

  it("fails a native abort without exposing its reason", {
    timeout: 10000,
  }, async () => {
    const telemetryPayload = vi.fn();
    server.use(
      http.post("/api/ai/stream", () => {
        return new HttpResponse(
          'data: {"type":"abort","reason":"provider-secret"}\n\n' + "data: [DONE]\n\n",
          {
            headers: { "Content-Type": "text/event-stream" },
            status: 200,
          }
        );
      }),
      http.post("/api/telemetry/ai-demo", async ({ request }) => {
        telemetryPayload(await request.json());
        return HttpResponse.json({ ok: true });
      })
    );

    render(<Page />);
    const textarea = screen.getByPlaceholderText(/say hello to ai sdk v7/i);

    act(() => {
      fireEvent.change(textarea, { target: { value: "Test input" } });
      fireEvent.click(screen.getByRole("button", { name: /submit/i }));
    });

    await waitFor(() => {
      expect(
        screen.getByText(/failed to stream response: ai stream was interrupted/i)
      ).toBeInTheDocument();
    });
    expect(screen.queryByText(/provider-secret/i)).not.toBeInTheDocument();
    await waitFor(() => {
      expect(telemetryPayload).toHaveBeenCalledWith({
        detail: "AI stream was interrupted",
        status: "error",
      });
    });
  });

  it("surfaces UI stream error chunks and reports error telemetry", {
    timeout: 10000,
  }, async () => {
    const telemetryPayload = vi.fn();
    server.use(
      http.post("/api/ai/stream", () => {
        return new HttpResponse(
          'data: {"type":"error","errorText":"Model unavailable"}\n\n' +
            "data: [DONE]\n\n",
          {
            headers: { "Content-Type": "text/event-stream" },
            status: 200,
          }
        );
      }),
      http.post("/api/telemetry/ai-demo", async ({ request }) => {
        telemetryPayload(await request.json());
        return HttpResponse.json({ ok: true });
      })
    );

    render(<Page />);
    const textarea = screen.getByPlaceholderText(/say hello to ai sdk v7/i);

    act(() => {
      fireEvent.change(textarea, { target: { value: "Test input" } });
      fireEvent.click(screen.getByRole("button", { name: /submit/i }));
    });

    await waitFor(() => {
      expect(
        screen.getByText(/failed to stream response: model unavailable/i)
      ).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(telemetryPayload).toHaveBeenCalledWith({
        detail: "Model unavailable",
        status: "error",
      });
    });
  });

  it("handles fetch errors gracefully", { timeout: 10000 }, async () => {
    // Override handler to simulate network error
    server.use(
      http.post("/api/ai/stream", () => {
        return HttpResponse.error();
      })
    );

    render(<Page />);
    const textarea = screen.getByPlaceholderText(/say hello to ai sdk v7/i);
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
    const textarea = screen.getByPlaceholderText(/say hello to ai sdk v7/i);
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
