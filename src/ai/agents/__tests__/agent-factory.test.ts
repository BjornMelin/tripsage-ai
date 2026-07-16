/**
 * @vitest-environment node
 */

import { MockLanguageModelV4 } from "ai/test";
import { describe, expect, it, vi } from "vitest";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

// Mock server-only module before imports
vi.mock("server-only", () => ({}));

// Mock AI SDK ToolLoopAgent to capture constructor config
vi.mock("ai", async () => {
  const actual = await vi.importActual<typeof import("ai")>("ai");
  class MockToolLoopAgent {
    public id: string;
    public config: unknown;
    constructor(config: { id: string }) {
      this.id = config.id;
      this.config = config;
    }
  }
  return {
    ...actual,
    ToolLoopAgent: MockToolLoopAgent,
  };
});

// Mock telemetry
vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: () => ({
    error: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
  }),
}));

// Mock security random
vi.mock("@/lib/security/random", () => {
  let counter = 0;
  return {
    secureUuid: vi.fn(() => `test-uuid-${++counter}`),
  };
});

import { safeValidateUIMessages } from "ai";
import { createTripSageAgent } from "../agent-factory";
import type { AgentDependencies, TripSageAgentConfig } from "../types";
import { extractAgentParameters, prepareSchemaPrompt } from "../types";

/**
 * Creates a mock LanguageModel for testing.
 */
function createMockModel(): MockLanguageModelV4 {
  return new MockLanguageModelV4({
    modelId: "test-model",
    provider: "test-provider",
  });
}

/**
 * Creates test dependencies for agent creation.
 */
function createTestDeps(overrides: Partial<AgentDependencies> = {}): AgentDependencies {
  return {
    model: createMockModel(),
    modelId: "gpt-5.4-mini",
    userId: "test-user-123",
    ...overrides,
  };
}

describe("createTripSageAgent", () => {
  it("should create an agent with required configuration", () => {
    const deps = createTestDeps();
    const config: TripSageAgentConfig = {
      agentType: "budgetPlanning",
      instructions: "You are a budget planning assistant.",
      name: "Budget Agent",
      tools: {},
      uiMessages: [],
    };

    const result = createTripSageAgent(deps, config);

    expect(result).toBeDefined();
    expect(result.agent).toBeDefined();
    expect(result.uiMessages).toEqual(config.uiMessages);

    // Verify agent has expected properties from config
    expect(result.agent.id).toContain("tripsage-budgetPlanning");
    const { config: agentSettings } = unsafeCast<{
      config: Record<string, unknown>;
    }>(result.agent);
    expect(agentSettings).toMatchObject({
      repairToolCall: expect.any(Function),
      runtimeContext: {
        agentType: "budgetPlanning",
        modelId: "gpt-5.4-mini",
      },
      telemetry: {
        functionId: "agent.budgetPlanning",
        includeRuntimeContext: {
          agentType: true,
          modelId: true,
        },
        recordInputs: false,
        recordOutputs: false,
      },
    });
    expect(agentSettings).not.toHaveProperty("experimental_repairToolCall");
    expect(agentSettings).not.toHaveProperty("experimental_telemetry");
  });

  it("should create an agent with optional parameters", () => {
    const deps = createTestDeps();
    const config: TripSageAgentConfig = {
      agentType: "flightSearch",
      headers: { "x-agent-test": "forwarded" },
      instructions: "You are a flight search assistant.",
      maxOutputTokens: 2048,
      name: "Flight Agent",
      stepLimit: 15,
      temperature: 0.5,
      tools: {},
      topP: 0.9,
      uiMessages: [],
    };

    const result = createTripSageAgent(deps, config);

    expect(result).toBeDefined();
    expect(result.uiMessages).toEqual(config.uiMessages);
    const { config: agentSettings } = unsafeCast<{
      config: Record<string, unknown>;
    }>(result.agent);
    expect(agentSettings).toMatchObject({
      headers: { "x-agent-test": "forwarded" },
      maxOutputTokens: 2048,
      topP: 0.9,
    });
    expect(agentSettings).not.toHaveProperty("agentType");
    expect(agentSettings).not.toHaveProperty("name");
    expect(agentSettings).not.toHaveProperty("stepLimit");
    expect(agentSettings).not.toHaveProperty("uiMessages");
  });

  it("should use default values when optional parameters not provided", () => {
    const deps = createTestDeps({ userId: undefined });
    const config: TripSageAgentConfig = {
      agentType: "destinationResearch",
      instructions: "You are a destination research assistant.",
      name: "Destination Agent",
      tools: {},
      uiMessages: [],
    };

    const result = createTripSageAgent(deps, config);

    expect(result).toBeDefined();
    expect(result.agent).toBeDefined();
  });
});

describe("extractAgentParameters", () => {
  it("should extract parameters with defaults", () => {
    const config = {
      agentType: "budgetAgent" as const,
      createdAt: "2025-01-01T00:00:00.000Z",
      id: "test-id",
      isEnabled: true,
      model: "gpt-5.4-mini" as const,
      parameters: {},
      scope: "global" as const,
      updatedAt: "2025-01-01T00:00:00.000Z",
    };

    const params = extractAgentParameters(config);

    expect(params.stepLimit).toBe(10);
    expect(params.maxOutputTokens).toBe(4096);
    expect(params.temperature).toBe(0.3);
    expect(params.topP).toBeUndefined();
  });

  it("should extract custom parameters", () => {
    const config = {
      agentType: "flightAgent" as const,
      createdAt: "2025-01-01T00:00:00.000Z",
      id: "test-id",
      isEnabled: true,
      model: "gpt-5.4-mini" as const,
      parameters: {
        maxOutputTokens: 8192,
        stepLimit: 20,
        temperature: 0.7,
        topP: 0.95,
      },
      scope: "global" as const,
      updatedAt: "2025-01-01T00:00:00.000Z",
    };

    const params = extractAgentParameters(config);

    expect(params.stepLimit).toBe(20);
    expect(params.maxOutputTokens).toBe(8192);
    expect(params.temperature).toBe(0.7);
    expect(params.topP).toBe(0.95);
  });
});

describe("prepareSchemaPrompt", () => {
  it("produces a native UIMessage contract", async () => {
    const result = prepareSchemaPrompt({
      instructions: "Return a flight search response.",
      maxOutputTokens: 1024,
      modelId: "gpt-5.4-mini",
      userPrompt: 'Return schemaVersion="flight.v2".',
    });

    expect(result.uiMessages).toEqual([
      {
        id: expect.any(String),
        parts: [{ text: 'Return schemaVersion="flight.v2".', type: "text" }],
        role: "user",
      },
    ]);
    await expect(
      safeValidateUIMessages({ messages: result.uiMessages })
    ).resolves.toMatchObject({ success: true });
  });
});
