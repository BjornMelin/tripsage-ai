/**
 * @fileoverview Client-side API helpers for chat operations.
 *
 * Provides typed functions for calling chat API routes from client stores.
 * Handles request/response transformation and error handling.
 */

import type { Message, SendMessageOptions } from "@schemas/chat";
import type { UIMessage } from "ai";

/**
 * Options for sending a chat message.
 */
export interface SendMessageRequest {
  content: string;
  options?: SendMessageOptions;
  sessionId: string;
}

/**
 * Options for streaming a chat message.
 */
export interface StreamMessageRequest {
  content: string;
  options?: SendMessageOptions;
  sessionId: string;
}

/**
 * Response from non-streaming chat send.
 */
export interface SendMessageResponse {
  message: Message;
}

/**
 * Convert store messages to AI SDK UIMessage format.
 *
 * @param messages - Store messages to convert
 * @returns UIMessage array
 */
function convertToUiMessages(messages: Message[]): UIMessage[] {
  return messages.map((msg) => {
    const parts: Array<{ text: string; type: "text" }> = [
      { text: msg.content, type: "text" },
    ];

    // Note: Attachments are handled separately in the API layer
    // We include them as text references here for context
    if (msg.attachments && msg.attachments.length > 0) {
      for (const att of msg.attachments) {
        parts.push({
          text: `[Attachment: ${att.name || "file"}]`,
          type: "text",
        });
      }
    }

    return {
      id: msg.id,
      parts,
      role: msg.role,
    } satisfies UIMessage;
  });
}

/**
 * Send a non-streaming chat message.
 *
 * @param request - Send message request
 * @param existingMessages - Existing messages in the session
 * @returns Promise resolving to assistant message
 */
export async function sendChatMessage(
  request: SendMessageRequest,
  existingMessages: Message[] = []
): Promise<Message> {
  const userMessageParts: Array<{ text: string; type: "text" }> = [
    { text: request.content, type: "text" },
  ];

  // Note: Attachments are handled separately in the API layer
  // We include them as text references here for context
  if (request.options?.attachments && request.options.attachments.length > 0) {
    for (const file of request.options.attachments) {
      userMessageParts.push({
        text: `[Attachment: ${file.name || "file"}]`,
        type: "text",
      });
    }
  }

  const userMessage: UIMessage = {
    id: `msg-${Date.now()}`,
    parts: userMessageParts,
    role: "user",
  };

  const messages: UIMessage[] = [...convertToUiMessages(existingMessages), userMessage];

  const response = await fetch("/api/chat/send", {
    body: JSON.stringify({
      messages,
      sessionId: request.sessionId,
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Chat send failed: ${response.status}`);
  }

  const data = await response.json();

  // Transform response to Message format
  // handleChatNonStream returns { content, model, usage, durationMs, reasons }
  return {
    content: data.content || "",
    id: `msg-${Date.now()}`,
    role: "assistant",
    timestamp: new Date().toISOString(),
  };
}

/**
 * Stream a chat message.
 *
 * @param request - Stream message request
 * @param existingMessages - Existing messages in the session
 * @param onChunk - Callback for each chunk of streamed content
 * @param signal - Abort signal for canceling the request
 * @returns Promise resolving when stream completes
 */
export async function streamChatMessage(
  request: StreamMessageRequest,
  existingMessages: Message[] = [],
  onChunk: (chunk: string) => void,
  signal?: AbortSignal
): Promise<void> {
  const userMessageParts: Array<{ text: string; type: "text" }> = [
    { text: request.content, type: "text" },
  ];

  // Note: Attachments are handled separately in the API layer
  // We include them as text references here for context
  if (request.options?.attachments && request.options.attachments.length > 0) {
    for (const file of request.options.attachments) {
      userMessageParts.push({
        text: `[Attachment: ${file.name || "file"}]`,
        type: "text",
      });
    }
  }

  const userMessage: UIMessage = {
    id: `msg-${Date.now()}`,
    parts: userMessageParts,
    role: "user",
  };

  const messages: UIMessage[] = [...convertToUiMessages(existingMessages), userMessage];

  const response = await fetch("/api/chat/stream", {
    body: JSON.stringify({
      messages,
      sessionId: request.sessionId,
    }),
    headers: { "Content-Type": "application/json" },
    method: "POST",
    signal,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error || `Chat stream failed: ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Response body is null");
  }

  // Consume AI SDK v6 UI Message Stream (SSE format)
  // toUIMessageStreamResponse() returns a Response with SSE-formatted UIMessageChunks
  // Format: data: { type: 'text-delta', id: string, delta: string } | { type: 'text', text: string } | ...
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() || ""; // Keep incomplete event in buffer

      for (const event of events) {
        const lines = event.trim().split("\n");
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const json = line.slice(6);
          try {
            const chunk = JSON.parse(json) as
              | { type: "text-delta"; id: string; delta: string }
              | { type: "text"; text: string }
              | { type: "text-start"; id: string }
              | { type: "text-end"; id: string }
              | { type: "start" }
              | { type: "finish" }
              | { type: string; [key: string]: unknown };

            // AI SDK v6: Handle text-delta chunks (primary format for streaming text)
            if (chunk.type === "text-delta" && typeof chunk.delta === "string") {
              onChunk(chunk.delta);
            }
            // Fallback: Handle legacy 'text' format (for compatibility)
            else if (chunk.type === "text" && typeof chunk.text === "string") {
              onChunk(chunk.text);
            }
            // Ignore other chunk types (start, finish, text-start, text-end, etc.)
          } catch {
            // Ignore malformed JSON chunks
          }
        }
      }
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      // Stream was aborted, which is expected when stopStreaming is called
      return;
    }
    throw error;
  } finally {
    reader.releaseLock();
  }
}
