/** @vitest-environment node */

import type { MemoryUpdateRequest } from "@schemas/agents";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";

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

vi.mock("@ai/tools", () => ({
  toolRegistry: {
    addConversationMemory: {
      description: "mocked addConversationMemory",
      execute: hoisted.executeSpy,
      inputSchema: z.object({ category: z.string().optional(), content: z.string() }),
    },
  },
}));

let persistMemoryRecords: typeof import("@ai/agents/memory-agent").persistMemoryRecords;

describe("persistMemoryRecords", () => {
  beforeAll(async () => {
    ({ persistMemoryRecords } = await import("@ai/agents/memory-agent"));
  });
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

    // Assert successes and failures separately
    expect(out.successes).toBeDefined();
    expect(out.successes.length).toBe(2);
    expect(out.failures).toBeDefined();
    expect(out.failures.length).toBe(0);

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
