/**
 * @fileoverview Chat agent for travel planning conversations.
 */

import "server-only";

import { CHAT_DEFAULT_SYSTEM_PROMPT } from "@ai/constants";
import { toolRegistry } from "@ai/tools";
import { wrapToolsWithUserId } from "@ai/tools/server/injection";
import type { ModelMessage, PrepareStepFunction, ToolSet, UIMessage } from "ai";
import { convertToModelMessages } from "ai";
import { z } from "zod";
import { extractTexts, validateImageAttachments } from "@/app/api/_helpers/attachments";
import { createServerLogger } from "@/lib/telemetry/logger";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens, countTokens } from "@/lib/tokens/budget";
import { getModelContextLimit } from "@/lib/tokens/limits";

import { createTripSageAgent } from "./agent-factory";
import { extractTextFromContent, normalizeInstructions } from "./instructions";
import type { AgentDependencies, TripSageAgentResult } from "./types";

const logger = createServerLogger("chat-agent");

export { extractTextFromContent, normalizeInstructions };

const isUnknownArray = (value: unknown): value is unknown[] => Array.isArray(value);

const textContentPartSchema = z.looseObject({
  content: z.string().optional(),
  text: z.string().optional(),
  type: z.string().optional(),
});

const toolCallPartSchema = textContentPartSchema.extend({
  input: z.unknown().optional(),
  toolCallId: z.string().optional(),
  toolName: z.string(),
  type: z.literal("tool-call"),
});

const toolCallIdPartSchema = z.looseObject({
  toolCallId: z.string(),
  type: z.literal("tool-call"),
});

const toolResultPartSchema = textContentPartSchema.extend({
  output: z.unknown().optional(),
  toolCallId: z.string().optional(),
  type: z.literal("tool-result"),
});

const toolResultIdPartSchema = z.looseObject({
  toolCallId: z.string(),
  type: z.literal("tool-result"),
});

const toolResultOutputSchema = z.looseObject({
  type: z.string().optional(),
  value: z.unknown().optional(),
});

const messageContentPartSchema = z.union([
  toolCallPartSchema,
  toolResultPartSchema,
  textContentPartSchema,
]);

type MessageContentPart = z.infer<typeof messageContentPartSchema>;
type ToolResultOutput = z.infer<typeof toolResultOutputSchema>;
type ToolCallIdPart = z.infer<typeof toolCallIdPartSchema>;
type ToolResultIdPart = z.infer<typeof toolResultIdPartSchema>;

const parseMessageContentPart = (value: unknown): MessageContentPart | null => {
  const parsed = messageContentPartSchema.safeParse(value);
  return parsed.success ? parsed.data : null;
};

const parseToolCallIdPart = (value: unknown): ToolCallIdPart | null => {
  const parsed = toolCallIdPartSchema.safeParse(value);
  return parsed.success ? parsed.data : null;
};

const parseToolResultIdPart = (value: unknown): ToolResultIdPart | null => {
  const parsed = toolResultIdPartSchema.safeParse(value);
  return parsed.success ? parsed.data : null;
};

const parseToolResultOutput = (value: unknown): ToolResultOutput | null => {
  const parsed = toolResultOutputSchema.safeParse(value);
  return parsed.success ? parsed.data : null;
};

/**
 * Call options schema for the chat agent (AI SDK v6).
 *
 * Enables type-safe runtime configuration when calling agent.generate() or agent.stream().
 * These options are passed through prepareCall to dynamically configure the agent.
 */
export const chatCallOptionsSchema = z.object({
  /** Optional memory summary to inject into system prompt. */
  memorySummary: z.string().optional(),
  /** Optional session ID for context tracking. */
  sessionId: z.string().optional(),
  /** User ID for user-scoped tool operations. */
  userId: z.string(),
});

/** TypeScript type for chat agent call options. */
export type ChatCallOptions = z.infer<typeof chatCallOptionsSchema>;

/**
 * Configuration for creating the chat agent.
 */
export interface ChatAgentConfig {
  /** System prompt, can be extended with memory context. */
  systemPrompt?: string;

  /** Optional memory summary to append to system prompt. */
  memorySummary?: string;

  /** Desired max output tokens before clamping. */
  desiredMaxTokens?: number;

  /** Maximum tool execution steps. */
  maxSteps?: number;

  /** Tools that require user ID injection for user-scoped operations. */
  userScopedTools?: string[];

  /** Enable call options schema for dynamic configuration. */
  useCallOptions?: boolean;
}

/**
 * Validation result for chat messages.
 */
export interface ChatValidationResult {
  valid: boolean;
  error?: string;
  reason?: string;
}

/**
 * Validates chat messages for the chat agent.
 *
 * Checks for valid attachment types and message structure.
 *
 * @param messages - UI messages to validate.
 * @returns Validation result with error details if invalid.
 */
export function validateChatMessages(messages: UIMessage[]): ChatValidationResult {
  const att = validateImageAttachments(messages);
  if (!att.valid) {
    return {
      error: "invalid_attachment",
      reason: att.reason,
      valid: false,
    };
  }
  return { valid: true };
}

/**
 * Creates the main chat agent for conversational travel planning.
 *
 * Returns a reusable ToolLoopAgent instance supporting dynamic configuration
 * via callOptionsSchema, memory/context injection, and context window management.
 *
 * @param deps - Runtime dependencies including model and identifiers.
 * @param messages - UI messages for context.
 * @param config - Chat agent configuration.
 * @returns Configured ToolLoopAgent for chat.
 *
 * @example
 * ```typescript
 * const { agent } = createChatAgent(deps, messages, {
 *   memorySummary: "User prefers boutique hotels.",
 * });
 * const stream = agent.stream({ prompt: userMessage });
 * ```
 *
 * @example With dynamic call options
 * ```typescript
 * const { agent } = createChatAgent(deps, messages, { useCallOptions: true });
 * const stream = agent.stream({
 *   prompt: userMessage,
 *   options: { userId: "user_123", memorySummary: "..." },
 * });
 * ```
 */
export function createChatAgent(
  deps: AgentDependencies,
  messages: UIMessage[],
  config?: ChatAgentConfig & { useCallOptions?: false | undefined }
): TripSageAgentResult<ToolSet, never>;
export function createChatAgent(
  deps: AgentDependencies,
  messages: UIMessage[],
  config: ChatAgentConfig & { useCallOptions: true }
): TripSageAgentResult<ToolSet, ChatCallOptions>;
export function createChatAgent(
  deps: AgentDependencies,
  messages: UIMessage[],
  config: ChatAgentConfig = {}
): TripSageAgentResult<ToolSet, ChatCallOptions> | TripSageAgentResult<ToolSet, never> {
  if (!deps.userId) {
    throw new Error(
      "Chat agent requires a valid userId for user-scoped tool operations"
    );
  }

  const {
    desiredMaxTokens = 1024,
    maxSteps = 10,
    memorySummary,
    systemPrompt = CHAT_DEFAULT_SYSTEM_PROMPT,
    useCallOptions = false,
    userScopedTools = [
      "createTravelPlan",
      "updateTravelPlan",
      "saveTravelPlan",
      "deleteTravelPlan",
      "bookAccommodation",
    ],
  } = config;

  // Build base system prompt with optional memory context
  let instructions = systemPrompt;
  if (memorySummary) {
    instructions += `\n\nUser memory (summary):\n${memorySummary}`;
  }

  // Extract text parts for token counting
  const textParts = extractTexts(messages);
  const promptCount = countTokens([instructions, ...textParts], deps.modelId);
  const modelLimit = getModelContextLimit(deps.modelId);
  const available = Math.max(0, modelLimit - promptCount);

  if (available <= 0) {
    throw new Error(
      `Context limit exceeded: modelLimit=${modelLimit}, promptTokens=${promptCount}, available=${available}`
    );
  }

  // Token budgeting: clamp max output tokens based on prompt length
  const clampInput: ChatMessage[] = [
    { content: instructions, role: "system" },
    { content: textParts.join(" "), role: "user" },
  ];
  const { maxTokens } = clampMaxTokens(clampInput, desiredMaxTokens, deps.modelId);

  // Build tools with user ID injection for user-scoped operations
  const chatTools = wrapToolsWithUserId(
    toolRegistry,
    deps.userId,
    userScopedTools,
    deps.sessionId
  ) as ToolSet;

  logger.info("Creating chat agent", {
    identifier: deps.identifier,
    maxSteps,
    maxTokens,
    modelId: deps.modelId,
    useCallOptions,
  });

  const extractTokenizableText = (message: ModelMessage): string[] => {
    const content = message.content;
    if (typeof content === "string") return [content];
    if (!isUnknownArray(content)) return [];

    const texts: string[] = [];

    for (const part of content) {
      const parsedPart = parseMessageContentPart(part);
      if (!parsedPart) continue;

      if (parsedPart.text) texts.push(parsedPart.text);
      if (parsedPart.content) texts.push(parsedPart.content);

      if (parsedPart.type === "tool-call") {
        texts.push(
          JSON.stringify({
            input: parsedPart.input,
            toolName: parsedPart.toolName,
          })
        );
        continue;
      }

      if (parsedPart.type === "tool-result") {
        const parsedOutput = parseToolResultOutput(parsedPart.output);
        if (!parsedOutput) continue;

        if (parsedOutput.type === "text" && typeof parsedOutput.value === "string") {
          texts.push(parsedOutput.value);
        } else if (Object.hasOwn(parsedOutput, "value")) {
          texts.push(JSON.stringify(parsedOutput.value));
        }
      }
    }

    return texts;
  };

  const compressMessagesToTokenBudget = (
    stepMessages: ModelMessage[],
    promptTokenBudget: number
  ): { kept: ModelMessage[]; originalCount: number; keptCount: number } => {
    const originalCount = stepMessages.length;
    if (originalCount <= 2) {
      return { kept: stepMessages, keptCount: originalCount, originalCount };
    }

    const messageTokens = stepMessages.map((message) =>
      countTokens(extractTokenizableText(message), deps.modelId)
    );

    const keepIndices = new Set<number>([0]);
    let totalTokens = messageTokens[0] ?? 0;

    const getAssistantToolCallIds = (message: ModelMessage): Set<string> => {
      if (message.role !== "assistant") return new Set<string>();
      const content = message.content;
      if (!isUnknownArray(content)) return new Set<string>();
      const ids = new Set<string>();
      for (const part of content) {
        const parsedPart = parseToolCallIdPart(part);
        if (!parsedPart) continue;
        ids.add(parsedPart.toolCallId);
      }
      return ids;
    };

    const getToolResultIds = (message: ModelMessage): Set<string> => {
      if (message.role !== "tool") return new Set<string>();
      const content = message.content;
      if (!isUnknownArray(content)) return new Set<string>();
      const ids = new Set<string>();
      for (const part of content) {
        const parsedPart = parseToolResultIdPart(part);
        if (!parsedPart) continue;
        ids.add(parsedPart.toolCallId);
      }
      return ids;
    };

    const intersects = (a: Set<string>, b: Set<string>): boolean => {
      for (const v of a) if (b.has(v)) return true;
      return false;
    };

    let i = originalCount - 1;
    while (i >= 1) {
      const message = stepMessages[i];
      const isToolMessage = message.role === "tool";

      // Keep tool call/result pairs together when they are adjacent.
      let groupIndices: number[] = [i];
      let nextIndex = i - 1;
      if (isToolMessage && i - 1 >= 1) {
        const toolResultIds = getToolResultIds(message);
        const prev = stepMessages[i - 1];
        const prevToolCallIds = getAssistantToolCallIds(prev);
        if (toolResultIds.size > 0 && intersects(toolResultIds, prevToolCallIds)) {
          groupIndices = [i - 1, i];
          nextIndex = i - 2;
        }
      }

      let groupTokens = 0;
      for (const idx of groupIndices) {
        if (keepIndices.has(idx)) continue;
        groupTokens += messageTokens[idx] ?? 0;
      }

      // Always keep at least the first and the most recent group.
      const mustKeepSomeRecentContext = keepIndices.size === 1;
      if (!mustKeepSomeRecentContext && totalTokens + groupTokens > promptTokenBudget) {
        i = nextIndex;
        continue;
      }

      for (const idx of groupIndices) keepIndices.add(idx);
      totalTokens += groupTokens;
      i = nextIndex;
    }

    const kept = Array.from(keepIndices)
      .sort((a, b) => a - b)
      .map((idx) => stepMessages[idx])
      .filter(Boolean);

    return { kept, keptCount: kept.length, originalCount };
  };

  const prepareStep: PrepareStepFunction<ToolSet> = ({
    messages: stepMessages,
    stepNumber,
  }) => {
    // Token-based context management to stay within model context limits.
    // Budget prompt tokens to leave room for tool-call overhead and max output tokens.
    const promptTokenBudget = Math.max(1, modelLimit - maxTokens - 1024);
    const estimatedPromptTokens = countTokens(
      stepMessages.flatMap((m) => extractTokenizableText(m)),
      deps.modelId
    );

    if (estimatedPromptTokens > promptTokenBudget) {
      const { kept, keptCount, originalCount } = compressMessagesToTokenBudget(
        stepMessages,
        promptTokenBudget
      );
      logger.info("Compressing chat context", {
        estimatedPromptTokens,
        keptCount,
        originalCount,
        promptTokenBudget,
        stepNumber,
      });
      return { messages: kept };
    }
    return {};
  };

  const baseAgentConfig = {
    agentType: "router" as const, // Chat agent acts as the main router
    defaultMessages: [],
    instructions,
    maxOutputTokens: maxTokens,
    maxSteps,
    name: "Chat Agent",
    // AI SDK v6: Prepare step for context management in long conversations
    prepareStep,
    tools: chatTools,
  };

  // Avoid exposing call options unless explicitly enabled (keeps downstream agent APIs type-safe).
  if (!useCallOptions) {
    return createTripSageAgent<ToolSet, never>(deps, baseAgentConfig);
  }

  // AI SDK v6: Call options schema + prepareCall enable dynamic memory injection.
  return createTripSageAgent<ToolSet, ChatCallOptions>(deps, {
    ...baseAgentConfig,
    callOptionsSchema: chatCallOptionsSchema,
    prepareCall: ({ instructions: baseInstructions, options }) => {
      // Inject memory summary into instructions at runtime
      let finalInstructions = normalizeInstructions(baseInstructions);
      if (options.memorySummary) {
        finalInstructions += `\n\nUser memory (summary):\n${options.memorySummary}`;
      }
      return { instructions: finalInstructions };
    },
  });
}

// Re-export default system prompt for external consumers (e.g., API handlers)
export { CHAT_DEFAULT_SYSTEM_PROMPT };

/**
 * Converts UI messages to model messages for agent context.
 *
 * @param messages - UI messages to convert.
 * @returns Promise resolving to model messages for agent prompt.
 */
export function toModelMessages(messages: UIMessage[]): Promise<ModelMessage[]> {
  return convertToModelMessages(messages);
}
