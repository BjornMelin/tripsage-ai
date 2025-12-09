/**
 * @fileoverview Stream testing utilities for AI SDK v6.
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
 * Simulates the format returned by toUIMessageStreamResponse().
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
  finishReason?: "stop" | "length" | "tool-calls" | "error";
  toolCalls?: Array<{
    toolCallId: string;
    toolName: string;
    args: unknown;
  }>;
}): Response {
  const {
    textChunks,
    messageId = "msg-test-default",
    finishReason = "stop",
    toolCalls = [],
  } = options;

  const events: string[] = [];

  // Start event
  events.push(`data: ${JSON.stringify({ messageId, type: "start" })}\n\n`);

  // Text content
  if (textChunks.length > 0) {
    events.push(`data: ${JSON.stringify({ id: "text-1", type: "text-start" })}\n\n`);
    for (const chunk of textChunks) {
      events.push(
        `data: ${JSON.stringify({ delta: chunk, id: "text-1", type: "text-delta" })}\n\n`
      );
    }
    events.push(`data: ${JSON.stringify({ id: "text-1", type: "text-end" })}\n\n`);
  }

  // Tool calls
  for (const call of toolCalls) {
    // Build events as objects and stringify once to ensure proper JSON encoding
    const startEvent = {
      id: call.toolCallId,
      toolName: call.toolName,
      type: "tool-call-start",
    };
    events.push(`data: ${JSON.stringify(startEvent)}\n\n`);

    const argsText = JSON.stringify(call.args);
    const chunkCount = Math.max(1, Math.ceil(argsText.length / 50));
    const chunkSize = Math.ceil(argsText.length / chunkCount);
    for (let idx = 0; idx < argsText.length; idx += chunkSize) {
      const deltaEvent = {
        argsTextDelta: argsText.slice(idx, idx + chunkSize),
        id: call.toolCallId,
        type: "tool-call-delta",
      };
      events.push(`data: ${JSON.stringify(deltaEvent)}\n\n`);
    }

    const endEvent = { id: call.toolCallId, type: "tool-call-end" };
    events.push(`data: ${JSON.stringify(endEvent)}\n\n`);
  }

  // Finish event
  events.push(`data: ${JSON.stringify({ finishReason, type: "finish" })}\n\n`);
  events.push("data: [DONE]\n\n");

  const stream = createMockStreamResponse({
    chunkDelayMs: 5,
    chunks: events,
  });

  return new Response(stream, {
    headers: {
      "Cache-Control": "no-cache",
      // biome-ignore lint/style/useNamingConvention: HTTP header name
      Connection: "keep-alive",
      "Content-Type": "text/event-stream",
    },
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
