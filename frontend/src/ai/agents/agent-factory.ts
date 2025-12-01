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

import type { LanguageModel, ToolSet } from "ai";
import {
  asSchema,
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
 * Maximum number of tool repair attempts to avoid runaway costs.
 */
const MAX_TOOL_REPAIR_ATTEMPTS = 2;

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
export function createTripSageAgent<TagentTools extends ToolSet>(
  deps: AgentDependencies,
  config: TripSageAgentConfig<TagentTools>
): TripSageAgentResult<TagentTools> {
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

  const agent = new ToolLoopAgent<never, TagentTools>({
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

      const repairAttempts = Number(
        (toolCall as { repairAttempts?: number }).repairAttempts ?? 0
      );
      if (repairAttempts >= MAX_TOOL_REPAIR_ATTEMPTS) {
        logger.warn("Max repair attempts reached", {
          agentType,
          requestId,
          toolName: toolCall.toolName,
        });
        return null;
      }

      // Get the tool definition
      const tool = agentTools[toolCall.toolName as keyof typeof agentTools];
      if (!tool || typeof tool !== "object" || !("inputSchema" in tool)) {
        return null;
      }

      const parseRawInput = () => {
        if (typeof toolCall.input === "string") {
          try {
            return JSON.parse(toolCall.input);
          } catch {
            return toolCall.input;
          }
        }
        return toolCall.input;
      };

      const attemptLocalRepair = async () => {
        const schema = asSchema(tool.inputSchema);
        const rawInput = parseRawInput();
        if (schema?.validate) {
          const result = await schema.validate(rawInput);
          if (result.success) {
            return {
              ok: true as const,
              value: result.value,
            };
          }
          return {
            error: result.error.message,
            ok: false as const,
          };
        }
        // Without a validator, we can only return a stringified version of the raw input.
        try {
          return { ok: true as const, value: rawInput };
        } catch (error) {
          return {
            error: error instanceof Error ? error.message : "Unknown parse error",
            ok: false as const,
          };
        }
      };

      try {
        const schema = await inputSchema({ toolName: toolCall.toolName });
        const prompt = [
          `The model tried to call the tool "${toolCall.toolName}" with the following inputs:`,
          JSON.stringify(toolCall.input, null, 2),
          "The tool accepts the following schema:",
          JSON.stringify(schema, null, 2),
          "Please fix the inputs to match the schema exactly.",
        ].join("\n");

        const attemptModelRepair = async (modelId: string, model: LanguageModel) => {
          const { object: repaired } = await generateObject({
            model,
            prompt,
            schema: tool.inputSchema,
          });
          const schema = asSchema(tool.inputSchema);
          if (schema?.validate) {
            const validation = await schema.validate(repaired);
            if (!validation.success) {
              throw new Error(
                `Repaired args invalid for schema using model ${modelId}: ${validation.error.message}`
              );
            }
            return validation.value;
          }
          return repaired;
        };

        let repairedArgs: unknown;
        try {
          repairedArgs = await attemptModelRepair(deps.modelId, deps.model);
        } catch (primaryError) {
          logger.warn("Primary tool call repair failed", {
            agentType,
            error:
              primaryError instanceof Error
                ? primaryError.message
                : String(primaryError),
            modelId: deps.modelId,
            requestId,
            toolName: toolCall.toolName,
          });
          if (deps.repairModel) {
            try {
              repairedArgs = await attemptModelRepair(
                deps.repairModelId ?? "repair-model",
                deps.repairModel
              );
            } catch (fallbackError) {
              logger.warn("Fallback repair model failed", {
                agentType,
                error:
                  fallbackError instanceof Error
                    ? fallbackError.message
                    : String(fallbackError),
                modelId: deps.repairModelId ?? "repair-model",
                requestId,
                toolName: toolCall.toolName,
              });
            }
          }
        }

        if (repairedArgs === undefined || repairedArgs === null) {
          const local = await attemptLocalRepair();
          if (!local.ok) {
            const message = `Deterministic repair failed: ${local.error}`;
            logger.error("Tool call repair failed", {
              agentType,
              error: message,
              modelId: deps.modelId,
              requestId,
              toolName: toolCall.toolName,
            });
            throw new Error(message);
          }
          repairedArgs = local.value;
        }

        const serializedInput =
          typeof repairedArgs === "string"
            ? repairedArgs
            : JSON.stringify(repairedArgs);

        logger.info("Repaired tool call", {
          agentType,
          modelId: deps.modelId,
          requestId,
          toolName: toolCall.toolName,
        });

        return {
          ...toolCall,
          input: serializedInput,
          repairAttempts: repairAttempts + 1,
        };
      } catch (repairError) {
        const normalizedError =
          repairError instanceof Error ? repairError : new Error(String(repairError));
        logger.error("Tool call repair failed", {
          agentType,
          error: normalizedError.message,
          requestId,
          toolName: toolCall.toolName,
        });
        throw normalizedError;
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
    agent,
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
