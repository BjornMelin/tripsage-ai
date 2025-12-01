/**
 * @fileoverview Type definitions for TripSage AI agents using AI SDK v6 ToolLoopAgent.
 *
 * Defines configuration, dependencies, and result types for agent creation
 * and execution. Agents use ToolLoopAgent for autonomous multi-step reasoning
 * with tool calling.
 */

import "server-only";

import type { AgentWorkflowKind } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import type { InferAgentUIMessage, LanguageModel, ToolLoopAgent, ToolSet } from "ai";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import type { ChatMessage } from "@/lib/tokens/budget";

/**
 * Dependencies required for agent creation and execution.
 *
 * All dependencies are injected to enable deterministic testing and
 * avoid module-scope state per AGENTS.md requirements.
 */
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
 * Configuration for creating a TripSage agent.
 *
 * Combines runtime dependencies with agent-specific configuration
 * for ToolLoopAgent instantiation.
 */
// biome-ignore lint/style/useNamingConvention: TypeScript generic convention
export interface TripSageAgentConfig<TTools extends ToolSet = ToolSet> {
  /** Unique agent type identifier. */
  agentType: AgentWorkflowKind;

  /** Human-readable agent name for logging. */
  name: string;

  /** System instructions for the agent. */
  instructions: string;

  /** Tools available to the agent. */
  tools: TTools;

  /**
   * Schema-enforcing default conversation to send with the agent.
   * Must include the user prompt that instructs the model to return
   * the correct schemaVersion payload for downstream consumers.
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
}

/**
 * Result of agent creation containing the configured ToolLoopAgent instance.
 *
 * Uses ToolSet as the base type for flexibility across different agent configurations.
 */
export interface TripSageAgentResult<TagentTools extends ToolSet = ToolSet> {
  /** The configured ToolLoopAgent instance. */
  agent: ToolLoopAgent<never, TagentTools>;

  /** Agent type identifier for routing and logging. */
  agentType: AgentWorkflowKind;

  /** Resolved model identifier. */
  modelId: string;

  /** Default schema-enforcing messages to stream with the agent. */
  defaultMessages: ChatMessage[];
}

/**
 * Type helper for inferring UI message types from a TripSage agent.
 *
 * @template TAgent - The ToolLoopAgent type to infer messages from.
 */
// biome-ignore lint/style/useNamingConvention: TypeScript generic convention
export type InferTripSageUIMessage<TAgent extends ToolLoopAgent> =
  InferAgentUIMessage<TAgent>;

/**
 * Factory function signature for creating workflow-specific agents.
 *
 * @template TInput - Input type for the agent workflow.
 */
// biome-ignore lint/style/useNamingConvention: TypeScript generic convention
export type AgentFactory<TInput, TagentTools extends ToolSet = ToolSet> = (
  deps: AgentDependencies,
  config: AgentConfig,
  input: TInput
) => TripSageAgentResult<TagentTools>;

/**
 * Metadata for agent execution tracking and observability.
 */
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

/**
 * Common agent parameters extracted from AgentConfig.
 */
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
