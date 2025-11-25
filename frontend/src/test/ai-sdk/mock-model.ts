/**
 * @fileoverview AI SDK test utilities using official MockLanguageModelV3.
 *
 * Provides utilities for testing AI SDK v6 flows with accurate model behavior.
 * These utilities use the official MockLanguageModelV3 from ai/test for accurate simulation.
 *
 * @example
 * ```typescript
 * import { createMockModel, createMockToolModel } from '@/test/ai-sdk/mock-model';
 * import { generateText } from 'ai';
 *
 * test('generates text', async () => {
 *   const model = createMockModel({
 *     text: 'Hello from AI!',
 *   });
 *
 *   const result = await generateText({
 *     model,
 *     prompt: 'Say hello',
 *   });
 *
 *   expect(result.text).toBe('Hello from AI!');
 * });
 * ```
 */

import { MockLanguageModelV3 } from "ai/test";

/**
 * Options for creating a mock language model.
 */
export interface MockModelOptions {
  /** Text content to return */
  text?: string;
  /** Finish reason (default: 'stop') */
  finishReason?:
    | "stop"
    | "length"
    | "content-filter"
    | "tool-calls"
    | "error"
    | "other"
    | "unknown";
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
