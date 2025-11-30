/**
 * @fileoverview Main chat agent using AI SDK v6 ToolLoopAgent.
 *
 * Creates a reusable chat agent that serves as the primary conversational
 * interface for travel planning. Provides access to all travel planning
 * tools through autonomous multi-step reasoning.
 */

import "server-only";

import * as tools from "@ai/tools";
import { wrapToolsWithUserId } from "@ai/tools/server/injection";
import type { ModelMessage, ToolSet, UIMessage } from "ai";
import {
  convertToModelMessages,
  generateObject,
  InvalidToolInputError,
  NoSuchToolError,
  stepCountIs,
  ToolLoopAgent,
} from "ai";
import { CHAT_DEFAULT_SYSTEM_PROMPT } from "@/ai/constants";
import { extractTexts, validateImageAttachments } from "@/app/api/_helpers/attachments";
import { secureUuid } from "@/lib/security/random";
import { createServerLogger } from "@/lib/telemetry/logger";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens, countTokens } from "@/lib/tokens/budget";
import { getModelContextLimit } from "@/lib/tokens/limits";

import type { AgentDependencies, TripSageAgentResult } from "./types";

const logger = createServerLogger("chat-agent");

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
 * Creates the main chat agent using AI SDK v6 ToolLoopAgent.
 *
 * The chat agent serves as the primary conversational interface,
 * providing access to all travel planning tools through autonomous
 * multi-step reasoning. Returns a reusable agent instance.
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
 *
 * // Use with createAgentUIStreamResponse
 * return createAgentUIStreamResponse({
 *   agent,
 *   messages,
 * });
 * ```
 */
export function createChatAgent(
  deps: AgentDependencies,
  messages: UIMessage[],
  config: ChatAgentConfig = {}
): TripSageAgentResult<ToolSet> {
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
    userScopedTools = [
      "createTravelPlan",
      "updateTravelPlan",
      "saveTravelPlan",
      "deleteTravelPlan",
      "bookAccommodation",
    ],
  } = config;

  const requestId = secureUuid();

  // Build system prompt with optional memory context
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
    throw new Error("No output tokens available - context limit exceeded");
  }

  // Token budgeting: clamp max output tokens based on prompt length
  const clampInput: ChatMessage[] = [
    { content: instructions, role: "system" },
    { content: textParts.join(" "), role: "user" },
  ];
  const { maxTokens } = clampMaxTokens(clampInput, desiredMaxTokens, deps.modelId);

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
    requestId,
  });

  const agent = new ToolLoopAgent<never, ToolSet>({
    // Experimental: Automatic tool call repair for malformed inputs
    // biome-ignore lint/style/useNamingConvention: AI SDK property name
    experimental_repairToolCall: async ({
      error,
      inputSchema,
      toolCall,
      tools: agentTools,
    }) => {
      // Don't attempt to fix invalid tool names
      if (NoSuchToolError.isInstance(error)) {
        return null;
      }

      // Only repair invalid input errors
      if (!InvalidToolInputError.isInstance(error)) {
        return null;
      }

      // Get the tool definition
      const tool = agentTools[toolCall.toolName as keyof typeof agentTools];
      if (!tool || typeof tool !== "object" || !("inputSchema" in tool)) {
        return null;
      }

      let schema: unknown;
      try {
        schema = await inputSchema({ toolName: toolCall.toolName });
      } catch (schemaError) {
        logger.error("Failed to retrieve tool input schema", {
          error:
            schemaError instanceof Error ? schemaError.message : String(schemaError),
          toolName: toolCall.toolName,
        });
        return null;
      }

      try {
        const { object: repairedArgs } = await generateObject({
          model: deps.model,
          prompt: [
            `The model tried to call the tool "${toolCall.toolName}" with the following inputs:`,
            JSON.stringify(toolCall.input, null, 2),
            "The tool accepts the following schema:",
            JSON.stringify(schema, null, 2),
            "Please fix the inputs to match the schema exactly.",
          ].join("\n"),
          schema: tool.inputSchema,
        });

        logger.info("Repaired tool call", {
          requestId,
          toolName: toolCall.toolName,
        });

        return {
          ...toolCall,
          input: JSON.stringify(repairedArgs),
        };
      } catch (repairError) {
        logger.error("Tool call repair failed", {
          error:
            repairError instanceof Error ? repairError.message : String(repairError),
          requestId,
          toolName: toolCall.toolName,
        });
        return null;
      }
    },

    // Telemetry settings
    // biome-ignore lint/style/useNamingConvention: AI SDK property name
    experimental_telemetry: {
      functionId: "agent.chat",
      isEnabled: true,
      metadata: {
        identifier: deps.identifier,
        modelId: deps.modelId,
        ...(deps.sessionId ? { sessionId: deps.sessionId } : {}),
        ...(deps.userId ? { userId: deps.userId } : {}),
      },
    },
    // Core configuration
    id: `tripsage-chat-${requestId}`,
    instructions,

    // Generation parameters
    maxOutputTokens: maxTokens,
    model: deps.model,
    stopWhen: stepCountIs(maxSteps),
    toolChoice: "auto",
    tools: chatTools,
  });

  return {
    agent,
    agentType: "router", // Chat agent acts as the main router
    defaultMessages: [],
    modelId: deps.modelId,
  };
}

/**
 * Converts UI messages to model messages for agent context.
 *
 * Wrapper around AI SDK's convertToModelMessages for type consistency.
 *
 * @param messages - UI messages to convert.
 * @returns Model messages for agent prompt.
 */
export function toModelMessages(messages: UIMessage[]): ModelMessage[] {
  return convertToModelMessages(messages);
}
