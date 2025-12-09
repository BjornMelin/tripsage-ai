/**
 * @fileoverview Mem0 adapter for memory orchestrator.
 *
 * Uses the official mem0ai Node SDK to enrich `fetchContext` intents by
 * retrieving user-specific memories for the current session.
 *
 * This adapter is optional and only enabled when MEM0_API_KEY is configured.
 * Uses MemoryClient for hosted Mem0 service.
 */

import "server-only";

import type { MemoryContextResponse } from "@schemas/chat";
import type {
  MemoryAdapter,
  MemoryAdapterContext,
  MemoryAdapterExecutionResult,
  MemoryIntent,
} from "./orchestrator";

/**
 * Cached Mem0 client wrapper to avoid recreating MemoryClient instances.
 * The client is created once and reused for all memory fetch operations.
 */
let cachedClient: {
  search: (
    query: string,
    options: { userId: string }
  ) => Promise<{
    results: Array<{ memory: string; score?: number }>;
  }>;
} | null = null;

let cachedApiKey: string | undefined;

/**
 * Lazy loader for Mem0 SDK. We avoid importing the package when it is not
 * configured to keep bundles lean in environments without Mem0.
 *
 * The client is cached and reused across requests to avoid unnecessary
 * instantiation and potential connection/resource issues.
 */
async function loadMem0Client(): Promise<{
  search: (
    query: string,
    options: { userId: string }
  ) => Promise<{
    results: Array<{ memory: string; score?: number }>;
  }>;
}> {
  const apiKey = getMem0ApiKey();
  if (!apiKey) {
    throw new Error("MEM0_API_KEY not configured");
  }

  // Reuse cached client if API key hasn't changed
  if (cachedClient && cachedApiKey === apiKey) {
    return cachedClient;
  }

  // Import SDK only when needed
  const { MemoryClient } = await import("mem0ai");
  const client = new MemoryClient({ apiKey });

  // Create and cache the wrapper
  cachedClient = {
    search: async (query: string, options: { userId: string }) => {
      // biome-ignore lint/style/useNamingConvention: Mem0 API expects user_id
      const result = await client.search(query, { user_id: options.userId });
      // Mem0 returns Memory[] array, convert to expected format
      if (Array.isArray(result)) {
        return {
          results: result.map((mem) => ({
            memory: typeof mem === "string" ? mem : String(mem),
            score: 0.5,
          })),
        };
      }
      return { results: [] };
    },
  };
  cachedApiKey = apiKey;

  return cachedClient;
}

function getMem0ApiKey(): string | undefined {
  // Server-side only - never expose to client
  return process.env.MEM0_API_KEY;
}

async function handleFetchContext(
  intent: Extract<MemoryIntent, { type: "fetchContext" }>,
  _ctx: MemoryAdapterContext
): Promise<MemoryAdapterExecutionResult> {
  const apiKey = getMem0ApiKey();
  if (!apiKey) {
    return { status: "skipped" };
  }

  try {
    const client = await loadMem0Client();

    // Use a simple query tying context to the current session.
    const query = `Recall relevant long-term memories for user ${intent.userId}${intent.sessionId ? ` and session ${intent.sessionId}` : ""}.`;

    const searchResult = await client.search(query, {
      userId: intent.userId,
    });

    if (!searchResult.results || searchResult.results.length === 0) {
      return { contextItems: [], status: "ok" };
    }

    const contextItems: MemoryContextResponse[] = searchResult.results.map(
      (result) => ({
        context: result.memory,
        score: result.score ?? 0.5,
        source: "mem0",
      })
    );

    return {
      contextItems,
      status: "ok",
    };
  } catch (error) {
    return {
      error:
        error instanceof Error
          ? `mem0_search_failed:${error.message}`
          : "mem0_search_failed",
      status: "error",
    };
  }
}

/**
 * Create Mem0 adapter if configuration is available.
 *
 * Returns null when Mem0 is not configured so callers can exclude it from
 * the orchestrator pipeline without additional checks.
 */
export function createMem0Adapter(): MemoryAdapter | null {
  const apiKey = getMem0ApiKey();
  if (!apiKey) {
    return null;
  }

  return {
    async handle(
      intent: MemoryIntent,
      ctx: MemoryAdapterContext
    ): Promise<MemoryAdapterExecutionResult> {
      if (intent.type !== "fetchContext") {
        return { status: "skipped" };
      }

      return await handleFetchContext(intent, ctx);
    },
    id: "mem0",
    supportedIntents: ["fetchContext"],
  };
}
