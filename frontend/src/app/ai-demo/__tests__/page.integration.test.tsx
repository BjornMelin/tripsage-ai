/** @vitest-environment jsdom */

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/ai-demo/page";

// Mock fetch to control API responses
const MOCK_FETCH = vi.fn();
(globalThis as { fetch: typeof fetch }).fetch = MOCK_FETCH;

describe("AI Demo Page", () => {
  beforeEach(() => {
    vi.useRealTimers();
    MOCK_FETCH.mockClear();
    (window as { fetch: typeof fetch }).fetch = MOCK_FETCH;
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
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
      // Mock successful streaming response with minimal chunks
      const mockReader = {
        read: vi
          .fn()
          .mockResolvedValueOnce({
            done: false,
            value: new TextEncoder().encode('data: {"type":"text","text":"Hello"}\n\n'),
          })
          .mockResolvedValueOnce({ done: true, value: null }),
      };

      MOCK_FETCH.mockResolvedValueOnce({
        body: {
          getReader: () => mockReader,
        },
        ok: true,
      } as unknown as Response);

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
    MOCK_FETCH.mockRejectedValueOnce(new Error("Network error"));

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
        expect(screen.getByText(/network error/i)).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });

  it("handles HTTP error responses", { timeout: 10000 }, async () => {
    MOCK_FETCH.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
    } as unknown as Response);

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
