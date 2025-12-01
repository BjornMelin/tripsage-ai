/**
 * @vitest-environment node
 */

import { describe, expect, it, vi } from "vitest";

// Mock server-only module before imports
vi.mock("server-only", () => ({}));

// Mock telemetry
vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: () => ({
    error: vi.fn(),
    info: vi.fn(),
  }),
}));

// Mock security random
vi.mock("@/lib/security/random", () => {
  let counter = 0;
  return {
    secureUuid: vi.fn(() => `test-uuid-${++counter}`),
  };
});

import { InvalidToolInputError, type LanguageModel, NoSuchToolError } from "ai";

import { createTripSageAgent, isToolError } from "../agent-factory";
import type { AgentDependencies, TripSageAgentConfig } from "../types";
import { extractAgentParameters } from "../types";

/**
 * Creates a mock LanguageModel for testing.
 */
function createMockModel(): LanguageModel {
  return {
    defaultObjectGenerationMode: "json",
    doGenerate: vi.fn(async () => ({
      finishReason: "stop",
      rawCall: { rawPrompt: null, rawSettings: {} },
      response: {
        id: "test-response-id",
        modelId: "test-model",
        timestamp: new Date(),
      },
      text: "Test response",
      usage: { completionTokens: 10, promptTokens: 10 },
    })),
    doStream: vi.fn(async () => ({
      rawCall: { rawPrompt: null, rawSettings: {} },
      stream: new ReadableStream(),
    })),
    modelId: "test-model",
    provider: "test-provider",
    specificationVersion: "V3",
    supportsStructuredOutputs: true,
  } as unknown as LanguageModel;
}

/**
 * Creates test dependencies for agent creation.
 */
function createTestDeps(overrides: Partial<AgentDependencies> = {}): AgentDependencies {
  return {
    identifier: "test-user-123",
    model: createMockModel(),
    modelId: "gpt-4",
    sessionId: "test-session-456",
    userId: "test-user-123",
    ...overrides,
  };
}

describe("createTripSageAgent", () => {
  it("should create an agent with required configuration", () => {
    const deps = createTestDeps();
    const config: TripSageAgentConfig = {
      agentType: "budgetPlanning",
      defaultMessages: [],
      instructions: "You are a budget planning assistant.",
      name: "Budget Agent",
      tools: {},
    };

    const result = createTripSageAgent(deps, config);

    expect(result).toBeDefined();
    expect(result.agentType).toBe("budgetPlanning");
    expect(result.modelId).toBe("gpt-4");
    expect(result.agent).toBeDefined();
    expect(result.defaultMessages).toEqual(config.defaultMessages);

    // Verify agent has expected properties from config
    expect(result.agent.id).toContain("tripsage-budgetPlanning");
    expect(result.agent.instructions).toBe(config.instructions);
    expect(result.agent.tools).toBe(config.tools);
  });

  it("should create an agent with optional parameters", () => {
    const deps = createTestDeps();
    const config: TripSageAgentConfig = {
      agentType: "flightSearch",
      defaultMessages: [],
      instructions: "You are a flight search assistant.",
      maxOutputTokens: 2048,
      maxSteps: 15,
      name: "Flight Agent",
      temperature: 0.5,
      tools: {},
      topP: 0.9,
    };

    const result = createTripSageAgent(deps, config);

    expect(result).toBeDefined();
    expect(result.agentType).toBe("flightSearch");
  });

  it("should use default values when optional parameters not provided", () => {
    const deps = createTestDeps({
      sessionId: undefined,
      userId: undefined,
    });
    const config: TripSageAgentConfig = {
      agentType: "destinationResearch",
      defaultMessages: [],
      instructions: "You are a destination research assistant.",
      name: "Destination Agent",
      tools: {},
    };

    const result = createTripSageAgent(deps, config);

    expect(result).toBeDefined();
    expect(result.agentType).toBe("destinationResearch");
    // Verify that undefined sessionId/userId are handled gracefully
    expect(result.agent).toBeDefined();
    // Agent should be created even without sessionId/userId
    expect(result.modelId).toBe("gpt-4");

    // Verify telemetry metadata handles undefined sessionId/userId
    // When undefined, these fields are not included in metadata (no fallback values)
    const telemetryConfig = result.agent.experimental_telemetry;
    expect(telemetryConfig).toBeDefined();
    expect(telemetryConfig?.metadata).toBeDefined();
    expect(telemetryConfig?.metadata).toMatchObject({
      agentType: "destinationResearch",
      identifier: "test-user-123",
      modelId: "gpt-4",
    });
    // Verify sessionId and userId are not present in metadata when undefined
    expect(telemetryConfig?.metadata).not.toHaveProperty("sessionId");
    expect(telemetryConfig?.metadata).not.toHaveProperty("userId");
  });
});

describe("extractAgentParameters", () => {
  it("should extract parameters with defaults", () => {
    const config = {
      agentType: "budgetAgent" as const,
      createdAt: "2025-01-01T00:00:00.000Z",
      id: "test-id",
      isEnabled: true,
      model: "gpt-4" as const,
      parameters: {},
      scope: "global" as const,
      updatedAt: "2025-01-01T00:00:00.000Z",
    };

    const params = extractAgentParameters(config);

    expect(params.maxSteps).toBe(10);
    expect(params.maxTokens).toBe(4096);
    expect(params.temperature).toBe(0.3);
    expect(params.topP).toBeUndefined();
  });

  it("should extract custom parameters", () => {
    const config = {
      agentType: "flightAgent" as const,
      createdAt: "2025-01-01T00:00:00.000Z",
      id: "test-id",
      isEnabled: true,
      model: "gpt-4" as const,
      parameters: {
        maxSteps: 20,
        maxTokens: 8192,
        temperature: 0.7,
        topP: 0.95,
      },
      scope: "global" as const,
      updatedAt: "2025-01-01T00:00:00.000Z",
    };

    const params = extractAgentParameters(config);

    expect(params.maxSteps).toBe(20);
    expect(params.maxTokens).toBe(8192);
    expect(params.temperature).toBe(0.7);
    expect(params.topP).toBe(0.95);
  });
});

describe("isToolError", () => {
  it("should return false for non-tool errors", () => {
    expect(isToolError(new Error("Generic error"))).toBe(false);
    expect(isToolError(null)).toBe(false);
    expect(isToolError(undefined)).toBe(false);
    expect(isToolError("string error")).toBe(false);
  });

  it("should return true for NoSuchToolError instances", () => {
    const toolError = new NoSuchToolError({
      toolName: "nonexistentTool",
    });
    expect(isToolError(toolError)).toBe(true);
  });

  it("should return true for InvalidToolInputError instances", () => {
    const inputError = new InvalidToolInputError({
      cause: new Error("test"),
      toolInput: "invalid",
      toolName: "testTool",
    });
    expect(isToolError(inputError)).toBe(true);
  });
});
