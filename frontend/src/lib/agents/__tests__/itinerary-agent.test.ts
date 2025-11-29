/** @vitest-environment node */

import { toolRegistry } from "@ai/tools";
import type { ItineraryPlanRequest } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { runItineraryAgent } from "@/lib/agents/itinerary-agent";
import { deepCloneValue } from "@/test-utils/deep-clone";
import { createMockModel } from "@/test/ai-sdk/mock-model";

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
  agentType: "itineraryAgent",
  createdAt: "2025-01-01T00:00:00.000Z",
  id: "v1_abcdef01",
  model: "gpt-4o",
  parameters: {
    description: null,
    maxTokens: 4096,
    model: "gpt-4o",
    temperature: 0.2,
    timeoutSeconds: 30,
    topKTools: 4,
    topP: 0.9,
  },
  scope: "agentSpecific",
  updatedAt: "2025-01-01T00:00:00.000Z",
};

const baseInput: ItineraryPlanRequest = {
  budgetPerDay: 300,
  destination: "Lisbon",
  durationDays: 3,
  interests: ["food"],
  partySize: 2,
  travelDates: "2025-04-20",
};

const cloneToolRegistry = (registry: typeof toolRegistry) =>
  Object.fromEntries(
    Object.entries(registry).map(([key, tool]) => [key, deepCloneValue(tool)])
  ) as typeof toolRegistry;

const originalRegistry = cloneToolRegistry(toolRegistry);

describe("runItineraryAgent", () => {
  beforeEach(() => {
    Object.keys(toolRegistry).forEach((key) => {
      delete (toolRegistry as Record<string, unknown>)[key];
    });
    Object.assign(toolRegistry, cloneToolRegistry(originalRegistry));
    streamTextMock.mockReset();
    streamTextMock.mockImplementation(streamTextImpl);
    createAiToolMock.mockClear();
  });

  it("throws when required tool is missing", () => {
    (toolRegistry as Record<string, unknown>).createTravelPlan = undefined as never;

    expect(() =>
      runItineraryAgent(
        { identifier: "user-1", model: createMockModel(), modelId: "mock" },
        baseConfig,
        baseInput
      )
    ).toThrow(/Tool createTravelPlan not registered/);
  });

  it("wraps registry tools and delegates execution", async () => {
    const createExecute = vi.fn().mockResolvedValue({ ok: true });
    const saveExecute = vi.fn().mockResolvedValue({ saved: true });
    const searchExecute = vi.fn().mockResolvedValue({ results: [] });
    const batchExecute = vi.fn().mockResolvedValue({ results: [] });
    const poiExecute = vi.fn().mockResolvedValue({ pois: [] });

    Object.assign(toolRegistry, {
      createTravelPlan: { description: "create", execute: createExecute },
      lookupPoiContext: { description: "poi", execute: poiExecute },
      saveTravelPlan: { description: "save", execute: saveExecute },
      webSearch: { description: "search", execute: searchExecute },
      webSearchBatch: { description: "batch", execute: batchExecute },
    });

    runItineraryAgent(
      { identifier: "user-1", model: createMockModel(), modelId: "mock" },
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

    const createInput = { plan: true };
    const saveInput = { save: true };
    const searchInput = { query: "q" };
    const batchInput = { queries: ["q1"] };
    const poiInput = { destination: "Lisbon" };

    await tools.createTravelPlan.execute(createInput, { toolCallId: "tc1" });
    await tools.saveTravelPlan.execute(saveInput, { toolCallId: "tc2" });
    await tools.webSearch.execute(searchInput, { toolCallId: "tc3" });
    await tools.webSearchBatch.execute(batchInput, { toolCallId: "tc4" });
    await tools.lookupPoiContext.execute(poiInput, { toolCallId: "tc5" });

    expect(createExecute).toHaveBeenCalledWith(
      createInput,
      expect.objectContaining({ toolCallId: "tc1" })
    );
    expect(saveExecute).toHaveBeenCalledWith(
      saveInput,
      expect.objectContaining({ toolCallId: "tc2" })
    );
    expect(searchExecute).toHaveBeenCalledWith(
      searchInput,
      expect.objectContaining({ toolCallId: "tc3" })
    );
    expect(batchExecute).toHaveBeenCalledWith(
      batchInput,
      expect.objectContaining({ toolCallId: "tc4" })
    );
    expect(poiExecute).toHaveBeenCalledWith(
      poiInput,
      expect.objectContaining({ toolCallId: "tc5" })
    );
    expect(createAiToolMock).toHaveBeenCalledTimes(5);
    expect(streamTextMock).toHaveBeenCalledTimes(1);
  });
});
