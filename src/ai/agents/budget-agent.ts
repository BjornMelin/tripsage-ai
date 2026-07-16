/**
 * @fileoverview Budget planning agent using AI SDK v7 ToolLoopAgent.
 */

import "server-only";

import {
  combineSearchResults,
  getTravelAdvisory,
  placeDetails,
  searchPlaces,
  webSearchBatch,
} from "@ai/tools";
import type { BudgetPlanRequest } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import type { ToolSet } from "ai";
import { buildBudgetPrompt } from "@/prompts/agents";

import { createTripSageAgent } from "./agent-factory";
import type { AgentDependencies, TripSageAgentResult } from "./types";
import { extractAgentParameters, prepareSchemaPrompt } from "./types";

/**
 * Tools available to the budget planning agent with built-in
 * guardrails for caching, rate limiting, and telemetry.
 */
const BUDGET_TOOLS = {
  combineSearchResults,
  getTravelAdvisory,
  searchPlaceDetails: placeDetails,
  searchPlaces,
  webSearchBatch,
} satisfies ToolSet;

/**
 * Creates a budget planning agent using AI SDK v7 ToolLoopAgent.
 *
 * Autonomously researches destinations, gathers pricing data, and generates
 * structured budget allocations through phased tool calling (research → pricing → allocation).
 * Encourages schema-versioned JSON payloads in the assistant text (schema cards) for UI rendering.
 *
 * @param deps - Runtime dependencies including model and identifiers.
 * @param config - Agent configuration from database.
 * @param input - Validated budget plan request.
 * @returns Configured agent and canonical UI messages for budget planning.
 *
 * @example
 * ```typescript
 * const { agent, uiMessages } = createBudgetAgent(deps, config, {
 *   budgetCap: 2500,
 *   destination: "Tokyo, Japan",
 *   durationDays: 7,
 *   preferredCurrency: "USD",
 *   travelers: 2,
 * });
 * return createAgentUIStreamResponse({ agent, uiMessages });
 * ```
 */
export function createBudgetAgent(
  deps: AgentDependencies,
  config: AgentConfig,
  input: BudgetPlanRequest
): TripSageAgentResult<typeof BUDGET_TOOLS> {
  const params = extractAgentParameters(config);
  const instructions = buildBudgetPrompt();

  const { maxOutputTokens, uiMessages } = prepareSchemaPrompt({
    instructions,
    maxOutputTokens: params.maxOutputTokens,
    modelId: deps.modelId,
    userPrompt: `Generate a budget plan and summarize. Always return JSON with schemaVersion="budget.v1" and allocations[]. Parameters: ${JSON.stringify(
      input
    )}`,
  });

  return createTripSageAgent<typeof BUDGET_TOOLS>(deps, {
    agentType: "budgetPlanning",
    instructions,
    maxOutputTokens,
    name: "Budget Planning Agent",
    // Phased tool selection for budget workflow
    prepareStep: ({ stepNumber }) => {
      // Phase 1 (steps 0-3): Research destination costs and advisories
      if (stepNumber <= 3) {
        return {
          activeTools: [
            "webSearchBatch",
            "getTravelAdvisory",
            "searchPlaces",
            "searchPlaceDetails",
          ],
        };
      }
      // Phase 2 (steps 4+): Combine and finalize budget allocation
      return {
        activeTools: ["combineSearchResults", "searchPlaces", "searchPlaceDetails"],
      };
    },
    stepLimit: params.stepLimit,
    temperature: params.temperature,
    tools: BUDGET_TOOLS,
    topP: params.topP,
    uiMessages,
  });
}
