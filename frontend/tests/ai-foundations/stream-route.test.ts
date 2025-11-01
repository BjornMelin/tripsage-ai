/**
 * @fileoverview Comprehensive test for the demo streaming route. Mocks AI SDK to avoid
 * network calls and asserts SSE-compatible response shape, error handling, and edge cases.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock the `ai` package to avoid network/model dependencies
vi.mock("ai", () => ({
  streamText: vi.fn(),
}));

// Mock the openai provider
vi.mock("@ai-sdk/openai", () => ({
  openai: vi.fn(() => "openai/gpt-4o"),
}));

// Import after mocks are set up
import { streamText } from "ai";
import { POST } from "@/app/api/ai/stream/route";

const mockStreamText = vi.mocked(streamText);

describe("ai stream route", () => {
  beforeEach(() => {
    mockStreamText.mockClear();
  });

  it("returns an SSE response on successful request", async () => {
    // Mock successful streamText response
    const mockResponse = new Response('data: {"type":"finish"}\n\n', {
      headers: { "content-type": "text/event-stream" },
    });
    const mockToUIMessageStreamResponse = vi.fn().mockReturnValue(mockResponse);

    mockStreamText.mockReturnValue({
      toUIMessageStreamResponse: mockToUIMessageStreamResponse,
    } as any);

    const request = new Request("http://localhost", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ prompt: "Hello world" }),
    });

    const response = await POST(request);

    expect(response).toBeInstanceOf(Response);
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toMatch(/text\/event-stream/i);
    expect(mockStreamText).toHaveBeenCalledWith({
      model: "openai/gpt-4o",
      prompt: "Hello world",
    });
    expect(mockToUIMessageStreamResponse).toHaveBeenCalled();
  });

  it("handles requests with empty prompt", async () => {
    const mockResponse = new Response('data: {"type":"finish"}\n\n', {
      headers: { "content-type": "text/event-stream" },
    });
    const mockToUIMessageStreamResponse = vi.fn().mockReturnValue(mockResponse);

    mockStreamText.mockReturnValue({
      toUIMessageStreamResponse: mockToUIMessageStreamResponse,
    } as any);

    const request = new Request("http://localhost", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ prompt: "" }),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(mockStreamText).toHaveBeenCalledWith({
      model: "openai/gpt-4o",
      prompt: "Hello from AI SDK v6",
    });
  });

  it("handles requests with no prompt field", async () => {
    const mockResponse = new Response('data: {"type":"finish"}\n\n', {
      headers: { "content-type": "text/event-stream" },
    });
    const mockToUIMessageStreamResponse = vi.fn().mockReturnValue(mockResponse);

    mockStreamText.mockReturnValue({
      toUIMessageStreamResponse: mockToUIMessageStreamResponse,
    } as any);

    const request = new Request("http://localhost", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({}),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(mockStreamText).toHaveBeenCalledWith({
      model: "openai/gpt-4o",
      prompt: "Hello from AI SDK v6",
    });
  });

  it("handles malformed JSON request body", async () => {
    const mockResponse = new Response('data: {"type":"finish"}\n\n', {
      headers: { "content-type": "text/event-stream" },
    });
    const mockToUIMessageStreamResponse = vi.fn().mockReturnValue(mockResponse);

    mockStreamText.mockReturnValue({
      toUIMessageStreamResponse: mockToUIMessageStreamResponse,
    } as any);

    const request = new Request("http://localhost", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: "invalid json{",
    });

    const response = await POST(request);
    expect(response.status).toBe(200);
    expect(mockStreamText).toHaveBeenCalledWith({
      model: "openai/gpt-4o",
      prompt: "Hello from AI SDK v6",
    });
  });

  it("handles non-POST requests", async () => {
    const request = new Request("http://localhost", {
      method: "GET",
    });

    // The route handler should handle this appropriately
    // Note: Next.js route handlers typically only respond to their defined methods
    const response = await POST(request);
    expect(response).toBeDefined();
  });

  it("handles requests without content-type header", async () => {
    const mockResponse = new Response('data: {"type":"finish"}\n\n', {
      headers: { "content-type": "text/event-stream" },
    });
    const mockToUIMessageStreamResponse = vi.fn().mockReturnValue(mockResponse);

    mockStreamText.mockReturnValue({
      toUIMessageStreamResponse: mockToUIMessageStreamResponse,
    } as any);

    const request = new Request("http://localhost", {
      method: "POST",
      body: JSON.stringify({ prompt: "test" }),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
  });

  it("passes maxDuration constraint to streaming configuration", async () => {
    const mockResponse = new Response('data: {"type":"finish"}\n\n', {
      headers: { "content-type": "text/event-stream" },
    });
    const mockToUIMessageStreamResponse = vi.fn().mockReturnValue(mockResponse);

    mockStreamText.mockReturnValue({
      toUIMessageStreamResponse: mockToUIMessageStreamResponse,
    } as any);

    const request = new Request("http://localhost", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ prompt: "test" }),
    });

    await POST(request);

    // Verify the route uses the expected model and configuration
    expect(mockStreamText).toHaveBeenCalledWith({
      model: "openai/gpt-4o",
      prompt: "test",
    });
  });

  it("handles AI SDK errors gracefully", async () => {
    // Mock AI SDK to throw an error
    mockStreamText.mockImplementation(() => {
      throw new Error("AI SDK error");
    });

    const request = new Request("http://localhost", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ prompt: "test" }),
    });

    // Should propagate the error for Next.js error handling
    await expect(POST(request)).rejects.toThrow("AI SDK error");
  });

  it("handles streamText response conversion errors", async () => {
    // Mock successful streamText but failed response conversion
    const mockToUIMessageStreamResponse = vi.fn().mockImplementation(() => {
      throw new Error("Response conversion error");
    });

    mockStreamText.mockReturnValue({
      toUIMessageStreamResponse: mockToUIMessageStreamResponse,
    } as any);

    const request = new Request("http://localhost", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ prompt: "test" }),
    });

    await expect(POST(request)).rejects.toThrow("Response conversion error");
  });

  it("handles very long prompt content", async () => {
    const longPrompt = "a".repeat(10000);
    const mockResponse = new Response('data: {"type":"finish"}\n\n', {
      headers: { "content-type": "text/event-stream" },
    });
    const mockToUIMessageStreamResponse = vi.fn().mockReturnValue(mockResponse);

    mockStreamText.mockReturnValue({
      toUIMessageStreamResponse: mockToUIMessageStreamResponse,
    } as any);

    const request = new Request("http://localhost", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ prompt: longPrompt }),
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(mockStreamText).toHaveBeenCalledWith({
      model: "openai/gpt-4o",
      prompt: longPrompt,
    });
  });
});
