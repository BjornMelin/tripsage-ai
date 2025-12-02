/**
 * @fileoverview AI SDK v6 type utilities and patterns.
 *
 * Re-exports AI SDK v6 type helpers and provides utility types
 * for common patterns in our tool/agent system.
 */

export type {
  InferUITools,
  ToolSet,
  TypedToolCall,
  TypedToolResult,
} from "ai";

/**
 * Infer tool input type from a tool definition.
 *
 * @example
 * ```typescript
 * type SearchInput = InferToolInput<typeof searchTool>;
 * ```
 */
export type InferToolInput<T> = T extends {
  execute: (input: infer I, ...args: unknown[]) => unknown;
}
  ? I
  : T extends { inputSchema: infer S }
    ? S extends { _output: infer O }
      ? O
      : unknown
    : unknown;

/**
 * Infer tool output type from a tool definition.
 *
 * @example
 * ```typescript
 * type SearchOutput = InferToolOutput<typeof searchTool>;
 * ```
 */
export type InferToolOutput<T> = T extends {
  execute: (...args: unknown[]) => infer R;
}
  ? Awaited<R>
  : unknown;

/**
 * Type guard for non-dynamic tool calls.
 * Enables type narrowing in tool result processing.
 *
 * @example
 * ```typescript
 * if (!isStaticToolCall(toolCall)) return;
 * // Now TypeScript knows toolCall is static
 * switch (toolCall.toolName) {
 *   case 'weather': ...
 * }
 * ```
 */
export function isStaticToolCall<T extends import("ai").ToolSet>(
  toolCall: import("ai").TypedToolCall<T>
): toolCall is Extract<import("ai").TypedToolCall<T>, { dynamic?: false }> {
  return !("dynamic" in toolCall && toolCall.dynamic);
}
