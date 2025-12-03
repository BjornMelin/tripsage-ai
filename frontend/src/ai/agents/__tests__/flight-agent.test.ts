/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

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
  lookupPoiContext: { description: "poi", execute: vi.fn() },
  searchFlights: { description: "flights", execute: vi.fn() },
}));

import type { AgentConfig } from "@schemas/configuration";
import type { FlightSearchRequest } from "@schemas/flights";
import { createFlightAgent } from "../flight-agent";
import type { AgentDependencies } from "../types";

describe("createFlightAgent", () => {
  const mockDeps: AgentDependencies = {
    identifier: "test-agent",
    model: { modelId: "gpt-4" } as AgentDependencies["model"],
    modelId: "gpt-4",
    sessionId: "session-123",
    userId: "user-456",
  };

  // Use type assertion since we only need fields the agent extracts
  const mockConfig = {
    agentType: "flightAgent",
    createdAt: "2025-01-01T00:00:00Z",
    id: "config-1",
    model: "gpt-4",
    parameters: {
      maxSteps: 10,
      maxTokens: 2048,
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
    mockClampMaxTokens.mockReturnValue({ maxTokens: 1024, reasons: [] });
    mockBuildFlightPrompt.mockReturnValue("Search for flights from {origin} to {destination}");
    mockCreateTripSageAgent.mockReturnValue({
      agent: { generate: vi.fn(), stream: vi.fn() },
      metadata: { agentType: "flightSearch" },
    });
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

  it("builds prompt with flight search input", () => {
    createFlightAgent(mockDeps, mockConfig, mockInput);

    expect(mockBuildFlightPrompt).toHaveBeenCalledWith(mockInput);
  });

  it("clamps max tokens based on context messages", () => {
    const contextMessages = [
      { content: "Previous message", role: "user" as const },
    ];

    createFlightAgent(mockDeps, mockConfig, mockInput, contextMessages);

    expect(mockClampMaxTokens).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({ role: "system" }),
        expect.objectContaining({ role: "user" }),
      ]),
      2048,
      "gpt-4"
    );
  });

  it("includes flight tools in agent configuration", () => {
    createFlightAgent(mockDeps, mockConfig, mockInput);

    expect(mockCreateTripSageAgent).toHaveBeenCalledWith(
      mockDeps,
      expect.objectContaining({
        tools: expect.objectContaining({
          distanceMatrix: expect.anything(),
          geocode: expect.anything(),
          lookupPoiContext: expect.anything(),
          searchFlights: expect.anything(),
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
    expect(phase1.activeTools).toContain("lookupPoiContext");

    // Phase 2: steps 3+ should have search and distance tools
    const phase2 = config.prepareStep({ stepNumber: 3 });
    expect(phase2.activeTools).toContain("searchFlights");
    expect(phase2.activeTools).toContain("distanceMatrix");
  });

  it("includes JSON schema instruction in default messages", () => {
    createFlightAgent(mockDeps, mockConfig, mockInput);

    const call = mockCreateTripSageAgent.mock.calls[0];
    const config = call[1];
    expect(config.defaultMessages).toBeDefined();
    expect(config.defaultMessages[0].content).toContain("schemaVersion");
  });
});
