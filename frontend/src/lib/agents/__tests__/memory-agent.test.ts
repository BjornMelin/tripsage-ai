import { describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { persistMemoryRecords } from "@/lib/agents/memory-agent";
import type { MemoryUpdateRequest } from "@/schemas/agents";

vi.mock("@/lib/cache/upstash", () => ({
  getCachedJson: vi.fn().mockResolvedValue(null),
  setCachedJson: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/telemetry/agents", () => ({
  recordAgentToolEvent: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/redis", () => ({
  getRedis: () => undefined,
}));

// Hoist spies so they are available to vi.mock factory
const hoisted = vi.hoisted(() => ({
  executeSpy: vi.fn().mockImplementation(() => ({
    createdAt: new Date().toISOString(),
    id: Math.floor(Math.random() * 1000),
  })),
}));

// Keep actual schema exports from the real module (needed by guardrails)
vi.mock("@/lib/tools/memory", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/tools/memory")>("@/lib/tools/memory");
  return {
    ...actual,
  };
});

vi.mock("@/lib/tools", () => ({
  toolRegistry: {
    addConversationMemory: {
      description: "mocked addConversationMemory",
      execute: hoisted.executeSpy,
      inputSchema: z.object({ category: z.string().optional(), content: z.string() }),
    },
  },
}));

describe("persistMemoryRecords", () => {
  it("writes one call per record with correct payloads", async () => {
    const req: MemoryUpdateRequest = {
      records: [
        { category: "user_preference", content: "I prefer window seats" },
        { content: "Allergies: peanuts" }, // category defaults to other
      ],
    };

    const out = await persistMemoryRecords("user-123", req);
    expect(out.successes.length + out.failures.length).toBe(2);
    expect(hoisted.executeSpy).toHaveBeenCalledTimes(2);
    expect(hoisted.executeSpy).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        category: "user_preference",
        content: "I prefer window seats",
      })
    );
    expect(hoisted.executeSpy).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({ content: "Allergies: peanuts" })
    );
  });

  it("rejects large batches (>25)", async () => {
    const big: MemoryUpdateRequest = {
      records: Array.from({ length: 26 }, (_, i) => ({ content: `c-${i}` })),
    };
    await expect(persistMemoryRecords("user-1", big)).rejects.toThrow(
      /too_many_records/
    );
  });
});
