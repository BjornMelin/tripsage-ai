/**
 * @fileoverview AI SDK test utilities using official MockLanguageModelV3.
 *
 * Provides utilities for testing AI SDK v6 flows with accurate model behavior.
 * Uses official MockLanguageModelV3 from ai/test and simulateReadableStream from ai.
 *
 * @example
 * ```typescript
 * import { createMockModel, createStreamingMockModel } from '@/test/ai-sdk/mock-model';
 * import { generateText, streamText } from 'ai';
 *
 * test('generates text', async () => {
 *   const model = createMockModel({ text: 'Hello from AI!' });
 *   const result = await generateText({ model, prompt: 'Say hello' });
 *   expect(result.text).toBe('Hello from AI!');
 * });
 *
 * test('streams text', async () => {
 *   const model = createStreamingMockModel({ chunks: ['Hello', ' World'] });
 *   const result = streamText({ model, prompt: 'Say hello' });
 *   let text = '';
 *   for await (const chunk of result.textStream) { text += chunk; }
 *   expect(text).toBe('Hello World');
 * });
 * ```
 */

import { simulateReadableStream } from "ai";
import { MockLanguageModelV3 } from "ai/test";

type FinishReason =
  | "stop"
  | "length"
  | "content-filter"
  | "tool-calls"
  | "error"
  | "other"
  | "unknown";

/**
 * Options for creating a mock language model.
 */
export interface MockModelOptions {
  /** Text content to return */
  text?: string;
  /** Finish reason (default: 'stop') */
  finishReason?: FinishReason;
  /** Token usage (default: {input: 10, output: 20}) */
  usage?: {
    inputTokens?: number;
    outputTokens?: number;
  };
  /** Warnings to include */
  warnings?: Array<{ type: string; message: string }>;
}

/**
 * Creates a mock language model using AI SDK's official MockLanguageModelV3.
 *
 * This provides accurate simulation of AI SDK behavior for testing.
 *
 * @param options Configuration for the mock model
 * @returns Configured mock model instance
 *
 * @example
 * ```typescript
 * const model = createMockModel({
 *   text: 'Paris is the capital of France',
 *   usage: { inputTokens: 15, outputTokens: 8 },
 * });
 * ```
 */
export function createMockModel(options: MockModelOptions = {}) {
  const {
    text = "Mock AI response",
    finishReason = "stop",
    usage = {},
    warnings = [],
  } = options;

  return new MockLanguageModelV3({
    doGenerate: async (_options) => ({
      content: [{ text, type: "text" as const }],
      finishReason,
      usage: {
        inputTokens: usage.inputTokens ?? 10,
        outputTokens: usage.outputTokens ?? 20,
        totalTokens: (usage.inputTokens ?? 10) + (usage.outputTokens ?? 20),
      },
      warnings: warnings as never[],
    }),
  });
}

/**
 * Creates a mock language model that supports tool calls.
 *
 * @param options Configuration including tool calls to return
 * @returns Configured mock model with tool support
 *
 * @example
 * ```typescript
 * const model = createMockToolModel({
 *   toolCalls: [
 *     {
 *       toolCallId: 'call-1',
 *       toolName: 'get_weather',
 *       args: { location: 'Paris' },
 *     },
 *   ],
 * });
 * ```
 */
export function createMockToolModel(
  options: {
    toolCalls?: Array<{
      toolCallId: string;
      toolName: string;
      args: unknown;
    }>;
    text?: string;
  } = {}
) {
  const { toolCalls = [], text = "" } = options;

  return new MockLanguageModelV3({
    // biome-ignore lint/suspicious/noExplicitAny: MockLanguageModelV3 requires complex types that are difficult to infer correctly
    doGenerate: async (_options): Promise<any> => ({
      content: [
        ...(text ? [{ text, type: "text" as const }] : []),
        ...toolCalls.map((call) => ({
          args: call.args,
          toolCallId: call.toolCallId,
          toolName: call.toolName,
          type: "tool-call" as const,
        })),
      ],
      finishReason: toolCalls.length > 0 ? ("tool-calls" as const) : ("stop" as const),
      usage: {
        inputTokens: 10,
        outputTokens: 20,
        totalTokens: 30,
      },
      warnings: [],
    }),
  });
}

/**
 * Options for creating a streaming mock model.
 */
export interface StreamingMockModelOptions {
  /** Text chunks to stream */
  chunks: string[];
  /** Finish reason (default: 'stop') */
  finishReason?: FinishReason;
  /** Token usage (default: {inputTokens: 10, outputTokens: 20}) */
  usage?: {
    inputTokens?: number;
    outputTokens?: number;
    totalTokens?: number;
  };
}

/**
 * Creates a streaming mock model using AI SDK's simulateReadableStream.
 *
 * Use this for testing streamText flows with deterministic streaming behavior.
 *
 * @param options Configuration for the streaming mock
 * @returns Configured streaming mock model
 *
 * @example
 * ```typescript
 * const model = createStreamingMockModel({
 *   chunks: ['Hello', ', ', 'World', '!'],
 * });
 *
 * const result = streamText({ model, prompt: 'Greet me' });
 * let text = '';
 * for await (const chunk of result.textStream) {
 *   text += chunk;
 * }
 * expect(text).toBe('Hello, World!');
 * ```
 */
export function createStreamingMockModel(options: StreamingMockModelOptions) {
  const { chunks, finishReason = "stop", usage = {} } = options;

  const inputTokens = usage.inputTokens ?? 10;
  const outputTokens = usage.outputTokens ?? 20;
  const totalTokens = usage.totalTokens ?? inputTokens + outputTokens;

  return new MockLanguageModelV3({
    doStream: async () => ({
      stream: simulateReadableStream({
        chunks: [
          { id: "text-1", type: "text-start" as const },
          ...chunks.map((delta) => ({
            delta,
            id: "text-1",
            type: "text-delta" as const,
          })),
          { id: "text-1", type: "text-end" as const },
          {
            finishReason,
            logprobs: undefined,
            type: "finish" as const,
            usage: {
              inputTokens,
              outputTokens,
              totalTokens,
            },
          },
        ],
      }),
    }),
  });
}

/**
 * Options for creating a streaming tool mock model.
 */
export interface StreamingToolMockModelOptions {
  /** Tool calls to include in the stream */
  toolCalls: Array<{
    toolCallId: string;
    toolName: string;
    args: unknown;
  }>;
  /** Optional text to include before tool calls */
  textBefore?: string;
  /** Optional text to include after tool results */
  textAfter?: string;
  /** Optional finish reason for stream completion */
  finishReason?: FinishReason | null;
  /** Optional token usage to surface */
  usage?: {
    completionTokens?: number;
    promptTokens?: number;
    totalTokens?: number;
  };
}

/**
 * Creates a streaming mock model with tool calls.
 *
 * Use for testing streaming agents that make tool calls.
 * Uses AI SDK v6 stream part types (tool-input-start, tool-input-delta, tool-input-end).
 *
 * @param options Configuration for tool calls
 * @returns Configured streaming mock model with tool support
 *
 * @example
 * ```typescript
 * const model = createStreamingToolMockModel({
 *   toolCalls: [{
 *     toolCallId: 'call-1',
 *     toolName: 'searchFlights',
 *     args: { origin: 'NYC', destination: 'LAX' },
 *   }],
 * });
 * ```
 */
export function createStreamingToolMockModel(options: StreamingToolMockModelOptions) {
  const { toolCalls, textBefore, textAfter, finishReason, usage } = options;

  if (toolCalls.length === 0) {
    throw new Error(
      "createStreamingToolMockModel requires a non-empty toolCalls array"
    );
  }

  // Build stream chunks using AI SDK v6 LanguageModelV3StreamPart types
  // Tool calls use tool-input-* types in v6 with `delta` field
  type StreamChunk =
    | { type: "text-start"; id: string }
    | { type: "text-delta"; id: string; delta: string }
    | { type: "text-end"; id: string }
    | { type: "tool-input-start"; id: string; toolName: string }
    | { type: "tool-input-delta"; id: string; delta: string }
    | { type: "tool-input-end"; id: string }
    | {
        type: "finish";
        finishReason: "tool-calls" | "stop";
        logprobs: undefined;
        usage: { inputTokens: number; outputTokens: number; totalTokens: number };
      };

  const streamChunks: StreamChunk[] = [];

  // Add text before if present
  if (textBefore) {
    streamChunks.push({ id: "text-1", type: "text-start" });
    streamChunks.push({ delta: textBefore, id: "text-1", type: "text-delta" });
    streamChunks.push({ id: "text-1", type: "text-end" });
  }

  // Add tool calls using v6 tool-input-* types
  for (const call of toolCalls) {
    streamChunks.push({
      id: call.toolCallId,
      toolName: call.toolName,
      type: "tool-input-start",
    });
    streamChunks.push({
      delta: JSON.stringify(call.args),
      id: call.toolCallId,
      type: "tool-input-delta",
    });
    streamChunks.push({ id: call.toolCallId, type: "tool-input-end" });
  }

  // Add text after if present
  if (textAfter) {
    streamChunks.push({ id: "text-2", type: "text-start" });
    streamChunks.push({ delta: textAfter, id: "text-2", type: "text-delta" });
    streamChunks.push({ id: "text-2", type: "text-end" });
  }

  // Add finish
  const inputTokens = usage?.promptTokens ?? 10;
  const outputTokens = usage?.completionTokens ?? 20;
  const totalTokens = usage?.totalTokens ?? inputTokens + outputTokens;
  const resolvedFinishReason: "stop" | "tool-calls" =
    finishReason === "stop" || finishReason === "tool-calls"
      ? finishReason
      : "tool-calls";
  streamChunks.push({
    finishReason: resolvedFinishReason,
    logprobs: undefined,
    type: "finish",
    usage: { inputTokens, outputTokens, totalTokens },
  });

  return new MockLanguageModelV3({
    doStream: async () => ({
      stream: simulateReadableStream({ chunks: streamChunks }),
    }),
  });
}

/**
 * Creates a mock model that returns structured JSON for generateObject tests.
 *
 * @param jsonObject The object to return as stringified JSON text
 * @returns Mock model configured for structured output
 *
 * @example
 * ```typescript
 * const model = createMockObjectModel({
 *   classification: 'flightSearch',
 *   confidence: 0.95,
 * });
 *
 * const result = await generateObject({
 *   model,
 *   schema: mySchema,
 *   prompt: 'Classify this',
 * });
 * expect(result.object.classification).toBe('flightSearch');
 * ```
 */
export function createMockObjectModel<T>(jsonObject: T) {
  return new MockLanguageModelV3({
    doGenerate: async () => ({
      content: [{ text: JSON.stringify(jsonObject), type: "text" as const }],
      finishReason: "stop" as const,
      usage: { inputTokens: 10, outputTokens: 20, totalTokens: 30 },
      warnings: [],
    }),
  });
}

/**
 * Creates a streaming mock model for streamObject tests.
 *
 * Streams the JSON object incrementally for partial object testing.
 *
 * @param jsonObject The object to stream as JSON
 * @returns Mock model configured for streaming structured output
 *
 * @example
 * ```typescript
 * const model = createStreamingObjectMockModel({
 *   name: 'Paris',
 *   country: 'France',
 * });
 *
 * const { partialObjectStream } = streamObject({
 *   model,
 *   schema: destinationSchema,
 *   prompt: 'Describe Paris',
 * });
 *
 * for await (const partial of partialObjectStream) {
 *   console.log(partial);
 * }
 * ```
 */
export function createStreamingObjectMockModel<T>(jsonObject: T) {
  const jsonString = JSON.stringify(jsonObject);
  // Split JSON into smaller chunks for realistic streaming
  const chunkSize = Math.ceil(jsonString.length / 5);
  const chunks: string[] = [];
  for (let i = 0; i < jsonString.length; i += chunkSize) {
    chunks.push(jsonString.slice(i, i + chunkSize));
  }

  return new MockLanguageModelV3({
    doStream: async () => ({
      stream: simulateReadableStream({
        chunks: [
          { id: "text-1", type: "text-start" as const },
          ...chunks.map((delta) => ({
            delta,
            id: "text-1",
            type: "text-delta" as const,
          })),
          { id: "text-1", type: "text-end" as const },
          {
            finishReason: "stop" as const,
            logprobs: undefined,
            type: "finish" as const,
            usage: { inputTokens: 10, outputTokens: 20, totalTokens: 30 },
          },
        ],
      }),
    }),
  });
}

/** Re-export simulateReadableStream for direct use in tests */
export { simulateReadableStream } from "ai";
