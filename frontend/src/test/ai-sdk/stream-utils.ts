/**
 * @fileoverview Stream testing utilities for AI SDK.
 *
 * Provides utilities for testing streaming AI responses using
 * AI SDK's simulateReadableStream utility.
 *
 * @example
 * ```typescript
 * import { createMockStreamResponse } from '@/test/ai-sdk/stream-utils';
 *
 * test('handles streaming response', async () => {
 *   const stream = createMockStreamResponse({
 *     chunks: ['Hello', ' ', 'World'],
 *   });
 *
 *   const reader = stream.getReader();
 *   const chunks = [];
 *
 *   while (true) {
 *     const { done, value } = await reader.read();
 *     if (done) break;
 *     chunks.push(value);
 *   }
 *
 *   expect(chunks.join('')).toBe('Hello World');
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

  const sseChunks = [
    `data: {"type":"start","messageId":"${messageId}"}\n\n`,
    `data: {"type":"text-start","id":"text-1"}\n\n`,
    ...textChunks.map(
      (chunk) => `data: {"type":"text-delta","id":"text-1","delta":"${chunk}"}\n\n`
    ),
    `data: {"type":"text-end","id":"text-1"}\n\n`,
    `data: {"type":"finish"}\n\n`,
    "data: [DONE]\n\n",
  ];

  return createMockStreamResponse({
    chunkDelayMs: 10,
    chunks: sseChunks,
  });
}
