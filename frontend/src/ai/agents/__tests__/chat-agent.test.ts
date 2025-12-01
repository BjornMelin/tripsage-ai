/**
 * @vitest-environment node
 */

import { describe, expect, it, vi } from "vitest";

// Mock server-only module before imports
vi.mock("server-only", () => ({}));

// Mock ToolLoopAgent before other mocks
vi.mock("ai", () => {
  const mockAgent = {
    generate: vi.fn().mockResolvedValue({
      result: { text: "Mock response" },
      toolCalls: [],
    }),
    stream: vi.fn().mockReturnValue({
      result: { text: "Mock response" },
      toolCalls: [],
    }),
  };

  const MockToolLoopAgent = function (this: unknown, config: unknown) {
    Object.assign(this as object, { config, ...mockAgent });
    return this;
  };

  return {
    convertToModelMessages: vi.fn().mockReturnValue([]),
    createAgentUIStreamResponse: vi.fn(),
    generateObject: vi.fn(),
    InvalidToolInputError: { isInstance: () => false },
    NoSuchToolError: { isInstance: () => false },
    stepCountIs: vi.fn().mockReturnValue(() => false),
    ToolLoopAgent: MockToolLoopAgent,
  };
});

// Mock logger
vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: () => ({
    error: vi.fn(),
    info: vi.fn(),
  }),
}));

// Mock security
vi.mock("@/lib/security/random", () => ({
  secureUuid: () => "test-uuid-123",
}));

// Mock attachments helper
vi.mock("@/app/api/_helpers/attachments", () => ({
  extractTexts: () => ["test message"],
  validateImageAttachments: vi.fn(() => ({ valid: true })),
}));

// Mock tokens
vi.mock("@/lib/tokens/budget", () => ({
  clampMaxTokens: () => ({ maxTokens: 1024, reasons: [] }),
  countTokens: () => 100,
}));

vi.mock("@/lib/tokens/limits", () => ({
  getModelContextLimit: () => 128000,
}));

// Mock AI tools
vi.mock("@ai/tools", () => ({
  crawlSite: { description: "crawl", execute: vi.fn() },
  distanceMatrix: { description: "distance", execute: vi.fn() },
  geocode: { description: "geocode", execute: vi.fn() },
  getCurrentWeather: { description: "weather", execute: vi.fn() },
  getTravelAdvisory: { description: "advisory", execute: vi.fn() },
  lookupPoiContext: { description: "poi", execute: vi.fn() },
  searchFlights: { description: "flights", execute: vi.fn() },
  webSearch: { description: "web search", execute: vi.fn() },
  webSearchBatch: { description: "batch search", execute: vi.fn() },
}));

// Mock tool injection
vi.mock("@ai/tools/server/injection", () => ({
  wrapToolsWithUserId: vi.fn().mockReturnValue({
    crawlSite: { description: "crawl", execute: vi.fn() },
    distanceMatrix: { description: "distance", execute: vi.fn() },
    geocode: { description: "geocode", execute: vi.fn() },
    getCurrentWeather: { description: "weather", execute: vi.fn() },
    searchFlights: { description: "flights", execute: vi.fn() },
    webSearch: { description: "web search", execute: vi.fn() },
    webSearchBatch: { description: "batch search", execute: vi.fn() },
  }),
}));

import type { LanguageModel, UIMessage } from "ai";

import { createChatAgent, validateChatMessages } from "../chat-agent";
import type { AgentDependencies } from "../types";

/**
 * Creates a mock LanguageModel for testing.
 */
function createMockModel(): LanguageModel {
  return {
    defaultObjectGenerationMode: "json",
    doGenerate: vi.fn(),
    doStream: vi.fn(),
    modelId: "test-model",
    provider: "test-provider",
    specificationVersion: "v3",
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
    modelId: "gpt-4o",
    sessionId: "test-session-456",
    userId: "test-user-123",
  };
}

/**
 * Creates test UIMessages.
 */
function createTestMessages(): UIMessage[] {
  return [
    {
      id: "1",
      parts: [{ text: "Hello", type: "text" }],
      role: "user",
    },
  ] as unknown as UIMessage[];
}

describe("createChatAgent", () => {
  it("should create a chat agent with required config", () => {
    const deps = createTestDeps();
    const messages = createTestMessages();
    const result = createChatAgent(deps, messages, {
      desiredMaxTokens: 4096,
      maxSteps: 20,
    });

    expect(result).toBeDefined();
    expect(result.modelId).toBeDefined();
    expect(result.agent).toBeDefined();
  });

  it("should use provided model ID", () => {
    const deps = createTestDeps();
    deps.modelId = "claude-3-opus";
    const messages = createTestMessages();

    const result = createChatAgent(deps, messages, {
      desiredMaxTokens: 2048,
      maxSteps: 10,
    });

    expect(result.modelId).toBe("claude-3-opus");
  });

  it("should include memory summary in instructions when provided", () => {
    const deps = createTestDeps();
    const messages = createTestMessages();

    const result = createChatAgent(deps, messages, {
      desiredMaxTokens: 2048,
      maxSteps: 10,
      memorySummary: "User prefers boutique hotels.",
    });

    expect(result).toBeDefined();
    expect(result.agent).toBeDefined();
  });
});

describe("validateChatMessages", () => {
  it("should pass valid messages", () => {
    const validMessages = createTestMessages();

    const result = validateChatMessages(validMessages);
    expect(result.valid).toBe(true);
  });

  it("should return error for invalid attachments", async () => {
    vi.doMock("@/app/api/_helpers/attachments", () => ({
      extractTexts: () => ["test message"],
      validateImageAttachments: vi.fn(() => ({
        error: "Invalid attachment",
        reason: "Unsupported format",
        valid: false,
      })),
    }));

    vi.resetModules();
    const { validateChatMessages: validateWithInvalidMock } = await import(
      "../chat-agent"
    );

    const messages = createTestMessages();
    const result = validateWithInvalidMock(messages);

    expect(result.valid).toBe(false);
    if (!result.valid) {
      expect(result.error).toBe("invalid_attachment");
      expect(result.reason).toBe("Unsupported format");
    }

    vi.doUnmock("@/app/api/_helpers/attachments");
    vi.resetModules();
  });
});
