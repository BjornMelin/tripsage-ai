/**
 * @fileoverview Type definitions for TripSage AI agents using ToolLoopAgent.
 *
 * Defines configuration, dependencies, and result types for agent creation
 * and execution.
 */

import "server-only";

import type { AgentWorkflowKind } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import type {
  FlexibleSchema,
  GenerateTextOnStepFinishCallback,
  InferAgentUIMessage,
  LanguageModel,
  ModelMessage,
  Output,
  PrepareStepFunction,
  StopCondition,
  ToolLoopAgent,
  ToolSet,
} from "ai";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import type { ChatMessage } from "@/lib/tokens/budget";

// Re-export AI SDK types for downstream consumers
export type {
  FlexibleSchema,
  GenerateTextOnStepFinishCallback,
  InferAgentUIMessage,
  ModelMessage,
  PrepareStepFunction,
  StopCondition,
  ToolLoopAgent,
  ToolSet,
};

export type StructuredOutput<OutputType> = ReturnType<typeof Output.object<OutputType>>;

/** Dependencies required for agent creation and execution. */
export interface AgentDependencies {
  /** Resolved language model for the agent. */
  model: LanguageModel;

  /** Optional dedicated model for structured repair tasks. */
  repairModel?: LanguageModel;

  /** Model identifier for logging and token counting. */
  modelId: string;

  /** Optional identifier for the repair model. */
  repairModelId?: string;

  /** Stable identifier for rate limiting (user ID or hashed IP). */
  identifier: string;

  /** Optional user ID for user-scoped tool operations. */
  userId?: string;

  /** Optional session ID for memory persistence. */
  sessionId?: string;

  /** Optional Supabase client for database operations. */
  supabase?: TypedServerSupabase;

  /** Optional abort signal for request cancellation. */
  abortSignal?: AbortSignal;
}

/**
 * Prepare call function signature. Called before agent execution to modify settings.
 *
 * @template OptionsT - Call options type from callOptionsSchema.
 * @template ToolsT - Tool set type for the agent.
 */
export type PrepareCallFunction<
  OptionsT = unknown,
  ToolsT extends ToolSet = ToolSet,
> = (context: {
  options: OptionsT;
  instructions: string;
  tools: ToolsT;
  model: LanguageModel;
}) => Promise<Partial<PrepareCallResult<ToolsT>>> | Partial<PrepareCallResult<ToolsT>>;

/** Result type for prepareCall function. */
export interface PrepareCallResult<ToolsT extends ToolSet = ToolSet> {
  /** Modified system instructions. */
  instructions?: string;
  /** Modified tool set. */
  tools?: ToolsT;
  /** Modified model. */
  model?: LanguageModel;
  /** Active tools subset. */
  activeTools?: Array<keyof ToolsT & string>;
  /** Tool choice override. */
  toolChoice?: "auto" | "none" | "required" | { type: "tool"; toolName: string };
}

/**
 * Configuration for creating a TripSage agent.
 *
 * Combines runtime dependencies with agent-specific configuration
 * for ToolLoopAgent instantiation.
 */
export interface TripSageAgentConfig<
  ToolsType extends ToolSet = ToolSet,
  CallOptionsType = never,
  // biome-ignore lint/correctness/noUnusedVariables: OutputType kept for documentation/future use
  OutputType = unknown,
> {
  /** Unique agent type identifier. */
  agentType: AgentWorkflowKind;

  /** Human-readable agent name for logging. */
  name: string;

  /** System instructions for the agent. */
  instructions: string;

  /** Tools available to the agent. */
  tools: ToolsType;

  /**
   * Default conversation messages to send with the agent.
   * Must include the user prompt instructing the model to return
   * the correct schemaVersion payload.
   */
  defaultMessages: ChatMessage[];

  /** Maximum tool execution steps (used with stepCountIs). */
  maxSteps?: number;

  /** Maximum output tokens (after clamping). */
  maxOutputTokens?: number;

  /** Temperature for generation (0-1). */
  temperature?: number;

  /** Top-p nucleus sampling parameter. */
  topP?: number;

  /**
   * Schema for type-safe call options.
   * When provided, options are required when calling generate() or stream().
   */
  callOptionsSchema?: FlexibleSchema<CallOptionsType>;

  /**
   * Prepare call function for dynamic configuration.
   * Called before agent execution to modify settings.
   */
  prepareCall?: PrepareCallFunction<CallOptionsType, ToolsType>;

  /**
   * Prepare step function for per-step configuration.
   * Called before each step to modify settings.
   */
  prepareStep?: PrepareStepFunction<ToolsType>;

  /** Callback invoked after each agent step completes. */
  onStepFinish?: GenerateTextOnStepFinishCallback<ToolsType>;

  /**
   * Structured output specification.
   *
   * Stored in config but not passed to ToolLoopAgent constructor.
   * Pass output when calling agent.generate({ output }) or agent.stream({ output }).
   */
  output?: ReturnType<typeof Output.object>;

  /**
   * Active tools subset for this agent.
   * Limits which tools are available to the model.
   */
  activeTools?: Array<keyof ToolsType & string>;

  /**
   * Custom stop conditions beyond stepCountIs().
   * Can be a single condition or array of conditions.
   */
  stopWhen?: StopCondition<ToolsType> | Array<StopCondition<ToolsType>>;
}

/** Result type for agent creation. Contains the configured ToolLoopAgent instance. */
export interface TripSageAgentResult<
  TagentTools extends ToolSet = ToolSet,
  CallOptionsType = never,
  OutputType = unknown,
> {
  /** The configured ToolLoopAgent instance. */
  agent: ToolLoopAgent<CallOptionsType, TagentTools, StructuredOutput<OutputType>>;

  /** Agent type identifier for routing and logging. */
  agentType: AgentWorkflowKind;

  /** Resolved model identifier. */
  modelId: string;

  /** Default schema-enforcing messages to stream with the agent. */
  defaultMessages: ChatMessage[];
}

/** Type helper for inferring UI message types from a TripSage agent. */
// biome-ignore lint/style/useNamingConvention: TypeScript generic convention
export type InferTripSageUIMessage<TAgent extends ToolLoopAgent> =
  InferAgentUIMessage<TAgent>;

/** Factory function signature for creating workflow-specific agents. */
// biome-ignore lint/style/useNamingConvention: TypeScript generic convention
export type AgentFactory<TInput, TagentTools extends ToolSet = ToolSet> = (
  deps: AgentDependencies,
  config: AgentConfig,
  input: TInput
) => TripSageAgentResult<TagentTools>;

/** Metadata for agent execution tracking. */
export interface AgentExecutionMeta {
  /** Unique request identifier. */
  requestId: string;

  /** Agent type being executed. */
  agentType: AgentWorkflowKind;

  /** Model identifier used. */
  modelId: string;

  /** Provider name (e.g., "openai", "anthropic"). */
  provider?: string;

  /** Start timestamp in milliseconds. */
  startedAt: number;

  /** Optional user identifier. */
  userId?: string;

  /** Optional session identifier. */
  sessionId?: string;
}

/** Common agent parameters extracted from AgentConfig. */
export interface AgentParameters {
  /** Maximum output tokens. */
  maxTokens: number;

  /** Temperature for generation. */
  temperature: number;

  /** Top-p nucleus sampling. */
  topP?: number;

  /** Maximum tool execution steps. */
  maxSteps: number;
}

/**
 * Extracts typed agent parameters from AgentConfig with defaults.
 *
 * @param config - Agent configuration from database.
 * @returns Typed agent parameters with sensible defaults.
 */
export function extractAgentParameters(config: AgentConfig): AgentParameters {
  const params = config.parameters;
  return {
    maxSteps:
      "maxSteps" in params && typeof params.maxSteps === "number"
        ? params.maxSteps
        : 10,
    maxTokens:
      "maxTokens" in params && typeof params.maxTokens === "number"
        ? params.maxTokens
        : 4096,
    temperature:
      "temperature" in params && typeof params.temperature === "number"
        ? params.temperature
        : 0.3,
    topP: "topP" in params && typeof params.topP === "number" ? params.topP : undefined,
  };
}
