/**
 * @fileoverview Memory update agent using AI SDK v6 streaming.
 *
 * Wraps memory tools (addConversationMemory) with guardrails (caching, rate
 * limiting) and executes streaming text generation to confirm memory writes.
 * Returns structured confirmation messages.
 */

import "server-only";

import type { LanguageModel } from "ai";
import { streamText } from "ai";
import type { z } from "zod";

import { createAiTool } from "@/lib/ai/tool-factory";
import { buildRateLimit } from "@/lib/ratelimit/config";
import type { MemoryUpdateRequest } from "@/lib/schemas/agents";
import type { ChatMessage } from "@/lib/tokens/budget";
import { clampMaxTokens } from "@/lib/tokens/budget";
import { toolRegistry } from "@/lib/tools";
import { TOOL_ERROR_CODES } from "@/lib/tools/errors";
import { addConversationMemoryInputSchema } from "@/lib/tools/memory";

// Note: no wrapped tools are exposed here; we execute persistence directly with guardrails.

/**
 * Execute the memory agent with AI SDK v6 streaming.
 *
 * Builds system instructions and messages, wraps core tools with guardrails,
 * and streams a model-guided confirmation message for memory writes.
 *
 * @param deps Language model, model identifier, and request-scoped utilities.
 * @param input Validated memory update request.
 * @returns AI SDK stream result for UI consumption.
 */
export function runMemoryAgent(
  deps: {
    model: LanguageModel;
    modelId: string;
    identifier: string;
  },
  input: MemoryUpdateRequest
) {
  return persistAndSummarize(deps, input);
}

/** Result of a memory persistence operation. */
type PersistOutcome = {
  successes: Array<{ id: string; createdAt: string; category: string }>;
  failures: Array<{ index: number; error: string }>;
};

/** Type alias for the input schema of the addConversationMemory tool. */
type AddConversationMemoryInput = z.infer<typeof addConversationMemoryInputSchema>;

/** Valid memory category values accepted by the schema. */
const MEMORY_CATEGORY_VALUES: readonly AddConversationMemoryInput["category"][] = [
  "user_preference",
  "trip_history",
  "search_pattern",
  "conversation_context",
  "other",
] as const;

/**
 * Normalizes a memory category string to a valid schema value.
 *
 * Validates the category against allowed values and defaults to "other"
 * if the provided category is invalid or undefined.
 *
 * @param category - Raw category string from user input.
 * @returns Validated category value or "other" as fallback.
 */
function normalizeMemoryCategory(
  category?: string
): AddConversationMemoryInput["category"] {
  if (category && (MEMORY_CATEGORY_VALUES as readonly string[]).includes(category)) {
    return category as AddConversationMemoryInput["category"];
  }
  return "other";
}

/**
 * Persists memory records and streams a summary of the operation.
 *
 * Executes persistence operations in parallel, aggregates statistics by category,
 * and streams model-generated summary. Uses token budgeting for concise summaries.
 *
 * @param deps - Language model and request-scoped dependencies.
 * @param input - Validated memory update request with records to persist.
 * @returns AI SDK stream result with memory operation summary.
 */
async function persistAndSummarize(
  deps: { model: LanguageModel; modelId: string; identifier: string },
  input: MemoryUpdateRequest
) {
  const outcome = await persistMemoryRecords(deps.identifier, input);

  const successCount = outcome.successes.length;
  const failureCount = outcome.failures.length;
  const byCategory = outcome.successes.reduce<Record<string, number>>((acc, r) => {
    acc[r.category] = (acc[r.category] ?? 0) + 1;
    return acc;
  }, {});

  const summaryJson = JSON.stringify({
    categories: byCategory,
    failed: failureCount,
    stored: successCount,
  });

  const systemPrompt =
    "You are a concise memory assistant. A batch of user memories was written. Summarize results briefly without echoing private content.";
  const userPrompt = `Summarize the following memory write results for the user in one or two short sentences. Do not restate raw memory contents. Results: ${summaryJson}`;

  // Token budgeting: clamp max output tokens based on prompt length
  const messages: ChatMessage[] = [
    { content: systemPrompt, role: "system" },
    { content: userPrompt, role: "user" },
  ];
  const desiredMaxTokens = 512; // Short summary for memory confirmations
  const { maxTokens } = clampMaxTokens(messages, desiredMaxTokens, deps.modelId);

  return streamText({
    maxOutputTokens: maxTokens,
    messages: [
      { content: systemPrompt, role: "system" },
      { content: userPrompt, role: "user" },
    ],
    model: deps.model,
    temperature: 0.1,
  });
}

/**
 * Persists multiple memory records with guardrails applied.
 *
 * Creates guardrailed tools for each record, executes operations in parallel,
 * collects outcomes. Validates limits, normalizes categories, handles errors gracefully.
 *
 * @param identifier - User or session identifier for rate limiting.
 * @param input - Validated memory update request with records to persist.
 * @returns Promise resolving to operation outcomes (successes and failures).
 * @throws {Error} When record count exceeds maximum allowed (25).
 */
export async function persistMemoryRecords(
  identifier: string,
  input: MemoryUpdateRequest
): Promise<PersistOutcome> {
  const records = input.records ?? [];
  if (records.length > 25) {
    throw new Error("too_many_records: max 25 per request");
  }

  const failures: PersistOutcome["failures"] = [];
  const successes: PersistOutcome["successes"] = [];

  type ToolBinding = {
    description?: string;
    execute?: (params: unknown, callOptions?: unknown) => Promise<unknown> | unknown;
  };
  const memoryTool = toolRegistry.addConversationMemory as ToolBinding | undefined;
  if (!memoryTool?.execute) {
    throw new Error("Tool addConversationMemory missing execute binding");
  }

  const rateLimit = buildRateLimit("memoryUpdate", identifier);
  const guardrailedAddMemory = createAiTool({
    description: memoryTool.description ?? "Add conversation memory",
    execute: async (params, callOptions) => {
      if (typeof memoryTool.execute !== "function") {
        throw new Error("Tool addConversationMemory missing execute binding");
      }
      return (await memoryTool.execute(params, callOptions)) as {
        createdAt: string;
        id: string;
      };
    },
    guardrails: {
      cache: {
        hashInput: true,
        key: () => "agent:memory:add",
        namespace: "",
        ttlSeconds: 60 * 5,
      },
      rateLimit: {
        errorCode: TOOL_ERROR_CODES.toolRateLimited,
        identifier: () => rateLimit.identifier,
        limit: rateLimit.limit,
        prefix: "ratelimit:agent:memory:add",
        window: rateLimit.window,
      },
      telemetry: {
        workflow: "memoryUpdate",
      },
    },
    inputSchema: addConversationMemoryInputSchema,
    name: "addConversationMemory",
  });

  const guardrailedExecute = guardrailedAddMemory.execute;
  if (!guardrailedExecute) {
    throw new Error("Guarded addConversationMemory tool missing execute binding");
  }

  await Promise.all(
    records.map(async (r, index) => {
      try {
        const normalizedCategory = normalizeMemoryCategory(r.category);
        const payload: AddConversationMemoryInput = {
          category: normalizedCategory,
          content: r.content,
        };
        const res = (await guardrailedExecute(payload, {
          messages: [],
          toolCallId: `memory-add-${index}`,
        })) as { createdAt: string; id: string };
        successes.push({
          category: normalizedCategory,
          createdAt: res.createdAt,
          id: res.id,
        });
      } catch (err) {
        failures.push({ error: err instanceof Error ? err.message : "error", index });
      }
    })
  );

  return { failures, successes };
}
