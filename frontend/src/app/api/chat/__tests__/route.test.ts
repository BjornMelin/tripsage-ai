import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { POST } from "../route";

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Mock TransformStream if not available
if (typeof TransformStream === "undefined") {
  global.TransformStream = class TransformStream {
    readable: ReadableStream;
    writable: WritableStream;

    constructor(_transformer?: Transformer<unknown, unknown>) {
      const { readable, writable } = new TransformStream();
      this.readable = readable;
      this.writable = writable;
    }
  } as unknown as typeof TransformStream;
}

// Mock environment variables
process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000";
process.env.API_TIMEOUT = "5000";

describe("/api/chat route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("POST handler", () => {
    it("should forward valid chat requests to backend", async () => {
      // Arrange
      const mockMessages = [{ role: "user", content: "Plan a trip to Paris" }];

      const mockRequest = new NextRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: mockMessages,
          stream: true,
        }),
      });

      // Mock backend response stream
      const mockStream = new ReadableStream({
        start(controller) {
          controller.enqueue(new TextEncoder().encode('0:"Hello"\n'));
          controller.enqueue(new TextEncoder().encode('0:" from"\n'));
          controller.enqueue(new TextEncoder().encode('0:" TripSage!"\n'));
          controller.enqueue(
            new TextEncoder().encode(
              'd:{"finishReason":"stop","usage":{"promptTokens":0,"completionTokens":0}}\n'
            )
          );
          controller.close();
        },
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        body: mockStream,
        headers: new Headers({
          "Content-Type": "text/event-stream",
        }),
      });

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/chat/",
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify({
            messages: mockMessages,
            session_id: undefined,
            stream: true,
          }),
        })
      );

      expect(response.status).toBe(200);
      expect(response.headers.get("Cache-Control")).toBe("no-cache");
      expect(response.headers.get("Connection")).toBe("keep-alive");
    });

    it("should handle authentication headers", async () => {
      // Arrange
      const mockMessages = [{ role: "user", content: "Book a flight" }];

      const mockRequest = new NextRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer test-token",
        },
        body: JSON.stringify({
          messages: mockMessages,
          stream: true,
        }),
      });

      const mockStream = new ReadableStream({
        start(controller) {
          controller.enqueue(new TextEncoder().encode('0:"OK"\n'));
          controller.close();
        },
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        body: mockStream,
        headers: new Headers(),
      });

      // Act
      await POST(mockRequest);

      // Assert
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer test-token",
          }),
        })
      );
    });

    it("should validate message content length", async () => {
      // Arrange
      const longContent = "x".repeat(4001); // Exceeds 4000 char limit
      const mockRequest = new NextRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: [{ role: "user", content: longContent }],
          stream: true,
        }),
      });

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(400);
      const body = await response.json();
      expect(body.error).toBe("Validation error");
      expect(body.code).toBe("VALIDATION_ERROR");
    });

    it("should reject empty message array", async () => {
      // Arrange
      const mockRequest = new NextRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: [],
          stream: true,
        }),
      });

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(400);
      const body = await response.json();
      expect(body.error).toBe("No messages provided");
      expect(body.code).toBe("INVALID_REQUEST");
    });

    it("should reject if last message is not from user", async () => {
      // Arrange
      const mockRequest = new NextRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: [
            { role: "user", content: "Hello" },
            { role: "assistant", content: "Hi there!" },
          ],
          stream: true,
        }),
      });

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(400);
      const body = await response.json();
      expect(body.error).toBe("Last message must be from user");
      expect(body.code).toBe("INVALID_REQUEST");
    });

    it("should handle network timeout", async () => {
      // Arrange
      const mockRequest = new NextRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: [{ role: "user", content: "Test timeout" }],
          stream: true,
        }),
      });

      // Mock timeout error
      mockFetch.mockImplementationOnce(
        () =>
          new Promise((_, reject) => {
            setTimeout(() => {
              const error = new Error("Aborted");
              error.name = "AbortError";
              reject(error);
            }, 100);
          })
      );

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(408);
      const body = await response.json();
      expect(body.error).toBe("Request timeout");
      expect(body.code).toBe("TIMEOUT");
    });

    it("should handle rate limiting", async () => {
      // Arrange
      const mockRequest = new NextRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: [{ role: "user", content: "Test rate limit" }],
          stream: true,
        }),
      });

      // Mock rate limit response
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 429,
        json: async () => ({ detail: "Rate limit exceeded" }),
        headers: new Headers(),
      });

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(429);
      const body = await response.json();
      expect(body.error).toBe("Too many requests. Please try again later.");
      expect(body.code).toBe("RATE_LIMITED");
    });

    it("should handle authentication errors", async () => {
      // Arrange
      const mockRequest = new NextRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: [{ role: "user", content: "Test auth" }],
          stream: true,
        }),
      });

      // Mock auth error response
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Invalid token" }),
        headers: new Headers(),
      });

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(401);
      const body = await response.json();
      expect(body.error).toBe("Authentication required");
      expect(body.code).toBe("AUTH_REQUIRED");
    });

    it("should handle service unavailable", async () => {
      // Arrange
      const mockRequest = new NextRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: [{ role: "user", content: "Test service" }],
          stream: true,
        }),
      });

      // Mock service unavailable response
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: async () => ({ detail: "Service temporarily unavailable" }),
        headers: new Headers(),
      });

      // Act
      const response = await POST(mockRequest);

      // Assert
      expect(response.status).toBe(503);
      const body = await response.json();
      expect(body.error).toBe("AI service temporarily unavailable");
      expect(body.code).toBe("SERVICE_UNAVAILABLE");
    });

    it("should handle valid session ID", async () => {
      // Arrange
      const mockSessionId = "550e8400-e29b-41d4-a716-446655440000";
      const mockRequest = new NextRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: [{ role: "user", content: "Continue conversation" }],
          session_id: mockSessionId,
          stream: true,
        }),
      });

      const mockStream = new ReadableStream({
        start(controller) {
          controller.enqueue(new TextEncoder().encode('0:"Continuing..."\n'));
          controller.close();
        },
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        body: mockStream,
        headers: new Headers(),
      });

      // Act
      await POST(mockRequest);

      // Assert
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining(mockSessionId),
        })
      );
    });

    it("should handle non-streaming requests", async () => {
      // Arrange
      const mockRequest = new NextRequest("http://localhost:3000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          messages: [{ role: "user", content: "Non-streaming test" }],
          stream: false,
        }),
      });

      const mockStream = new ReadableStream({
        start(controller) {
          controller.enqueue(
            new TextEncoder().encode('{"content":"Response","finish_reason":"stop"}\n')
          );
          controller.close();
        },
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        body: mockStream,
        headers: new Headers(),
      });

      // Act
      await POST(mockRequest);

      // Assert
      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('"stream":false'),
        })
      );
    });
  });
});
