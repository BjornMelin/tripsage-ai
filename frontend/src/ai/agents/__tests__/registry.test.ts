/**
 * @vitest-environment node
 */

import { describe, expect, it, vi } from "vitest";

// Mock server-only module before imports
vi.mock("server-only", () => ({}));

// Mock dependencies
vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: () => ({
    error: vi.fn(),
    info: vi.fn(),
  }),
}));

vi.mock("@/lib/security/random", () => ({
  secureUuid: () => "test-uuid-123",
}));

vi.mock("@/lib/ratelimit/config", () => ({
  buildRateLimit: () => ({
    identifier: "test",
    limit: 100,
    window: "1m",
  }),
}));

vi.mock("@/lib/tokens/budget", () => ({
  clampMaxTokens: () => ({ maxTokens: 1024, reasons: [] }),
  countTokens: () => 100,
}));

vi.mock("@/lib/tokens/limits", () => ({
  getModelContextLimit: () => 128000,
}));

vi.mock("@ai/lib/registry-utils", () => ({
  getRegistryTool: () => ({
    description: "Mock tool",
    execute: vi.fn(),
  }),
  invokeTool: vi.fn(),
  requireTool: () => ({
    description: "Mock tool",
    execute: vi.fn(),
  }),
}));

vi.mock("@ai/lib/tool-factory", () => ({
  createAiTool: () => ({
    description: "Mock AI tool",
    execute: vi.fn(),
  }),
}));

vi.mock("@ai/tools", () => {
  const createMockTool = (description: string) => ({ description, execute: vi.fn() });
  const tools = {
    bookAccommodation: createMockTool("book accommodation"),
    checkAvailability: createMockTool("check availability"),
    combineSearchResults: createMockTool("combine results"),
    crawlSite: createMockTool("crawl"),
    createTravelPlan: createMockTool("create plan"),
    distanceMatrix: createMockTool("distance"),
    geocode: createMockTool("geocode"),
    getAccommodationDetails: createMockTool("accommodation details"),
    getCurrentWeather: createMockTool("weather"),
    getTravelAdvisory: createMockTool("advisory"),
    lookupPoiContext: createMockTool("poi"),
    saveTravelPlan: createMockTool("save plan"),
    searchAccommodations: createMockTool("accommodations"),
    searchFlights: createMockTool("flights"),
    webSearch: createMockTool("web search"),
    webSearchBatch: createMockTool("batch search"),
  };

  return {
    ...tools,
    toolRegistry: tools,
  };
});

vi.mock("@/prompts/agents", () => ({
  buildAccommodationPrompt: () => "Accommodation prompt",
  buildBudgetPrompt: () => "Budget prompt",
  buildDestinationPrompt: () => "Destination prompt",
  buildFlightPrompt: () => "Flight prompt",
  buildItineraryPrompt: () => "Itinerary prompt",
}));

import type { LanguageModel } from "ai";
import {
  agentRegistry,
  createAgentForWorkflow,
  getAgentName,
  getMinimumMaxSteps,
  isSupportedAgentKind,
} from "../index";
import type { AgentDependencies } from "../types";

/**
 * Creates a mock LanguageModel for testing.
 */
function createMockModel(): LanguageModel {
  // Minimal fields used by tests; extend if LanguageModel interface adds requirements
  return {
    defaultObjectGenerationMode: "json",
    doGenerate: vi.fn(),
    doStream: vi.fn(),
    modelId: "test-model",
    provider: "test-provider",
    specificationVersion: "V3",
    supportsStructuredOutputs: true,
  } as unknown as LanguageModel;
}

/**
 * Creates test dependencies.
 */
function createTestDeps(): AgentDependencies {
  return {
    identifier: "test-user-123",
    model: createMockModel(),
    modelId: "gpt-4",
    sessionId: "test-session-456",
    userId: "test-user-123",
  };
}

describe("agentRegistry", () => {
  it("should contain all expected agent factories", () => {
    expect(agentRegistry.budgetPlanning).toBeDefined();
    expect(agentRegistry.flightSearch).toBeDefined();
    expect(agentRegistry.accommodationSearch).toBeDefined();
    expect(agentRegistry.destinationResearch).toBeDefined();
    expect(agentRegistry.itineraryPlanning).toBeDefined();
  });

  it("should have the correct number of agents", () => {
    expect(Object.keys(agentRegistry)).toHaveLength(5);
  });
});

describe("isSupportedAgentKind", () => {
  it("should return true for supported agent kinds", () => {
    expect(isSupportedAgentKind("budgetPlanning")).toBe(true);
    expect(isSupportedAgentKind("flightSearch")).toBe(true);
    expect(isSupportedAgentKind("accommodationSearch")).toBe(true);
    expect(isSupportedAgentKind("destinationResearch")).toBe(true);
    expect(isSupportedAgentKind("itineraryPlanning")).toBe(true);
  });

  it("should return false for unsupported agent kinds", () => {
    expect(isSupportedAgentKind("memoryUpdate")).toBe(false);
    expect(isSupportedAgentKind("router")).toBe(false);
  });
});

describe("getAgentName", () => {
  it("should return correct names for all agent kinds", () => {
    expect(getAgentName("budgetPlanning")).toBe("Budget Planning Agent");
    expect(getAgentName("flightSearch")).toBe("Flight Search Agent");
    expect(getAgentName("accommodationSearch")).toBe("Accommodation Search Agent");
    expect(getAgentName("destinationResearch")).toBe("Destination Research Agent");
    expect(getAgentName("itineraryPlanning")).toBe("Itinerary Planning Agent");
    expect(getAgentName("memoryUpdate")).toBe("Memory Update Agent");
    expect(getAgentName("router")).toBe("Router Agent");
  });
});

describe("getMinimumMaxSteps", () => {
  it("should return correct minimum steps for each agent kind", () => {
    expect(getMinimumMaxSteps("budgetPlanning")).toBe(10);
    expect(getMinimumMaxSteps("flightSearch")).toBe(10);
    expect(getMinimumMaxSteps("accommodationSearch")).toBe(10);
    expect(getMinimumMaxSteps("destinationResearch")).toBe(15);
    expect(getMinimumMaxSteps("itineraryPlanning")).toBe(15);
    expect(getMinimumMaxSteps("memoryUpdate")).toBe(5);
    expect(getMinimumMaxSteps("router")).toBe(1);
  });
});

describe("createAgentForWorkflow", () => {
  /**
   * Creates a full AgentConfig for testing.
   */
  function createTestConfig(
    agentType:
      | "budgetAgent"
      | "flightAgent"
      | "accommodationAgent"
      | "destinationResearchAgent"
      | "itineraryAgent"
  ) {
    return {
      agentType,
      createdAt: "2025-01-01T00:00:00.000Z",
      id: "test-config-id",
      model: "gpt-4" as const,
      parameters: {
        maxSteps: 10,
        maxTokens: 4096,
        temperature: 0.3,
      },
      scope: "global" as const,
      updatedAt: "2025-01-01T00:00:00.000Z",
    };
  }

  it("should create a budget planning agent", () => {
    const deps = createTestDeps();
    const result = createAgentForWorkflow(
      "budgetPlanning",
      deps,
      createTestConfig("budgetAgent"),
      {
        destination: "Tokyo",
        durationDays: 7,
      }
    );

    expect(result).toBeDefined();
    expect(result.agent).toBeDefined();
    expect(result.agentType).toBe("budgetPlanning");
  });

  it("should create a flight search agent", () => {
    const deps = createTestDeps();
    const result = createAgentForWorkflow(
      "flightSearch",
      deps,
      createTestConfig("flightAgent"),
      {
        cabinClass: "economy",
        currency: "USD",
        departureDate: "2025-03-15",
        destination: "Tokyo",
        origin: "New York",
        passengers: 2,
      }
    );

    expect(result).toBeDefined();
    expect(result.agent).toBeDefined();
    expect(result.agentType).toBe("flightSearch");
  });

  it("should create an accommodation search agent", () => {
    const deps = createTestDeps();
    const result = createAgentForWorkflow(
      "accommodationSearch",
      deps,
      createTestConfig("accommodationAgent"),
      {
        checkIn: "2025-03-15",
        checkOut: "2025-03-20",
        destination: "Paris",
        guests: 2,
      }
    );

    expect(result).toBeDefined();
    expect(result.agent).toBeDefined();
    expect(result.agentType).toBe("accommodationSearch");
  });

  it("should create a destination research agent", () => {
    const deps = createTestDeps();
    const result = createAgentForWorkflow(
      "destinationResearch",
      deps,
      createTestConfig("destinationResearchAgent"),
      {
        destination: "Kyoto",
        specificInterests: ["temples", "gardens"],
      }
    );

    expect(result).toBeDefined();
    expect(result.agent).toBeDefined();
    expect(result.agentType).toBe("destinationResearch");
  });

  it("should create an itinerary planning agent", () => {
    const deps = createTestDeps();
    const result = createAgentForWorkflow(
      "itineraryPlanning",
      deps,
      createTestConfig("itineraryAgent"),
      {
        destination: "Rome",
        durationDays: 5,
        interests: ["history", "food"],
      }
    );

    expect(result).toBeDefined();
    expect(result.agent).toBeDefined();
    expect(result.agentType).toBe("itineraryPlanning");
  });

  it("should throw error for unsupported workflow kind", () => {
    const deps = createTestDeps();
    expect(() => {
      createAgentForWorkflow(
        // Intentionally pass an unsupported workflow kind to verify runtime guardrails
        "memoryUpdate" as unknown as "budgetPlanning",
        deps,
        createTestConfig("budgetAgent"),
        { destination: "Test", durationDays: 1 }
      );
    }).toThrow("Unsupported agent kind");
  });

  it("should throw error for invalid workflow kind", () => {
    const deps = createTestDeps();
    expect(() => {
      createAgentForWorkflow(
        // Intentionally pass an unsupported workflow kind to verify runtime guardrails
        "invalidWorkflow" as unknown as "budgetPlanning",
        deps,
        createTestConfig("budgetAgent"),
        { destination: "Test", durationDays: 1 }
      );
    }).toThrow("Unsupported agent kind");
  });

  it("should handle malformed config gracefully", () => {
    const deps = createTestDeps();
    const malformedConfig = {
      agentType: "budgetAgent" as const,
      createdAt: "2025-01-01T00:00:00.000Z",
      id: "test-config-id",
      model: "gpt-4" as const,
      parameters: {}, // Empty parameters should use defaults
      scope: "global" as const,
      updatedAt: "2025-01-01T00:00:00.000Z",
    };

    const result = createAgentForWorkflow("budgetPlanning", deps, malformedConfig, {
      destination: "Tokyo",
      durationDays: 7,
    });

    expect(result).toBeDefined();
    expect(result.agent).toBeDefined();
    expect(result.agentType).toBe("budgetPlanning");
  });

  it("should handle missing optional params", () => {
    const deps = createTestDeps();
    const result = createAgentForWorkflow(
      "budgetPlanning",
      deps,
      createTestConfig("budgetAgent"),
      {
        destination: "Tokyo",
        durationDays: 7,
        // Missing optional params like travelers
      }
    );

    expect(result).toBeDefined();
    expect(result.agent).toBeDefined();
    expect(result.agentType).toBe("budgetPlanning");
  });
});
