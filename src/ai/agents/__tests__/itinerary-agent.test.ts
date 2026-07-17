/** @vitest-environment node */

import type { ItineraryPlanRequest } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockCreateTripSageAgent = vi.hoisted(() => vi.fn());
const mockClampMaxTokens = vi.hoisted(() => vi.fn());
const mockBuildItineraryPrompt = vi.hoisted(() => vi.fn());
const mockWrapToolsWithUserId = vi.hoisted(() => vi.fn());

vi.mock("server-only", () => ({}));

vi.mock("../agent-factory", () => ({
  createTripSageAgent: mockCreateTripSageAgent,
}));

vi.mock("@/lib/tokens/budget", () => ({
  clampMaxTokens: mockClampMaxTokens,
}));

vi.mock("@/prompts/agents", () => ({
  buildItineraryPrompt: mockBuildItineraryPrompt,
}));

vi.mock("@ai/tools/server/injection", () => ({
  wrapToolsWithUserId: mockWrapToolsWithUserId,
}));

vi.mock("@ai/tools", () => ({
  createTravelPlan: { description: "create plan" },
  placeDetails: { description: "place details" },
  saveTravelPlan: { description: "save plan" },
  searchPlaces: { description: "places" },
  webSearch: { description: "search" },
  webSearchBatch: { description: "batch search" },
}));

import { createItineraryAgent } from "../itinerary-agent";
import type { AgentDependencies } from "../types";

const mockDeps: AgentDependencies = {
  model: { modelId: "gpt-5.4-mini" } as AgentDependencies["model"],
  modelId: "gpt-5.4-mini",
  userId: "user-456",
};

const baseConfig: AgentConfig = {
  agentType: "itineraryAgent",
  createdAt: "2026-07-16T00:00:00.000Z",
  id: "v1784160000_deadbeef",
  model: "gpt-5.4-mini",
  parameters: {
    maxOutputTokens: 3072,
    stepLimit: 10,
    temperature: 0.6,
    topP: 0.85,
  },
  scope: "global",
  updatedAt: "2026-07-16T00:00:00.000Z",
};

const mockInput: ItineraryPlanRequest = {
  destination: "Rome, Italy",
  durationDays: 5,
  interests: ["history", "food"],
  partySize: 2,
};

function createdAgentConfig(): Record<string, unknown> {
  const call = mockCreateTripSageAgent.mock.calls.at(-1);
  expect(call).toBeDefined();
  return call?.[1] as Record<string, unknown>;
}

describe("createItineraryAgent", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBuildItineraryPrompt.mockReturnValue("Trusted itinerary instructions");
    mockClampMaxTokens.mockReturnValue({ maxOutputTokens: 1536, reasons: [] });
    mockWrapToolsWithUserId.mockImplementation((tools: Record<string, unknown>) => ({
      ...tools,
      createTravelPlan: { description: "wrapped create plan" },
      saveTravelPlan: { description: "wrapped save plan" },
    }));
    mockCreateTripSageAgent.mockReturnValue({ agent: {}, uiMessages: [] });
  });

  it("requires a user before preparing user-scoped tools", () => {
    expect(() =>
      createItineraryAgent({ ...mockDeps, userId: undefined }, baseConfig, mockInput)
    ).toThrow("Itinerary agent requires a valid userId");
    expect(mockWrapToolsWithUserId).not.toHaveBeenCalled();
    expect(mockCreateTripSageAgent).not.toHaveBeenCalled();
  });

  it("injects user ownership and keeps request data out of instructions", () => {
    createItineraryAgent(mockDeps, baseConfig, mockInput);

    expect(mockBuildItineraryPrompt).toHaveBeenCalledWith();
    expect(mockWrapToolsWithUserId).toHaveBeenCalledWith(
      expect.objectContaining({
        createTravelPlan: expect.anything(),
        saveTravelPlan: expect.anything(),
      }),
      "user-456",
      ["createTravelPlan", "saveTravelPlan"]
    );
    expect(mockCreateTripSageAgent).toHaveBeenCalledWith(
      mockDeps,
      expect.objectContaining({
        agentType: "itineraryPlanning",
        instructions: "Trusted itinerary instructions",
        maxOutputTokens: 1536,
        name: "Itinerary Planning Agent",
        stepLimit: 15,
        temperature: 0.6,
        tools: expect.objectContaining({
          createTravelPlan: { description: "wrapped create plan" },
          saveTravelPlan: { description: "wrapped save plan" },
        }),
        topP: 0.85,
      })
    );

    const config = createdAgentConfig();
    expect(config.instructions).not.toContain(mockInput.destination);
    expect(config.uiMessages).toEqual([
      expect.objectContaining({
        parts: [
          expect.objectContaining({
            text: expect.stringContaining('schemaVersion="itin.v1"'),
          }),
        ],
        role: "user",
      }),
    ]);
    const uiMessages = config.uiMessages as Array<{
      parts: Array<{ text: string }>;
    }>;
    expect(uiMessages[0]?.parts[0]?.text).toContain(JSON.stringify(mockInput));
  });

  it("selects research, planning, and persistence tools at each phase boundary", () => {
    createItineraryAgent(mockDeps, baseConfig, mockInput);

    const prepareStep = createdAgentConfig().prepareStep as (input: {
      stepNumber: number;
    }) => { activeTools: string[] };

    expect(prepareStep({ stepNumber: 5 }).activeTools).toEqual([
      "webSearch",
      "webSearchBatch",
      "searchPlaces",
      "searchPlaceDetails",
    ]);
    expect(prepareStep({ stepNumber: 6 }).activeTools).toEqual([
      "createTravelPlan",
      "searchPlaces",
    ]);
    expect(prepareStep({ stepNumber: 10 }).activeTools).toEqual([
      "createTravelPlan",
      "searchPlaces",
    ]);
    expect(prepareStep({ stepNumber: 11 }).activeTools).toEqual([
      "saveTravelPlan",
      "createTravelPlan",
    ]);
  });

  it("honors a configured step limit when it exceeds the workflow minimum", () => {
    createItineraryAgent(
      mockDeps,
      {
        ...baseConfig,
        parameters: { ...baseConfig.parameters, stepLimit: 20 },
      },
      mockInput
    );

    const config = createdAgentConfig();
    const prepareStep = config.prepareStep as (input: { stepNumber: number }) => {
      activeTools: string[];
    };
    expect(config.stepLimit).toBe(20);
    expect(prepareStep({ stepNumber: 7 }).activeTools).toContain("webSearch");
    expect(prepareStep({ stepNumber: 8 }).activeTools).toContain("createTravelPlan");
    expect(prepareStep({ stepNumber: 14 }).activeTools).toContain("createTravelPlan");
    expect(prepareStep({ stepNumber: 15 }).activeTools).toContain("saveTravelPlan");
  });
});
