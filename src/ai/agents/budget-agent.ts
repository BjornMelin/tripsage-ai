/**
 * @fileoverview Budget planning agent using AI SDK v6 ToolLoopAgent.
 *
 * Autonomously researches destinations, gathers pricing data, and generates
 * structured budget allocations through multi-step tool calling with phased
 * tool selection (research → pricing → allocation).
 */

import "server-only";

import {
  combineSearchResults,
  getTravelAdvisory,
  lookupPoiContext,
  webSearchBatch,
} from "@ai/tools";
import type { BudgetPlanRequest } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import type { ToolSet } from "ai";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { buildBudgetPrompt } from "@/prompts/agents";

import { createTripSageAgent } from "./agent-factory";
import type { AgentDependencies, TripSageAgentResult } from "./types";
import { extractAgentParameters } from "./types";

/**
 * Tools available to the budget planning agent with built-in
 * guardrails for caching, rate limiting, and telemetry.
 */
const BUDGET_TOOLS = {
  combineSearchResults,
  getTravelAdvisory,
  lookupPoiContext,
  webSearchBatch,
} satisfies ToolSet;

/**
 * Creates a budget planning agent using AI SDK v6 ToolLoopAgent.
 *
 * Autonomously researches destinations, gathers pricing data, and generates
 * structured budget allocations through phased tool calling (research → pricing → allocation).
 * Uses Output.object() for structured results and prepareStep for dynamic tool selection.
 *
 * @param deps - Runtime dependencies including model and identifiers.
 * @param config - Agent configuration from database.
 * @param input - Validated budget plan request.
 * @returns Configured ToolLoopAgent for budget planning.
 *
 * @example
 * ```typescript
 * const { agent } = createBudgetAgent(deps, config, {
 *   destination: "Tokyo, Japan",
 *   durationDays: 7,
 *   travelStyle: "mid-range",
 * });
 * return agent.stream({ prompt: "Plan my budget" });
 * ```
 */
export function createBudgetAgent(
  deps: AgentDependencies,
  config: AgentConfig,
  input: BudgetPlanRequest
): TripSageAgentResult<typeof BUDGET_TOOLS> {
  const params = extractAgentParameters(config);
  const instructions = buildBudgetPrompt(input);

  // Token budgeting: clamp max output tokens based on prompt length
  const userPrompt = `Generate a budget plan and summarize. Always return JSON with schemaVersion="budget.v1" and allocations[]. Parameters: ${JSON.stringify(
    input
  )}`;
  const schemaMessage: ChatMessage = { content: userPrompt, role: "user" };
  const clampMessages: ChatMessage[] = [
    { content: instructions, role: "system" },
    schemaMessage,
  ];
  const { maxTokens } = clampMaxTokens(clampMessages, params.maxTokens, deps.modelId);

  return createTripSageAgent<typeof BUDGET_TOOLS>(deps, {
    agentType: "budgetPlanning",
    defaultMessages: [schemaMessage],
    instructions,
    maxOutputTokens: maxTokens,
    maxSteps: params.maxSteps,
    name: "Budget Planning Agent",
    // Note: For structured output, pass Output.object({ schema: budgetPlanResultSchema })
    // when calling agent.generate() or agent.stream()
    // Phased tool selection for budget workflow
    prepareStep: ({ stepNumber }) => {
      // Phase 1 (steps 0-3): Research destination costs and advisories
      if (stepNumber <= 3) {
        return {
          activeTools: ["webSearchBatch", "getTravelAdvisory", "lookupPoiContext"],
        };
      }
      // Phase 2 (steps 4+): Combine and finalize budget allocation
      return {
        activeTools: ["combineSearchResults", "lookupPoiContext"],
      };
    },
    temperature: params.temperature,
    tools: BUDGET_TOOLS,
    topP: params.topP,
  });
}

/** Exported type for the budget agent's tool set. */
export type BudgetAgentTools = typeof BUDGET_TOOLS;
