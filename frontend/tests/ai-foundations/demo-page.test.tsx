/**
 * @fileoverview Test for the AI SDK v6 demo page. Ensures the page renders
 * core controls, handles user input, processes streaming responses, and manages error states.
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Page from "@/app/ai-demo/page";

// Mock fetch to control API responses
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe("AI Demo Page", () => {
  beforeEach(() => {
    mockFetch.mockClear();
    // Ensure both global and window fetch are mocked in JSDOM
    (window as any).fetch = mockFetch;
  });

  it("renders prompt input and conversation area", () => {
    render(<Page />);
    expect(screen.getByPlaceholderText(/say hello to ai sdk v6/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /submit/i })).toBeInTheDocument();
  });

  it("handles user input correctly", async () => {
    render(<Page />);
    const textarea = screen.getByPlaceholderText(/say hello to ai sdk v6/i);

    fireEvent.change(textarea, { target: { value: "Hello world" } });
    expect(textarea).toHaveValue("Hello world");
  });

  it("submits prompt and streams response successfully", async () => {
    // Mock successful streaming response
    const mockReader = {
      read: vi
        .fn()
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: {"type":"text","text":"Hello"}\n\n'),
        })
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: {"type":"text","text":" world"}\n\n'),
        })
        .mockResolvedValueOnce({ done: true, value: null }),
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      body: {
        getReader: () => mockReader,
      },
    });

    render(<Page />);
    const textarea = screen.getByPlaceholderText(/say hello to ai sdk v6/i);
    const submit = screen.getByRole("button", { name: /submit/i });

    fireEvent.change(textarea, { target: { value: "Test input" } });
    fireEvent.click(submit);

    // Submission triggers streaming; implementation details of fetch are not asserted here.

    // Wait for streaming response to appear
    await waitFor(() => {
      expect(screen.getByText(/Hello world/)).toBeInTheDocument();
    });
  });

  it("handles fetch errors gracefully", async () => {
    mockFetch.mockRejectedValueOnce(new Error("Network error"));

    render(<Page />);
    const textarea = screen.getByPlaceholderText(/say hello to ai sdk v6/i);
    const submit = screen.getByRole("button", { name: /submit/i });

    fireEvent.change(textarea, { target: { value: "Test input" } });
    fireEvent.click(submit);

    await waitFor(() => {
      expect(screen.getByText(/failed to stream response/i)).toBeInTheDocument();
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });

  it("handles HTTP error responses", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
    });

    render(<Page />);
    const textarea = screen.getByPlaceholderText(/say hello to ai sdk v6/i);
    const submit = screen.getByRole("button", { name: /submit/i });

    fireEvent.change(textarea, { target: { value: "Test input" } });
    fireEvent.click(submit);

    await waitFor(() => {
      expect(screen.getByText(/failed to stream response/i)).toBeInTheDocument();
      expect(screen.getByText(/HTTP 500/i)).toBeInTheDocument();
    });
  });

  it("handles missing response body", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      body: null,
    });

    render(<Page />);
    const textarea = screen.getByPlaceholderText(/say hello to ai sdk v6/i);
    const submit = screen.getByRole("button", { name: /submit/i });

    fireEvent.change(textarea, { target: { value: "Test input" } });
    fireEvent.click(submit);

    await waitFor(() => {
      expect(screen.getByText(/failed to stream response/i)).toBeInTheDocument();
      expect(screen.getByText(/response body is not available/i)).toBeInTheDocument();
    });
  });

  it("clears error state on new submission", async () => {
    // First call fails
    mockFetch.mockRejectedValueOnce(new Error("First error"));

    render(<Page />);
    const textarea = screen.getByPlaceholderText(/say hello to ai sdk v6/i);
    const submit = screen.getByRole("button", { name: /submit/i });

    // Trigger first error
    fireEvent.change(textarea, { target: { value: "Test input" } });
    fireEvent.click(submit);

    await waitFor(() => {
      expect(screen.getByText(/failed to stream response/i)).toBeInTheDocument();
    });

    // Setup successful response for second call
    const mockReader = {
      read: vi
        .fn()
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode('data: {"type":"text","text":"Success"}\n\n'),
        })
        .mockResolvedValueOnce({ done: true, value: null }),
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      body: {
        getReader: () => mockReader,
      },
    });

    // Submit again
    fireEvent.click(submit);

    await waitFor(() => {
      expect(screen.queryByText(/failed to stream response/i)).not.toBeInTheDocument();
      expect(screen.getByText(/Success/)).toBeInTheDocument();
    });
  });

  it("handles empty input submission", async () => {
    const mockReader = {
      read: vi
        .fn()
        .mockResolvedValueOnce({
          done: false,
          value: new TextEncoder().encode(
            'data: {"type":"text","text":"Response"}\n\n'
          ),
        })
        .mockResolvedValueOnce({ done: true, value: null }),
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      body: {
        getReader: () => mockReader,
      },
    });

    render(<Page />);
    const textarea = screen.getByPlaceholderText(/say hello to ai sdk v6/i);
    const submit = screen.getByRole("button", { name: /submit/i });

    // Type empty string and submit
    fireEvent.change(textarea, { target: { value: "" } });
    fireEvent.click(submit);

    // Submits with empty string; assert response content instead of network details.

    await waitFor(() => {
      expect(screen.getByText(/Response/)).toBeInTheDocument();
    });
  });
});
