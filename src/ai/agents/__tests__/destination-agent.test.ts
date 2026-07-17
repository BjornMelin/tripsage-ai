/** @vitest-environment node */

import type { DestinationResearchRequest } from "@schemas/agents";
import type { AgentConfig } from "@schemas/configuration";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockCreateTripSageAgent = vi.hoisted(() => vi.fn());
const mockClampMaxTokens = vi.hoisted(() => vi.fn());
const mockBuildDestinationPrompt = vi.hoisted(() => vi.fn());

vi.mock("server-only", () => ({}));

vi.mock("../agent-factory", () => ({
  createTripSageAgent: mockCreateTripSageAgent,
}));

vi.mock("@/lib/tokens/budget", () => ({
  clampMaxTokens: mockClampMaxTokens,
}));

vi.mock("@/prompts/agents", () => ({
  buildDestinationPrompt: mockBuildDestinationPrompt,
}));

vi.mock("@ai/tools", () => ({
  crawlSite: { description: "crawl" },
  getCurrentWeather: { description: "weather" },
  getTravelAdvisory: { description: "advisory" },
  placeDetails: { description: "place details" },
  searchPlaces: { description: "places" },
  webSearch: { description: "search" },
  webSearchBatch: { description: "batch search" },
}));

import { createDestinationAgent } from "../destination-agent";
import type { AgentDependencies } from "../types";

const mockDeps: AgentDependencies = {
  model: { modelId: "gpt-5.4-mini" } as AgentDependencies["model"],
  modelId: "gpt-5.4-mini",
  userId: "user-456",
};

const baseConfig: AgentConfig = {
  agentType: "destinationResearchAgent",
  createdAt: "2026-07-16T00:00:00.000Z",
  id: "v1784160000_deadbeef",
  model: "gpt-5.4-mini",
  parameters: {
    maxOutputTokens: 2048,
    stepLimit: 10,
    temperature: 0.7,
    topP: 0.9,
  },
  scope: "global",
  updatedAt: "2026-07-16T00:00:00.000Z",
};

const mockInput: DestinationResearchRequest = {
  destination: "Kyoto, Japan",
  specificInterests: ["temples", "food"],
  travelDates: "2027-04-01 to 2027-04-07",
};

function createdAgentConfig(): Record<string, unknown> {
  const call = mockCreateTripSageAgent.mock.calls.at(-1);
  expect(call).toBeDefined();
  return call?.[1] as Record<string, unknown>;
}

describe("createDestinationAgent", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBuildDestinationPrompt.mockReturnValue("Trusted destination instructions");
    mockClampMaxTokens.mockReturnValue({ maxOutputTokens: 1024, reasons: [] });
    mockCreateTripSageAgent.mockReturnValue({ agent: {}, uiMessages: [] });
  });

  it("creates a bounded agent while keeping request data out of instructions", () => {
    createDestinationAgent(mockDeps, baseConfig, mockInput);

    expect(mockBuildDestinationPrompt).toHaveBeenCalledWith();
    expect(mockCreateTripSageAgent).toHaveBeenCalledWith(
      mockDeps,
      expect.objectContaining({
        agentType: "destinationResearch",
        instructions: "Trusted destination instructions",
        maxOutputTokens: 1024,
        name: "Destination Research Agent",
        stepLimit: 15,
        temperature: 0.7,
        tools: expect.objectContaining({
          crawlSite: expect.anything(),
          getCurrentWeather: expect.anything(),
          getTravelAdvisory: expect.anything(),
          searchPlaceDetails: expect.anything(),
          searchPlaces: expect.anything(),
          webSearch: expect.anything(),
          webSearchBatch: expect.anything(),
        }),
        topP: 0.9,
      })
    );

    const config = createdAgentConfig();
    expect(config.instructions).not.toContain(mockInput.destination);
    expect(config.uiMessages).toEqual([
      expect.objectContaining({
        parts: [
          expect.objectContaining({
            text: expect.stringContaining('schemaVersion="dest.v1"'),
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

  it("selects the search, crawl, and safety tools at each phase boundary", () => {
    createDestinationAgent(mockDeps, baseConfig, mockInput);

    const prepareStep = createdAgentConfig().prepareStep as (input: {
      stepNumber: number;
    }) => { activeTools: string[] };

    expect(prepareStep({ stepNumber: 4 }).activeTools).toEqual([
      "webSearch",
      "webSearchBatch",
      "searchPlaces",
    ]);
    expect(prepareStep({ stepNumber: 5 }).activeTools).toEqual([
      "crawlSite",
      "webSearchBatch",
      "searchPlaces",
      "searchPlaceDetails",
    ]);
    expect(prepareStep({ stepNumber: 10 }).activeTools).toEqual([
      "getCurrentWeather",
      "getTravelAdvisory",
      "searchPlaceDetails",
    ]);
  });

  it("honors a configured step limit when it exceeds the workflow minimum", () => {
    createDestinationAgent(
      mockDeps,
      {
        ...baseConfig,
        parameters: { ...baseConfig.parameters, stepLimit: 50 },
      },
      mockInput
    );

    const config = createdAgentConfig();
    const prepareStep = config.prepareStep as (input: { stepNumber: number }) => {
      activeTools: string[];
    };
    expect(config.stepLimit).toBe(50);
    expect(prepareStep({ stepNumber: 16 }).activeTools).toContain("webSearch");
    expect(prepareStep({ stepNumber: 17 }).activeTools).toContain("crawlSite");
    expect(prepareStep({ stepNumber: 32 }).activeTools).toContain("crawlSite");
    expect(prepareStep({ stepNumber: 33 }).activeTools).toContain("getTravelAdvisory");
  });
});
