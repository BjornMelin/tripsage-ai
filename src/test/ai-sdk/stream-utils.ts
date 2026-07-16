/**
 * @fileoverview Stream testing utilities for AI SDK v7.
 *
 * Provides utilities for testing streaming AI responses and UI message streams.
 * Complements mock-model.ts for higher-level stream testing scenarios.
 *
 * @example
 * ```typescript
 * import { createMockStreamResponse, collectStreamChunks } from '@/test/ai-sdk/stream-utils';
 *
 * test('handles streaming response', async () => {
 *   const stream = createMockStreamResponse({
 *     chunks: ['Hello', ' ', 'World'],
 *   });
 *   const result = await collectStreamChunks(stream);
 *   expect(result).toBe('Hello World');
 * });
 * ```
 */

import {
  createUIMessageStream,
  createUIMessageStreamResponse,
  type FinishReason,
} from "ai";

/**
 * Options for creating a mock streaming response.
 */
export interface MockStreamOptions {
  /** Chunks to stream */
  chunks: string[];
  /** Initial delay before first chunk (ms) */
  initialDelayMs?: number;
  /** Delay between chunks (ms) */
  chunkDelayMs?: number;
}

/**
 * Creates a mock ReadableStream for testing streaming responses.
 *
 * This simulates AI SDK's streaming behavior for testing UI components
 * that consume streaming text.
 *
 * @param options Configuration for the stream
 * @returns ReadableStream that emits configured chunks
 *
 * @example
 * ```typescript
 * const stream = createMockStreamResponse({
 *   chunks: ['First', ' chunk', ' last'],
 *   chunkDelayMs: 50,
 * });
 * ```
 */
export function createMockStreamResponse(
  options: MockStreamOptions
): ReadableStream<string> {
  const { chunks, initialDelayMs = 0, chunkDelayMs = 0 } = options;

  let currentIndex = 0;

  return new ReadableStream({
    async start(controller) {
      // Initial delay
      if (initialDelayMs > 0) {
        await new Promise((resolve) => setTimeout(resolve, initialDelayMs));
      }

      // Enqueue chunks
      for (const chunk of chunks) {
        controller.enqueue(chunk);

        // Delay between chunks
        if (chunkDelayMs > 0 && currentIndex < chunks.length - 1) {
          await new Promise((resolve) => setTimeout(resolve, chunkDelayMs));
        }

        currentIndex++;
      }

      controller.close();
    },
  });
}

/**
 * Creates a mock AI SDK streaming response with proper SSE formatting.
 *
 * This simulates the actual format returned by AI SDK's streaming endpoints.
 *
 * @param options Stream configuration
 * @returns ReadableStream in AI SDK streaming format
 *
 * @example
 * ```typescript
 * const stream = createMockAiStreamResponse({
 *   textChunks: ['Hello', ' ', 'World'],
 * });
 * ```
 */
export function createMockAiStreamResponse(options: {
  textChunks: string[];
  messageId?: string;
}): ReadableStream<string> {
  const { textChunks, messageId = "msg-123" } = options;

  const encode = (payload: unknown) => `data: ${JSON.stringify(payload)}\n\n`;
  const sseChunks = [
    encode({ messageId, type: "start" }),
    encode({ id: "text-1", type: "text-start" }),
    ...textChunks.map((chunk) =>
      encode({ delta: chunk, id: "text-1", type: "text-delta" })
    ),
    encode({ id: "text-1", type: "text-end" }),
    encode({ type: "finish" }),
    "data: [DONE]\n\n",
  ];

  return createMockStreamResponse({
    chunkDelayMs: 10,
    chunks: sseChunks,
  });
}

async function readAllChunks(stream: ReadableStream<string>): Promise<string[]> {
  const reader = stream.getReader();
  const chunks: string[] = [];

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      chunks.push(value);
    }
    return chunks;
  } catch (error) {
    try {
      await reader.cancel(error);
    } catch {
      // ignore cancellation errors to surface original error
    }
    throw error;
  } finally {
    reader.releaseLock();
  }
}

/**
 * Collects all chunks from a ReadableStream into a single string.
 *
 * Utility for asserting on complete stream output in tests.
 *
 * @param stream The stream to collect
 * @returns Promise resolving to concatenated string
 *
 * @example
 * ```typescript
 * const stream = createMockStreamResponse({ chunks: ['a', 'b', 'c'] });
 * const result = await collectStreamChunks(stream);
 * expect(result).toBe('abc');
 * ```
 */
export async function collectStreamChunks(
  stream: ReadableStream<string>
): Promise<string> {
  const chunks = await readAllChunks(stream);
  return chunks.join("");
}

/**
 * Collects stream chunks as an array.
 *
 * Use when you need to inspect individual chunks.
 *
 * @param stream The stream to collect
 * @returns Promise resolving to array of chunks
 */
export async function collectStreamChunksArray(
  stream: ReadableStream<string>
): Promise<string[]> {
  return await readAllChunks(stream);
}

/**
 * Creates a mock UI message stream response for testing route handlers.
 *
 * Simulates a response created from an AI SDK UI message stream.
 *
 * @param options Configuration for the stream
 * @returns Response object with streaming body
 *
 * @example
 * ```typescript
 * const response = createMockUiMessageStreamResponse({
 *   textChunks: ['Hello', ' World'],
 *   finishReason: 'stop',
 * });
 * ```
 */
export function createMockUiMessageStreamResponse(options: {
  textChunks: string[];
  messageId?: string;
  finishReason?: FinishReason;
  toolCalls?: Array<{
    toolCallId: string;
    toolName: string;
    input: unknown;
  }>;
}): Response {
  const {
    textChunks,
    messageId = "msg-test-default",
    finishReason = "stop",
    toolCalls = [],
  } = options;

  const stream = createUIMessageStream({
    execute: ({ writer }) => {
      writer.write({ type: "start" });

      if (textChunks.length > 0) {
        writer.write({ id: "text-1", type: "text-start" });
        for (const chunk of textChunks) {
          writer.write({ delta: chunk, id: "text-1", type: "text-delta" });
        }
        writer.write({ id: "text-1", type: "text-end" });
      }

      for (const call of toolCalls) {
        const input = call.input ?? null;
        writer.write({
          toolCallId: call.toolCallId,
          toolName: call.toolName,
          type: "tool-input-start",
        });
        writer.write({
          inputTextDelta: JSON.stringify(input),
          toolCallId: call.toolCallId,
          type: "tool-input-delta",
        });
        writer.write({
          input,
          toolCallId: call.toolCallId,
          toolName: call.toolName,
          type: "tool-input-available",
        });
      }

      writer.write({ finishReason, type: "finish" });
    },
    generateId: () => messageId,
  });

  return createUIMessageStreamResponse({
    headers: {
      "Cache-Control": "no-cache",
    },
    stream,
  });
}

/**
 * Creates a mock error response for testing error handling.
 *
 * @param error Error message or object
 * @param status HTTP status code (default: 500)
 * @returns Response with error body
 */
export function createMockErrorResponse(
  error: string | { message: string; code?: string },
  status = 500
): Response {
  const body = typeof error === "string" ? { error } : error;
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status,
  });
}
