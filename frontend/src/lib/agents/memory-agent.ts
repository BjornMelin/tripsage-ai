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

import { runWithGuardrails } from "@/lib/agents/runtime";
import { buildRateLimit } from "@/lib/ratelimit/config";
import { toolRegistry } from "@/lib/tools";
import { addConversationMemoryInputSchema } from "@/lib/tools/memory";
import type { MemoryUpdateRequest } from "@/schemas/agents";

// Note: no wrapped tools are exposed here; we execute persistence directly with guardrails.

/**
 * Execute the memory agent with AI SDK v6 streaming.
 *
 * Builds system instructions and messages, wraps core tools with guardrails,
 * and streams a model-guided confirmation message for memory writes.
 *
 * @param deps Language model and request-scoped utilities.
 * @param input Validated memory update request.
 * @returns AI SDK stream result for UI consumption.
 */
export function runMemoryAgent(
  deps: {
    model: LanguageModel;
    identifier: string;
  },
  input: MemoryUpdateRequest
) {
  return persistAndSummarize(deps, input);
}

type PersistOutcome = {
  successes: Array<{ id: number; createdAt: string; category: string }>;
  failures: Array<{ index: number; error: string }>;
};

/**
 * Persist all memory records deterministically, then stream a short summary.
 */
async function persistAndSummarize(
  deps: { model: LanguageModel; identifier: string },
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

  return streamText({
    model: deps.model,
    prompt: `Summarize the following memory write results for the user in one or two short sentences. Do not restate raw memory contents. Results: ${summaryJson}`,
    system:
      "You are a concise memory assistant. A batch of user memories was written. Summarize results briefly without echoing private content.",
    temperature: 0.1,
  });
}

/**
 * Persist memory records with guardrails and return per-record outcomes.
 * Exported for unit testing.
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

  const memoryTool = toolRegistry.addConversationMemory as unknown as {
    execute: (params: unknown) => Promise<unknown>;
  };

  // Guardrailed executor similar to buildMemoryTools but direct
  const executeAddMemory = async (params: unknown) => {
    const { result } = await runWithGuardrails(
      {
        cache: { hashInput: true, key: "agent:memory:add", ttlSeconds: 60 * 5 },
        parametersSchema: addConversationMemoryInputSchema,
        rateLimit: buildRateLimit("memoryUpdate", identifier),
        tool: "addConversationMemory",
        workflow: "memoryUpdate",
      },
      params,
      async (validated) => memoryTool.execute(validated)
    );
    return result as { id: number; createdAt: string };
  };

  await Promise.all(
    records.map(async (r, index) => {
      try {
        const payload = {
          // default category enforcement handled by schema
          category: r.category,
          content: r.content,
        };
        const res = await executeAddMemory(payload);
        successes.push({
          category: r.category ?? "other",
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
