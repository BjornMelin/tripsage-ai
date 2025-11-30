/**
 * @fileoverview Factory for creating TripSage agents using AI SDK v6 ToolLoopAgent.
 *
 * Provides a centralized factory function for instantiating ToolLoopAgent
 * instances with consistent configuration, telemetry, and error handling.
 * Agents created through this factory automatically receive:
 *
 * - Telemetry spans for observability
 * - Token budget clamping
 * - Tool call repair for invalid inputs
 * - Consistent stop conditions
 */

import "server-only";

import type { ToolSet } from "ai";
import {
  generateObject,
  InvalidToolInputError,
  NoSuchToolError,
  stepCountIs,
  ToolLoopAgent,
} from "ai";
import { secureUuid } from "@/lib/security/random";
import { createServerLogger } from "@/lib/telemetry/logger";

import type {
  AgentDependencies,
  TripSageAgentConfig,
  TripSageAgentResult,
} from "./types";

const logger = createServerLogger("agent-factory");

/**
 * Default maximum tool execution steps for agents.
 * Allows complex multi-tool workflows while preventing infinite loops.
 */
const DEFAULT_MAX_STEPS = 10;

/**
 * Default temperature for agent generation.
 * Slightly lower than default for more consistent planning outputs.
 */
const DEFAULT_TEMPERATURE = 0.3;

/**
 * Creates a TripSage agent using AI SDK v6 ToolLoopAgent.
 *
 * Instantiates a reusable agent capable of autonomous multi-step reasoning
 * with tool calling. The agent runs in a loop until a stop condition is met
 * (default: stepCountIs(maxSteps)).
 *
 * @template TTools - Tool set type for the agent.
 * @param deps - Runtime dependencies including model and identifiers.
 * @param config - Agent configuration including tools and instructions.
 * @returns Configured ToolLoopAgent instance with metadata.
 *
 * @example
 * ```typescript
 * const { agent, agentType, modelId } = createTripSageAgent(deps, {
 *   agentType: "budgetPlanning",
 *   name: "Budget Agent",
 *   instructions: buildBudgetPrompt(input),
 *   tools: buildBudgetTools(deps.identifier),
 *   maxSteps: 10,
 * });
 *
 * // Stream the agent response
 * const stream = agent.stream({ prompt: userMessage });
 * ```
 */
// biome-ignore lint/style/useNamingConvention: TypeScript generic convention
export function createTripSageAgent<TTools extends ToolSet>(
  deps: AgentDependencies,
  config: TripSageAgentConfig<TTools>
): TripSageAgentResult {
  const {
    agentType,
    defaultMessages,
    instructions,
    maxOutputTokens,
    maxSteps = DEFAULT_MAX_STEPS,
    name,
    temperature = DEFAULT_TEMPERATURE,
    tools,
    topP,
  } = config;

  const requestId = secureUuid();

  logger.info(`Creating agent: ${name}`, {
    agentType,
    identifier: deps.identifier,
    maxSteps,
    modelId: deps.modelId,
    requestId,
  });

  const agent = new ToolLoopAgent({
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
        logger.info("Tool not found, cannot repair", {
          agentType,
          requestId,
          toolName: toolCall.toolName,
        });
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

      try {
        const schema = await inputSchema({ toolName: toolCall.toolName });

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
          agentType,
          requestId,
          toolName: toolCall.toolName,
        });

        return {
          ...toolCall,
          input: JSON.stringify(repairedArgs),
        };
      } catch (repairError) {
        logger.error("Tool call repair failed", {
          agentType,
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
      functionId: `agent.${agentType}`,
      isEnabled: true,
      metadata: {
        agentType,
        identifier: deps.identifier,
        modelId: deps.modelId,
        ...(deps.sessionId ? { sessionId: deps.sessionId } : {}),
        ...(deps.userId ? { userId: deps.userId } : {}),
      },
    },
    // Core configuration
    id: `tripsage-${agentType}-${requestId}`,
    instructions,

    // Generation parameters
    maxOutputTokens,
    model: deps.model,
    stopWhen: stepCountIs(maxSteps),
    temperature,
    toolChoice: "auto",
    tools,
    topP,
  });

  return {
    // biome-ignore lint/suspicious/noExplicitAny: ToolLoopAgent requires flexible tool types
    agent: agent as any,
    agentType,
    defaultMessages,
    modelId: deps.modelId,
  };
}

/**
 * Type guard to check if an error is a tool-related error.
 *
 * @param error - The error to check.
 * @returns True if the error is a NoSuchToolError or InvalidToolInputError.
 */
export function isToolError(
  error: unknown
): error is NoSuchToolError | InvalidToolInputError {
  return NoSuchToolError.isInstance(error) || InvalidToolInputError.isInstance(error);
}
