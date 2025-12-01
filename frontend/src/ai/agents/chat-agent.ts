/**
 * @fileoverview Chat agent for travel planning conversations.
 *
 * Reusable AI SDK v6 ToolLoopAgent that provides autonomous multi-step reasoning
 * over all travel planning tools. Supports dynamic memory injection, context window
 * management, and type-safe runtime configuration via callOptionsSchema/prepareCall/prepareStep.
 */

import "server-only";

import * as tools from "@ai/tools";
import { wrapToolsWithUserId } from "@ai/tools/server/injection";
import type { ModelMessage, ToolSet, UIMessage } from "ai";
import { convertToModelMessages } from "ai";
import { z } from "zod";
import { CHAT_DEFAULT_SYSTEM_PROMPT } from "@/ai/constants";
import { extractTexts, validateImageAttachments } from "@/app/api/_helpers/attachments";
import { createServerLogger } from "@/lib/telemetry/logger";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens, countTokens } from "@/lib/tokens/budget";
import { getModelContextLimit } from "@/lib/tokens/limits";

import { createTripSageAgent } from "./agent-factory";
import type { AgentDependencies, TripSageAgentResult } from "./types";

const logger = createServerLogger("chat-agent");

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
  config: ChatAgentConfig = {}
): TripSageAgentResult<ToolSet, ChatCallOptions> {
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
    { ...tools },
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

  // Use the centralized agent factory with AI SDK v6 features
  return createTripSageAgent<ToolSet, ChatCallOptions>(deps, {
    agentType: "router", // Chat agent acts as the main router
    // AI SDK v6: Call options schema for dynamic configuration
    ...(useCallOptions ? { callOptionsSchema: chatCallOptionsSchema } : {}),
    defaultMessages: [],
    instructions,
    maxOutputTokens: maxTokens,
    maxSteps,
    name: "Chat Agent",
    // AI SDK v6: Prepare call function for dynamic memory injection
    ...(useCallOptions
      ? {
          prepareCall: ({ instructions: baseInstructions, options }) => {
            // Inject memory summary into instructions at runtime
            let finalInstructions = baseInstructions;
            if (options.memorySummary) {
              finalInstructions += `\n\nUser memory (summary):\n${options.memorySummary}`;
            }
            return { instructions: finalInstructions };
          },
        }
      : {}),
    // AI SDK v6: Prepare step for context management in long conversations
    prepareStep: ({ messages: stepMessages, stepNumber }) => {
      // Compress conversation history for longer loops to stay within context limits
      if (stepMessages.length > 20) {
        logger.info("Compressing chat context", {
          originalCount: stepMessages.length,
          stepNumber,
        });
        return {
          messages: [
            stepMessages[0], // Keep system instructions
            ...stepMessages.slice(-15), // Keep last 15 messages
          ],
        };
      }
      return {};
    },
    tools: chatTools,
  });
}

// Re-export default system prompt for external consumers (e.g., API handlers)
export { CHAT_DEFAULT_SYSTEM_PROMPT };

/**
 * Converts UI messages to model messages for agent context.
 *
 * @param messages - UI messages to convert.
 * @returns Model messages for agent prompt.
 */
export function toModelMessages(messages: UIMessage[]): ModelMessage[] {
  return convertToModelMessages(messages);
}
