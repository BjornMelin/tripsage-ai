/**
 * @fileoverview Shared types and prompt setup for TripSage AI agents.
 */

import "server-only";

import type { AgentWorkflowKind } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import type {
  LanguageModel,
  SystemModelMessage,
  ToolLoopAgent,
  ToolLoopAgentSettings,
  ToolSet,
  UIMessage,
} from "ai";
import { secureUuid } from "@/lib/security/random";
import { type ChatMessage, clampMaxTokens } from "@/lib/tokens/budget";

/** Dependencies required for agent creation and execution. */
export interface AgentDependencies {
  model: LanguageModel;
  modelId: string;
  userId?: string;
  abortSignal?: AbortSignal;
}

/** Low-cardinality context explicitly selected for AI SDK telemetry. */
export interface AgentRuntimeContext extends Record<string, unknown> {
  agentType: AgentWorkflowKind;
  modelId: string;
}

type FactoryManagedAgentSetting =
  | "experimental_repairToolCall"
  | "experimental_telemetry"
  | "id"
  | "model"
  | "repairToolCall"
  | "runtimeContext"
  | "stopWhen"
  | "telemetry"
  | "toolChoice";

type ConfigurableAgentSettings<ToolsType extends ToolSet> = Omit<
  ToolLoopAgentSettings<never, ToolsType, AgentRuntimeContext>,
  FactoryManagedAgentSetting
>;

/** Configuration shared by the five ToolLoopAgent workflows. */
export type TripSageAgentConfig<ToolsType extends ToolSet = ToolSet> =
  ConfigurableAgentSettings<ToolsType> & {
    agentType: AgentWorkflowKind;
    name: string;
    instructions: string | SystemModelMessage;
    tools: ToolsType;
    uiMessages: UIMessage[];
    stepLimit?: number;
    maxOutputTokens?: number;
    temperature?: number;
    topP?: number;
  };

/** Configured agent and the canonical UI messages used to start its stream. */
export interface TripSageAgentResult<ToolsType extends ToolSet = ToolSet> {
  agent: ToolLoopAgent<never, ToolsType, AgentRuntimeContext>;
  uiMessages: UIMessage[];
}

interface AgentParameters {
  maxOutputTokens: number;
  temperature: number;
  topP?: number;
  stepLimit: number;
}

/**
 * Extracts typed agent parameters from a persisted agent configuration.
 *
 * @param config - Persisted configuration for an agent workflow.
 * @returns Normalized generation and step-limit parameters.
 * @see docs/architecture/decisions/adr-0052-agent-configuration-backend.md
 */
export function extractAgentParameters(config: AgentConfig): AgentParameters {
  const params = config.parameters;
  return {
    maxOutputTokens:
      "maxOutputTokens" in params && typeof params.maxOutputTokens === "number"
        ? params.maxOutputTokens
        : 4096,
    stepLimit:
      "stepLimit" in params && typeof params.stepLimit === "number"
        ? params.stepLimit
        : 10,
    temperature:
      "temperature" in params && typeof params.temperature === "number"
        ? params.temperature
        : 0.3,
    topP: "topP" in params && typeof params.topP === "number" ? params.topP : undefined,
  };
}

/**
 * Builds a valid UI message and computes its safe output-token budget.
 *
 * @param options - Instructions, model, prompt, and requested output-token limit.
 * @returns Canonical UI messages and the clamped output-token budget.
 * @see docs/specs/active/0103-spec-chat-and-agents.md
 */
export function prepareSchemaPrompt(options: {
  instructions: string;
  maxOutputTokens: number;
  modelId: string;
  userPrompt: string;
}): { maxOutputTokens: number; uiMessages: UIMessage[] } {
  const uiMessages: UIMessage[] = [
    {
      id: secureUuid(),
      parts: [{ text: options.userPrompt, type: "text" }],
      role: "user",
    },
  ];
  const tokenMessages: ChatMessage[] = [
    { content: options.instructions, role: "system" },
    { content: options.userPrompt, role: "user" },
  ];
  const { maxOutputTokens } = clampMaxTokens(
    tokenMessages,
    options.maxOutputTokens,
    options.modelId
  );

  return { maxOutputTokens, uiMessages };
}
