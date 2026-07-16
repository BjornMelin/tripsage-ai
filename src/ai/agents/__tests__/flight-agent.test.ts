/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

// Hoisted mocks per testing.md Pattern A
const mockCreateTripSageAgent = vi.hoisted(() => vi.fn());
const mockClampMaxTokens = vi.hoisted(() => vi.fn());
const mockBuildFlightPrompt = vi.hoisted(() => vi.fn());

vi.mock("server-only", () => ({}));

vi.mock("../agent-factory", () => ({
  createTripSageAgent: mockCreateTripSageAgent,
}));

vi.mock("@/lib/tokens/budget", () => ({
  clampMaxTokens: mockClampMaxTokens,
}));

vi.mock("@/prompts/agents", () => ({
  buildFlightPrompt: mockBuildFlightPrompt,
}));

vi.mock("@ai/tools", () => ({
  distanceMatrix: { description: "distance", execute: vi.fn() },
  geocode: { description: "geocode", execute: vi.fn() },
  placeDetails: { description: "place details", execute: vi.fn() },
  searchFlights: { description: "flights", execute: vi.fn() },
  searchPlaces: { description: "places", execute: vi.fn() },
}));

import type { AgentConfig } from "@schemas/configuration";
import type { FlightSearchRequest } from "@schemas/flights";
import { createFlightAgent } from "../flight-agent";
import type { AgentDependencies, TripSageAgentResult } from "../types";

describe("createFlightAgent", () => {
  const mockDeps: AgentDependencies = {
    model: { modelId: "gpt-5.4-mini" } as AgentDependencies["model"],
    modelId: "gpt-5.4-mini",
    userId: "user-456",
  };

  // Use type assertion since we only need fields the agent extracts
  const mockConfig = {
    agentType: "flightAgent",
    createdAt: "2025-01-01T00:00:00Z",
    id: "config-1",
    model: "gpt-5.4-mini",
    parameters: {
      maxOutputTokens: 2048,
      stepLimit: 10,
      temperature: 0.7,
      topP: 0.9,
    },
    scope: "global",
    updatedAt: "2025-01-01T00:00:00Z",
  } as AgentConfig;

  const mockInput: FlightSearchRequest = {
    cabinClass: "economy",
    currency: "USD",
    departureDate: "2025-06-01",
    destination: "Tokyo",
    origin: "New York",
    passengers: 2,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockClampMaxTokens.mockReturnValue({ maxOutputTokens: 1024, reasons: [] });
    mockBuildFlightPrompt.mockReturnValue(
      "Search for flights from {origin} to {destination}"
    );
    mockCreateTripSageAgent.mockReturnValue({
      agent: unsafeCast<TripSageAgentResult["agent"]>({
        generate: vi.fn(),
        stream: vi.fn(),
      }),
      uiMessages: [],
    } satisfies TripSageAgentResult);
  });

  it("creates flight agent with correct configuration", () => {
    const result = createFlightAgent(mockDeps, mockConfig, mockInput);

    expect(mockCreateTripSageAgent).toHaveBeenCalledWith(
      mockDeps,
      expect.objectContaining({
        agentType: "flightSearch",
        instructions: expect.any(String),
        maxOutputTokens: 1024,
        name: "Flight Search Agent",
      })
    );
    expect(result).toBeDefined();
    expect(result.agent).toBeDefined();
  });

  it("keeps request input out of trusted instructions", () => {
    createFlightAgent(mockDeps, mockConfig, mockInput);

    expect(mockBuildFlightPrompt).toHaveBeenCalledWith();
    const config = mockCreateTripSageAgent.mock.calls[0][1];
    expect(config.instructions).not.toContain(mockInput.destination);
  });

  it("includes flight tools in agent configuration", () => {
    createFlightAgent(mockDeps, mockConfig, mockInput);

    expect(mockCreateTripSageAgent).toHaveBeenCalledWith(
      mockDeps,
      expect.objectContaining({
        tools: expect.objectContaining({
          distanceMatrix: expect.anything(),
          geocode: expect.anything(),
          searchFlights: expect.anything(),
          searchPlaceDetails: expect.anything(),
          searchPlaces: expect.anything(),
        }),
      })
    );
  });

  it("configures phased tool selection via prepareStep", () => {
    createFlightAgent(mockDeps, mockConfig, mockInput);

    const call = mockCreateTripSageAgent.mock.calls[0];
    const config = call[1];
    expect(config.prepareStep).toBeDefined();

    // Phase 1: steps 0-2 should have geocode and POI tools
    const phase1 = config.prepareStep({ stepNumber: 0 });
    expect(phase1.activeTools).toContain("geocode");
    expect(phase1.activeTools).toContain("searchPlaces");
    expect(phase1.activeTools).toContain("searchPlaceDetails");

    // Phase 2: steps 3+ should have search and distance tools
    const phase2 = config.prepareStep({ stepNumber: 3 });
    expect(phase2.activeTools).toContain("searchFlights");
    expect(phase2.activeTools).toContain("distanceMatrix");
  });

  it("builds canonical UI messages and clamps output tokens", () => {
    createFlightAgent(mockDeps, mockConfig, mockInput);

    const call = mockCreateTripSageAgent.mock.calls[0];
    const config = call[1];
    expect(mockClampMaxTokens).toHaveBeenCalledWith(
      [
        {
          content: "Search for flights from {origin} to {destination}",
          role: "system",
        },
        {
          content: expect.stringContaining('schemaVersion="flight.v2"'),
          role: "user",
        },
      ],
      2048,
      "gpt-5.4-mini"
    );
    expect(config.maxOutputTokens).toBe(1024);
    expect(config.uiMessages).toBeDefined();
    expect(config.uiMessages[0].parts[0].text).toContain("schemaVersion");
    expect(config.uiMessages[0].parts[0].text).toContain(JSON.stringify(mockInput));
  });
});
