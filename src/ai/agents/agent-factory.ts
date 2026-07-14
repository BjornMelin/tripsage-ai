/**
 * @fileoverview Factory for creating TripSage agents using AI SDK v6 ToolLoopAgent.
 */

import "server-only";

import { buildTimeoutConfig, DEFAULT_AI_TIMEOUT_MS } from "@ai/timeout";
import type { LanguageModel, ToolSet } from "ai";
import {
  asSchema,
  generateText,
  InvalidToolInputError,
  NoSuchToolError,
  Output,
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
const DEFAULT_STEP_LIMIT = 10;

/**
 * Default temperature for agent generation.
 * Slightly lower than default for more consistent planning outputs.
 */
const DEFAULT_TEMPERATURE = 0.3;

/**
 * Creates a TripSage agent using AI SDK v6 ToolLoopAgent.
 *
 * Instantiates a reusable agent for autonomous multi-step reasoning with tool calling.
 * Runs until a stop condition is met (default: stepCountIs(stepLimit)).
 *
 * Supports per-step tool selection and malformed tool-call repair.
 *
 * @typeParam TagentTools - Tool set type for the agent.
 * @param deps - Runtime model and request signal.
 * @param config - Agent configuration including tools and instructions.
 * @returns Configured ToolLoopAgent and its initial UI messages.
 *
 * @example
 * ```typescript
 * const { agent, uiMessages } = createTripSageAgent(deps, {
 *   agentType: "budgetPlanning",
 *   name: "Budget Agent",
 *   instructions: buildBudgetPrompt(input),
 *   tools: budgetTools,
 *   stepLimit: 10,
 *   prepareStep: async ({ stepNumber }) => {
 *     if (stepNumber <= 2) return { activeTools: ['webSearch'] };
 *     return {};
 *   },
 *   uiMessages: [],
 * });
 *
 * return createAgentUIStreamResponse({ agent, uiMessages });
 * ```
 *
 * @see docs/architecture/decisions/adr-0066-ai-sdk-v6-agents-mcp-and-message-persistence.md
 */
export function createTripSageAgent<TagentTools extends ToolSet>(
  deps: AgentDependencies,
  config: TripSageAgentConfig<TagentTools>
): TripSageAgentResult<TagentTools> {
  const {
    agentType,
    instructions,
    maxOutputTokens,
    stepLimit = DEFAULT_STEP_LIMIT,
    name,
    prepareStep,
    temperature = DEFAULT_TEMPERATURE,
    tools,
    topP,
    uiMessages,
  } = config;

  const requestId = secureUuid();

  logger.info(`Creating agent: ${name}`, {
    agentType,
    modelId: deps.modelId,
    requestId,
    stepLimit,
  });

  const agent = new ToolLoopAgent<never, TagentTools>({
    // Prepare step function for per-step configuration
    ...(prepareStep ? { prepareStep } : {}),

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
          const { output: repaired } = await generateText({
            abortSignal: deps.abortSignal,
            // biome-ignore lint/style/useNamingConvention: AI SDK API uses snake_case
            experimental_telemetry: {
              functionId: "agent.tool_repair",
              isEnabled: true,
              metadata: {
                agentType,
                modelId,
                requestId,
                toolName: toolCall.toolName,
              },
            },
            model,
            output: Output.object({ schema: tool.inputSchema }),
            prompt,
            timeout: buildTimeoutConfig(DEFAULT_AI_TIMEOUT_MS),
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
    // biome-ignore lint/style/useNamingConvention: AI SDK API uses snake_case
    experimental_telemetry: {
      functionId: `agent.${agentType}`,
      isEnabled: true,
      metadata: {
        agentType,
        modelId: deps.modelId,
      },
    },
    // Core configuration
    id: `tripsage-${agentType}-${requestId}`,
    instructions,

    // Generation parameters
    maxOutputTokens,
    model: deps.model,
    stopWhen: stepCountIs(stepLimit),
    temperature,
    toolChoice: "auto",
    tools,
    topP,
  });

  return {
    agent,
    uiMessages,
  };
}
