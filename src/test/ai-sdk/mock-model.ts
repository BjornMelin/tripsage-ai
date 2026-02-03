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
import { unsafeCast } from "@/test/helpers/unsafe-cast";

/**
 * Creates a usage object compatible with LanguageModelV3Usage.
 */
function createUsage(input: number, output: number) {
  return {
    inputTokens: {
      cacheRead: undefined,
      cacheWrite: undefined,
      noCache: undefined,
      total: input,
    },
    outputTokens: {
      reasoning: undefined,
      text: output,
      total: output,
    },
  };
}

/** Finish reason type for mock model */
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

// Internal type for doGenerate result - mirrors LanguageModelV3GenerateResult
interface MockGenerateResult {
  content: Array<
    | { type: "text"; text: string }
    | { type: "tool-call"; toolCallId: string; toolName: string; input: string }
  >;
  finishReason: FinishReason;
  usage: ReturnType<typeof createUsage>;
  warnings: never[];
}

// Internal type for doStream result - mirrors LanguageModelV3StreamResult
interface MockStreamResult {
  stream: ReadableStream<unknown>;
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

  const inputTokens = usage.inputTokens ?? 10;
  const outputTokens = usage.outputTokens ?? 20;

  const result: MockGenerateResult = {
    content: [{ text, type: "text" }],
    finishReason,
    usage: createUsage(inputTokens, outputTokens),
    warnings: warnings as never[],
  };

  // Use unsafeCast for test mock - third-party types are complex to model exactly
  return new MockLanguageModelV3({
    doGenerate: unsafeCast(result),
  });
}

/**
 * Creates a mock language model with call tracking.
 *
 * @param options - Configuration for the mock model.
 * @returns Mock model plus a mutable call log for assertions.
 * @see https://sdk.vercel.ai/docs
 */
export function createMockModelWithTracking(options: MockModelOptions = {}) {
  const calls: Array<{ input: unknown }> = [];
  const {
    text = "Mock AI response",
    finishReason = "stop",
    usage = {},
    warnings = [],
  } = options;

  const inputTokens = usage.inputTokens ?? 10;
  const outputTokens = usage.outputTokens ?? 20;

  const result: MockGenerateResult = {
    content: [{ text, type: "text" }],
    finishReason,
    usage: createUsage(inputTokens, outputTokens),
    warnings: warnings as never[],
  };

  const model = new MockLanguageModelV3({
    doGenerate: (input) => {
      calls.push({ input });
      return unsafeCast(result);
    },
  });

  return { calls, model };
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

  const finishReason: FinishReason = toolCalls.length > 0 ? "tool-calls" : "stop";

  const result: MockGenerateResult = {
    content: [
      ...(text ? [{ text, type: "text" as const }] : []),
      ...toolCalls.map((call) => ({
        input: JSON.stringify(call.args),
        toolCallId: call.toolCallId,
        toolName: call.toolName,
        type: "tool-call" as const,
      })),
    ],
    finishReason,
    usage: createUsage(10, 20),
    warnings: [] as never[],
  };

  return new MockLanguageModelV3({
    doGenerate: unsafeCast(result),
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

  const result: MockStreamResult = {
    stream: simulateReadableStream({
      chunks: [
        { id: "text-1", type: "text-start" },
        ...chunks.map((delta) => ({
          delta,
          id: "text-1",
          type: "text-delta",
        })),
        { id: "text-1", type: "text-end" },
        {
          finishReason,
          type: "finish",
          usage: createUsage(inputTokens, outputTokens),
        },
      ],
    }),
  };

  return new MockLanguageModelV3({
    doStream: unsafeCast(result),
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
  finishReason?: "stop" | "tool-calls" | null;
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
 * @param options - Configuration for tool calls
 * @returns Configured streaming mock model with tool support
 * @throws {Error} Thrown when `toolCalls` is empty.
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

  const inputTokens = usage?.promptTokens ?? 10;
  const outputTokens = usage?.completionTokens ?? 20;
  const resolvedFinishReason: FinishReason =
    finishReason === "stop" ? "stop" : "tool-calls";

  // Build stream chunks
  type StreamChunk =
    | { type: "text-start"; id: string }
    | { type: "text-delta"; id: string; delta: string }
    | { type: "text-end"; id: string }
    | { type: "tool-input-start"; id: string; toolName: string }
    | { type: "tool-input-delta"; id: string; delta: string }
    | { type: "tool-input-end"; id: string }
    | {
        type: "finish";
        finishReason: FinishReason;
        usage: ReturnType<typeof createUsage>;
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

  streamChunks.push({
    finishReason: resolvedFinishReason,
    type: "finish",
    usage: createUsage(inputTokens, outputTokens),
  });

  const result: MockStreamResult = {
    stream: simulateReadableStream({ chunks: streamChunks }),
  };

  return new MockLanguageModelV3({
    doStream: unsafeCast(result),
  });
}

/**
 * Creates a mock model that returns structured JSON for structured output tests.
 *
 * @typeParam T - The shape of the JSON object returned by the mock model.
 * @param jsonObject - The object to return as stringified JSON text
 * @returns Mock model configured for structured output
 *
 * @example
 * ```typescript
 * const model = createMockObjectModel({
 *   classification: 'flightSearch',
 *   confidence: 0.95,
 * });
 *
 * const result = await generateText({
 *   model,
 *   output: Output.object({ schema: mySchema }),
 *   prompt: 'Classify this',
 * });
 * expect(result.output?.classification).toBe('flightSearch');
 * ```
 */
export function createMockObjectModel<T>(jsonObject: T) {
  const result: MockGenerateResult = {
    content: [{ text: JSON.stringify(jsonObject), type: "text" }],
    finishReason: "stop",
    usage: createUsage(10, 20),
    warnings: [] as never[],
  };

  return new MockLanguageModelV3({
    doGenerate: unsafeCast(result),
  });
}

/**
 * Creates a streaming mock model for structured output streaming tests.
 *
 * Streams the JSON object incrementally for partial output testing.
 *
 * @typeParam T - The shape of the JSON object streamed by the mock model.
 * @param jsonObject - The object to stream as JSON
 * @returns Mock model configured for streaming structured output
 */
export function createStreamingObjectMockModel<T>(jsonObject: T) {
  const jsonString = JSON.stringify(jsonObject);
  // Split JSON into smaller chunks for realistic streaming
  const chunkSize = Math.ceil(jsonString.length / 5);
  const chunks: string[] = [];
  for (let i = 0; i < jsonString.length; i += chunkSize) {
    chunks.push(jsonString.slice(i, i + chunkSize));
  }

  const result: MockStreamResult = {
    stream: simulateReadableStream({
      chunks: [
        { id: "text-1", type: "text-start" },
        ...chunks.map((delta) => ({
          delta,
          id: "text-1",
          type: "text-delta",
        })),
        { id: "text-1", type: "text-end" },
        {
          finishReason: "stop" as const,
          type: "finish",
          usage: createUsage(10, 20),
        },
      ],
    }),
  };

  return new MockLanguageModelV3({
    doStream: unsafeCast(result),
  });
}

/** Re-export simulateReadableStream for direct use in tests */
export { simulateReadableStream } from "ai";
