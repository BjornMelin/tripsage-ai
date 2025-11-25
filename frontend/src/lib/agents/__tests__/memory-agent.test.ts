/** @vitest-environment node */

import type { MemoryUpdateRequest } from "@schemas/agents";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { persistMemoryRecords } from "@/lib/agents/memory-agent";

const createAiToolMock = vi.hoisted(() =>
  vi
    .fn()
    .mockImplementation(
      ({ execute }: { execute: (...args: unknown[]) => Promise<unknown> }) => ({
        description: "mock tool",
        execute,
        inputSchema: z.object({}),
        name: "mock",
      })
    )
);

vi.mock("@ai/lib/tool-factory", () => ({
  createAiTool: createAiToolMock,
}));

// Hoist spies so they are available to vi.mock factory
const hoisted = vi.hoisted(() => ({
  executeSpy: vi.fn().mockImplementation(() => ({
    createdAt: new Date().toISOString(),
    id: Math.floor(Math.random() * 1000),
  })),
}));

// Keep actual schema exports from the real module (needed by guardrails)
vi.mock("@ai/tools/memory", async () => {
  const actual = await vi.importActual<typeof import("@ai/tools")>("@ai/tools");
  return {
    ...actual,
  };
});

vi.mock("@ai/tools", () => ({
  toolRegistry: {
    addConversationMemory: {
      description: "mocked addConversationMemory",
      execute: hoisted.executeSpy,
      inputSchema: z.object({ category: z.string().optional(), content: z.string() }),
    },
  },
}));

describe("persistMemoryRecords", () => {
  beforeEach(() => {
    createAiToolMock.mockClear();
    hoisted.executeSpy.mockClear();
  });

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
      }),
      expect.objectContaining({ toolCallId: "memory-add-0" })
    );
    expect(hoisted.executeSpy).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({ content: "Allergies: peanuts" }),
      expect.objectContaining({ toolCallId: "memory-add-1" })
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
