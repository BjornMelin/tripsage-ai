import { createOpenAI } from "@ai-sdk/openai";
import { streamText } from "ai";
import type { NextRequest } from "next/server";
import { z } from "zod";

// Environment variables
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_TIMEOUT = Number.parseInt(process.env.API_TIMEOUT || "30000", 10);

// Request validation schema
const ChatRequestSchema = z.object({
  messages: z.array(
    z.object({
      role: z.enum(["user", "assistant", "system"]),
      content: z.string().max(4000, "Message content too long"),
    })
  ),
  session_id: z.string().uuid().optional(),
  stream: z.boolean().default(true),
});

// Error response types
class ChatError extends Error {
  constructor(
    message: string,
    public status = 500,
    public code?: string
  ) {
    super(message);
    this.name = "ChatError";
  }
}

/**
 * Forward request to FastAPI backend and handle streaming response
 */
async function forwardToBackend(
  messages: any[],
  sessionId?: string,
  stream = true,
  authToken?: string
): Promise<ReadableStream> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);

  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    // Forward authorization header if present
    if (authToken) {
      headers["Authorization"] = authToken;
    } else if (process.env.API_KEY) {
      // Fallback to server-side API key if no user token
      headers["Authorization"] = `Bearer ${process.env.API_KEY}`;
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/chat/`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        messages,
        session_id: sessionId,
        stream,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    // Handle error responses
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));

      // Map backend error codes to user-friendly messages
      switch (response.status) {
        case 401:
          throw new ChatError("Authentication required", 401, "AUTH_REQUIRED");
        case 403:
          throw new ChatError("Access denied", 403, "ACCESS_DENIED");
        case 429:
          throw new ChatError(
            "Too many requests. Please try again later.",
            429,
            "RATE_LIMITED"
          );
        case 503:
          throw new ChatError(
            "AI service temporarily unavailable",
            503,
            "SERVICE_UNAVAILABLE"
          );
        default:
          throw new ChatError(
            errorData.detail || "Failed to process chat request",
            response.status
          );
      }
    }

    // Return the response body as a readable stream
    if (!response.body) {
      throw new ChatError("No response body from backend", 500);
    }

    return response.body;
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof ChatError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === "AbortError") {
        throw new ChatError("Request timeout", 408, "TIMEOUT");
      }
      throw new ChatError(error.message);
    }

    throw new ChatError("Unknown error occurred");
  }
}

/**
 * POST handler for /api/chat
 * Forwards requests to the FastAPI backend with proper error handling and streaming
 */
export async function POST(req: NextRequest) {
  try {
    // Parse and validate request body
    const body = await req.json();
    const validatedData = ChatRequestSchema.parse(body);
    const { messages, session_id, stream } = validatedData;

    // Validate messages array
    if (messages.length === 0) {
      throw new ChatError("No messages provided", 400, "INVALID_REQUEST");
    }

    const lastMessage = messages[messages.length - 1];
    if (lastMessage.role !== "user") {
      throw new ChatError("Last message must be from user", 400, "INVALID_REQUEST");
    }

    // Get authorization header from the request
    const authToken = req.headers.get("authorization");

    // Forward to backend and get stream
    const backendStream = await forwardToBackend(
      messages,
      session_id,
      stream,
      authToken || undefined
    );

    // Transform the backend stream to match Vercel AI SDK format
    const transformedStream = new TransformStream({
      async transform(chunk, controller) {
        // The backend already sends in Vercel AI SDK format, so we can pass through
        controller.enqueue(chunk);
      },
    });

    // Pipe the backend stream through our transform
    backendStream.pipeTo(transformedStream.writable);

    // Return the streaming response
    return new Response(transformedStream.readable, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch (error) {
    console.error("Error in chat API route:", error);

    // Handle validation errors
    if (error instanceof z.ZodError) {
      const firstError = error.errors[0];
      return new Response(
        JSON.stringify({
          error: "Validation error",
          code: "VALIDATION_ERROR",
          details: firstError.message,
        }),
        {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Handle chat errors
    if (error instanceof ChatError) {
      return new Response(
        JSON.stringify({
          error: error.message,
          code: error.code,
        }),
        {
          status: error.status,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Generic error response
    return new Response(
      JSON.stringify({
        error: "Internal server error",
        code: "INTERNAL_ERROR",
      }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}
