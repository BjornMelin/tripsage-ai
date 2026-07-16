/** @vitest-environment node */

import type { MemoryUpdateRequest } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { createMockModel } from "@/test/ai-sdk/mock-model";

const clampMaxTokensMock = vi.hoisted(() =>
  vi.fn(() => ({ maxOutputTokens: 256, reasons: [] }))
);
const streamTextMock = vi.hoisted(() =>
  vi.fn(() => ({ stream: new ReadableStream() }))
);

vi.mock("ai", async (importOriginal) => ({
  ...(await importOriginal<typeof import("ai")>()),
  streamText: streamTextMock,
}));

vi.mock("@/lib/tokens/budget", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/tokens/budget")>()),
  clampMaxTokens: clampMaxTokensMock,
}));

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
    id: "memory-1",
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
let runMemoryAgent: typeof import("@ai/agents/memory-agent").runMemoryAgent;

describe("persistMemoryRecords", () => {
  beforeAll(async () => {
    ({ persistMemoryRecords, runMemoryAgent } = await import(
      "@ai/agents/memory-agent"
    ));
  });
  beforeEach(() => {
    createAiToolMock.mockClear();
    clampMaxTokensMock.mockClear();
    hoisted.executeSpy.mockClear();
    streamTextMock.mockClear();
  });

  it("writes one call per record with correct payloads", async () => {
    const req: MemoryUpdateRequest = {
      records: [
        { category: "user_preference", content: "I prefer window seats" },
        { content: "Allergies: peanuts" }, // category defaults to other
      ],
    };

    const out = await persistMemoryRecords("user-123", req);

    const createAiToolCall = createAiToolMock.mock.calls[0]?.[0] as
      | {
          guardrails?: Record<string, unknown>;
          outputSchema?: unknown;
          validateOutput?: boolean;
        }
      | undefined;
    expect(createAiToolCall?.guardrails).toBeDefined();
    expect(createAiToolCall?.guardrails).not.toHaveProperty("cache");
    expect(createAiToolCall?.outputSchema).toBeDefined();
    expect(createAiToolCall?.validateOutput).toBe(true);

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

  it("budgets trusted instructions but sends only the user summary message", async () => {
    const config: AgentConfig = {
      agentType: "memoryAgent",
      createdAt: "2026-07-15T00:00:00.000Z",
      id: "v1_deadbeef",
      model: "gpt-5.5",
      parameters: {},
      scope: "global",
      updatedAt: "2026-07-15T00:00:00.000Z",
    };
    const input: MemoryUpdateRequest = {
      records: [{ content: "I prefer window seats" }],
    };

    await runMemoryAgent(
      {
        identifier: "user-123",
        model: createMockModel(),
        modelId: "gpt-5.5",
      },
      config,
      input
    );

    const instructions =
      "You are a concise memory assistant. A batch of user memories was written. Summarize results briefly without echoing private content.";
    expect(clampMaxTokensMock).toHaveBeenCalledWith(
      [
        { content: instructions, role: "system" },
        { content: expect.stringContaining("Results:"), role: "user" },
      ],
      512,
      "gpt-5.5"
    );
    expect(streamTextMock).toHaveBeenCalledWith(
      expect.objectContaining({
        instructions,
        messages: [{ content: expect.stringContaining("Results:"), role: "user" }],
      })
    );
  });
});
