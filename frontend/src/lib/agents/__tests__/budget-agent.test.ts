/** @vitest-environment node */

import { toolRegistry } from "@ai/tools";
import type { BudgetPlanRequest } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { runBudgetAgent } from "@/lib/agents/budget-agent";
import { createMockModel } from "@/test/ai-sdk/mock-model";
import { deepCloneValue } from "@/test-utils/deep-clone";

const streamTextImpl = (options: unknown) =>
  ({
    ...(options as Record<string, unknown>),
    textStream: (function* () {
      yield { textDelta: "ok", type: "text-delta" } as const;
    })(),
    toUIMessageStreamResponse: vi.fn(),
  }) as unknown;

const streamTextMock = vi.hoisted(() =>
  vi.fn<(options: unknown) => unknown>((options: unknown) => streamTextImpl(options))
);
const createAiToolMock = vi.hoisted(() =>
  vi.fn().mockImplementation(({ execute, name }) => ({
    description: name,
    execute,
    inputSchema: {},
    name,
  }))
);

vi.mock("ai", async () => {
  const actual = await vi.importActual<typeof import("ai")>("ai");
  return {
    ...actual,
    streamText: streamTextMock,
  };
});

vi.mock("@ai/lib/tool-factory", () => ({
  createAiTool: createAiToolMock,
}));

const baseConfig: AgentConfig = {
  agentType: "budgetAgent",
  createdAt: "2025-01-01T00:00:00.000Z",
  id: "v1_abcdef02",
  model: "gpt-4o",
  parameters: {
    description: null,
    maxTokens: 2048,
    model: "gpt-4o",
    temperature: 0.25,
    timeoutSeconds: 30,
    topKTools: 4,
    topP: 0.85,
  },
  scope: "agentSpecific",
  updatedAt: "2025-01-01T00:00:00.000Z",
};

const baseInput: BudgetPlanRequest = {
  budgetCap: 2500,
  destination: "Lisbon",
  durationDays: 5,
  preferredCurrency: "USD",
};

const cloneToolRegistry = (registry: typeof toolRegistry) =>
  deepCloneValue(registry) as typeof toolRegistry;

const originalRegistry = cloneToolRegistry(toolRegistry);

describe("runBudgetAgent", () => {
  beforeEach(() => {
    Object.keys(toolRegistry).forEach((key) => {
      delete (toolRegistry as Record<string, unknown>)[key];
    });
    Object.assign(toolRegistry, cloneToolRegistry(originalRegistry));
    streamTextMock.mockReset();
    streamTextMock.mockImplementation(streamTextImpl);
    createAiToolMock.mockClear();
  });

  it("throws when combineSearchResults tool is missing", () => {
    (toolRegistry as Record<string, unknown>).combineSearchResults = undefined as never;

    expect(() =>
      runBudgetAgent(
        { identifier: "user-2", model: createMockModel(), modelId: "mock" },
        baseConfig,
        baseInput
      )
    ).toThrow(/Tool combineSearchResults not registered/);
  });

  it("wraps budget tools and delegates execution", async () => {
    const combineExecute = vi.fn().mockResolvedValue({ combined: true });
    const advisoryExecute = vi.fn().mockResolvedValue({ score: 80 });
    const poiExecute = vi.fn().mockResolvedValue({ pois: [] });
    const batchExecute = vi.fn().mockResolvedValue({ results: [] });

    Object.assign(toolRegistry, {
      combineSearchResults: { description: "combine", execute: combineExecute },
      getTravelAdvisory: { description: "advisory", execute: advisoryExecute },
      lookupPoiContext: { description: "poi", execute: poiExecute },
      webSearchBatch: { description: "batch", execute: batchExecute },
    });

    runBudgetAgent(
      { identifier: "user-2", model: createMockModel(), modelId: "mock" },
      baseConfig,
      baseInput
    );

    const call = streamTextMock.mock.calls[0]?.[0] as {
      tools: Record<
        string,
        { execute: (params: unknown, callOpts?: unknown) => unknown }
      >;
    };
    expect(call).toBeDefined();
    const tools = call.tools;

    const combineInput = { combined: true };
    const advisoryInput = { destination: "Lisbon" };
    const poiInput = { destination: "Lisbon" };
    const batchInput = { queries: ["q1"] };

    await tools.combineSearchResults.execute(combineInput, { toolCallId: "tc1" });
    await tools.getTravelAdvisory.execute(advisoryInput, { toolCallId: "tc2" });
    await tools.lookupPoiContext.execute(poiInput, { toolCallId: "tc3" });
    await tools.webSearchBatch.execute(batchInput, { toolCallId: "tc4" });

    expect(combineExecute).toHaveBeenCalledWith(
      combineInput,
      expect.objectContaining({ toolCallId: "tc1" })
    );
    expect(advisoryExecute).toHaveBeenCalledWith(
      advisoryInput,
      expect.objectContaining({ toolCallId: "tc2" })
    );
    expect(poiExecute).toHaveBeenCalledWith(
      poiInput,
      expect.objectContaining({ toolCallId: "tc3" })
    );
    expect(batchExecute).toHaveBeenCalledWith(
      batchInput,
      expect.objectContaining({ toolCallId: "tc4" })
    );
    expect(createAiToolMock).toHaveBeenCalledTimes(4);
    expect(streamTextMock).toHaveBeenCalledTimes(1);
  });
});
