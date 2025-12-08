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

import type { LanguageModel, StopCondition, SystemModelMessage, ToolSet } from "ai";
import {
  asSchema,
  generateText,
  InvalidToolInputError,
  NoSuchToolError,
  Output,
  stepCountIs,
  ToolLoopAgent,
} from "ai";
import {
  hasInjectionRisk,
  isFilteredValue,
  sanitizeWithInjectionDetection,
} from "@/lib/security/prompt-sanitizer";
import { secureUuid } from "@/lib/security/random";
import { createServerLogger } from "@/lib/telemetry/logger";
import { recordTelemetryEvent } from "@/lib/telemetry/span";

import { normalizeInstructions } from "./chat-agent";
import type {
  AgentDependencies,
  StructuredOutput,
  TripSageAgentConfig,
  TripSageAgentResult,
} from "./types";

const logger = createServerLogger("agent-factory");

/**
 * Default maximum tool execution steps for agents.
 * Allows complex multi-tool workflows while preventing infinite loops.
 */
const DEFAULT_MAX_STEPS = 10;

/** Maximum number of tool repair attempts to avoid runaway costs. */
const MAX_TOOL_REPAIR_ATTEMPTS = 2;

/**
 * Default temperature for agent generation.
 * Slightly lower than default for more consistent planning outputs.
 */
const DEFAULT_TEMPERATURE = 0.3;

/**
 * Creates a TripSage agent using AI SDK v6 ToolLoopAgent.
 *
 * Instantiates a reusable agent for autonomous multi-step reasoning with tool calling.
 * Runs until a stop condition is met (default: stepCountIs(maxSteps)).
 *
 * Supports dynamic configuration via callOptionsSchema/prepareCall, per-step
 * tool/model selection via prepareStep, step-level telemetry via onStepFinish,
 * structured output, tool filtering, and custom stop conditions.
 *
 * @template TTools - Tool set type for the agent.
 * @template CallOptionsType - Call options type from callOptionsSchema.
 * @template OutputType - Output type for structured results.
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
 *   prepareStep: async ({ stepNumber }) => {
 *     if (stepNumber <= 2) return { activeTools: ['webSearch'] };
 *     return {};
 *   },
 * });
 *
 * // Stream the agent response
 * const stream = agent.stream({ prompt: userMessage });
 * ```
 */
export function createTripSageAgent<
  TagentTools extends ToolSet,
  CallOptionsType = never,
  OutputType = unknown,
>(
  deps: AgentDependencies,
  config: TripSageAgentConfig<TagentTools, CallOptionsType, OutputType>
): TripSageAgentResult<TagentTools, CallOptionsType, OutputType> {
  const {
    activeTools,
    agentType,
    callOptionsSchema,
    defaultMessages,
    instructions,
    maxOutputTokens,
    maxSteps = DEFAULT_MAX_STEPS,
    name,
    onStepFinish: configOnStepFinish,
    // Note: output is NOT passed to ToolLoopAgent constructor.
    // It should be passed when calling agent.generate() or agent.stream().
    output: _,
    prepareCall,
    prepareStep,
    stopWhen: customStopWhen,
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

  // Build stop conditions: combine default step count with custom conditions
  const buildStopConditions = ():
    | StopCondition<TagentTools>
    | StopCondition<TagentTools>[] => {
    const defaultCondition = stepCountIs(maxSteps);
    if (!customStopWhen) {
      return defaultCondition;
    }
    const customConditions = Array.isArray(customStopWhen)
      ? customStopWhen
      : [customStopWhen];
    return [defaultCondition, ...customConditions];
  };

  // Wrap onStepFinish to add telemetry
  const wrappedOnStepFinish: typeof configOnStepFinish = configOnStepFinish
    ? (stepResult) => {
        // Record telemetry event for step completion
        recordTelemetryEvent("agent.step.finish", {
          attributes: {
            agentType,
            hasToolCalls: stepResult.toolCalls.length > 0,
            modelId: deps.modelId,
            requestId,
            toolCallCount: stepResult.toolCalls.length,
          },
        });
        return configOnStepFinish(stepResult);
      }
    : undefined;

  const agent = new ToolLoopAgent<
    CallOptionsType,
    TagentTools,
    StructuredOutput<OutputType>
  >({
    // Call options schema for type-safe runtime configuration
    ...(callOptionsSchema ? { callOptionsSchema } : {}),

    // Prepare call function for dynamic configuration
    // Note: prepareCall must return the full settings object, not partial
    ...(prepareCall
      ? {
          prepareCall: async (params) => {
            // Normalize instructions to handle potential array input
            type InstructionValue = string | SystemModelMessage;
            const normalizeInstructionInput = (
              input: InstructionValue | Array<InstructionValue | undefined> | undefined
            ): string => {
              if (Array.isArray(input)) {
                return input
                  .map((instruction) => normalizeInstructions(instruction ?? ""))
                  .join("\n");
              }
              return normalizeInstructions(input ?? "");
            };

            const hasParamsInstructions = Object.hasOwn(params, "instructions");

            const normalizedInstructions = normalizeInstructionInput(
              hasParamsInstructions
                ? (params.instructions as
                    | InstructionValue
                    | InstructionValue[]
                    | undefined)
                : (instructions as InstructionValue | InstructionValue[] | undefined)
            );

            // Sanitize instructions to prevent prompt injection attacks
            const sanitizedInstructions = sanitizeWithInjectionDetection(
              normalizedInstructions,
              5000 // Reasonable limit for agent instructions
            );

            // Security monitoring: log if injection patterns were detected
            if (hasInjectionRisk(normalizedInstructions)) {
              logger.warn("Prompt injection patterns detected in agent instructions", {
                hasFilteredContent: isFilteredValue(sanitizedInstructions),
                identifier: deps.identifier,
                modelId: deps.modelId,
              });
              recordTelemetryEvent("security.prompt_injection_detected", {
                attributes: {
                  identifier: deps.identifier,
                  modelId: deps.modelId,
                  wasFiltered: isFilteredValue(sanitizedInstructions),
                },
                level: "warning",
              });
            }

            const result = await prepareCall({
              instructions: sanitizedInstructions,
              model: params.model ?? deps.model,
              options: params.options as CallOptionsType,
              tools: params.tools ?? tools,
            });

            const hasResultInstructions = Object.hasOwn(result, "instructions");
            // Return merged settings - prepareCall can override any setting
            return {
              ...params,
              instructions: hasResultInstructions
                ? (result.instructions ?? "")
                : sanitizedInstructions,
              ...(result.model ? { model: result.model } : {}),
              ...(result.tools ? { tools: result.tools } : {}),
              ...(result.activeTools ? { activeTools: result.activeTools } : {}),
              ...(result.toolChoice ? { toolChoice: result.toolChoice } : {}),
            };
          },
        }
      : {}),

    // Prepare step function for per-step configuration
    ...(prepareStep ? { prepareStep } : {}),

    // Step finish callback with telemetry
    ...(wrappedOnStepFinish ? { onStepFinish: wrappedOnStepFinish } : {}),

    // Active tools subset
    ...(activeTools ? { activeTools } : {}),

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
          const { output: repaired } = await generateText({
            model,
            output: Output.object({ schema: tool.inputSchema }),
            prompt,
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
    stopWhen: buildStopConditions(),
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
