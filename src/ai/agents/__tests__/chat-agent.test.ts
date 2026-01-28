/**
 * @vitest-environment node
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock server-only module before imports
vi.mock("server-only", () => ({}));

// Mock ToolLoopAgent before other mocks
const mockToolLoopAgent = vi.fn();
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
    mockToolLoopAgent(config);
    Object.assign(this as object, { config, ...mockAgent });
    return this;
  };

  return {
    convertToModelMessages: vi.fn().mockResolvedValue([]),
    createAgentUIStreamResponse: vi.fn(),
    generateText: vi.fn(),
    InvalidToolInputError: { isInstance: () => false },
    NoSuchToolError: { isInstance: () => false },
    Output: { object: vi.fn((value) => value) },
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
type CountTokens = (texts: string[], modelId?: string) => number;

const tokenMocks = vi.hoisted(() => ({
  clampMaxTokens: vi.fn(() => ({ maxOutputTokens: 1024, reasons: [] })),
  countTokens: vi.fn<CountTokens>((texts, modelId) => {
    if (texts.length > 0 && modelId) return 100;
    return 100;
  }),
}));
vi.mock("@/lib/tokens/budget", () => ({
  clampMaxTokens: tokenMocks.clampMaxTokens,
  countTokens: tokenMocks.countTokens,
}));

const limitMocks = vi.hoisted(() => ({
  getModelContextLimit: vi.fn(() => 128000),
}));
vi.mock("@/lib/tokens/limits", () => ({
  getModelContextLimit: limitMocks.getModelContextLimit,
}));

// Mock AI tools
const mockTools = vi.hoisted(() => {
  const tools = {
    crawlSite: { description: "crawl", execute: vi.fn() },
    distanceMatrix: { description: "distance", execute: vi.fn() },
    geocode: { description: "geocode", execute: vi.fn() },
    getCurrentWeather: { description: "weather", execute: vi.fn() },
    getTravelAdvisory: { description: "advisory", execute: vi.fn() },
    searchFlights: { description: "flights", execute: vi.fn() },
    searchPlaceDetails: { description: "place details", execute: vi.fn() },
    searchPlaces: { description: "places", execute: vi.fn() },
    tripsSavePlace: { description: "save place", execute: vi.fn() },
    webSearch: { description: "web search", execute: vi.fn() },
    webSearchBatch: { description: "batch search", execute: vi.fn() },
  };
  return { toolRegistry: tools, tools };
});
vi.mock("@ai/tools", () => mockTools);

// Mock tool injection
vi.mock("@ai/tools/server/injection", () => ({
  wrapToolsWithChatId: vi.fn().mockImplementation((tools: unknown) => tools),
  wrapToolsWithUserId: vi.fn().mockReturnValue(mockTools.tools),
}));

import type { LanguageModel, UIMessage } from "ai";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { createChatAgent, validateChatMessages } from "../chat-agent";
import type { AgentDependencies } from "../types";

/**
 * Creates a mock LanguageModel for testing.
 */
function createMockModel(): LanguageModel {
  return unsafeCast<LanguageModel>({
    defaultObjectGenerationMode: "json",
    doGenerate: vi.fn(),
    doStream: vi.fn(),
    modelId: "test-model",
    provider: "test-provider",
    specificationVersion: "V3",
    supportsStructuredOutputs: true,
  });
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
  return unsafeCast<UIMessage[]>([
    {
      id: "1",
      parts: [{ text: "Hello", type: "text" }],
      role: "user",
    },
  ]);
}

describe("createChatAgent", () => {
  beforeEach(() => {
    mockToolLoopAgent.mockClear();
    tokenMocks.clampMaxTokens.mockReset();
    tokenMocks.clampMaxTokens.mockReturnValue({ maxOutputTokens: 1024, reasons: [] });
    tokenMocks.countTokens.mockReset();
    tokenMocks.countTokens.mockReturnValue(100);
    limitMocks.getModelContextLimit.mockReset();
    limitMocks.getModelContextLimit.mockReturnValue(128000);
  });

  it("should create a chat agent with required config", () => {
    const deps = createTestDeps();
    const messages = createTestMessages();
    const result = createChatAgent(deps, messages, {
      desiredMaxTokens: 4096,
      stepLimit: 20,
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
      stepLimit: 10,
    });

    expect(result.modelId).toBe("claude-3-opus");
  });

  it("should include memory summary in instructions when provided", () => {
    const deps = createTestDeps();
    const messages = createTestMessages();

    const result = createChatAgent(deps, messages, {
      desiredMaxTokens: 2048,
      memorySummary: "User prefers boutique hotels.",
      stepLimit: 10,
    });

    expect(result).toBeDefined();
    expect(result.agent).toBeDefined();
    expect(mockToolLoopAgent).toHaveBeenCalledWith(
      expect.objectContaining({
        instructions: expect.stringContaining("User prefers boutique hotels."),
      })
    );
  });

  it("compresses context and keeps adjacent tool call/result pairs together", async () => {
    const ContextLimit = 2158; // Context limit for this test model
    const CompressionTrigger = 9999; // Token count that forces compression path
    const SystemTokens = 10;
    const UserMessageTokens = 60;
    const ToolCallTokens = 20;

    limitMocks.getModelContextLimit.mockReturnValue(ContextLimit);
    tokenMocks.countTokens.mockImplementation((texts: string[]) => {
      if (texts.some((t) => t.includes("test message"))) return SystemTokens;
      if (texts.length > 1) return CompressionTrigger;

      const joined = texts.join(" ");
      if (joined.includes("system")) return SystemTokens;
      if (joined.includes("old")) return UserMessageTokens;
      if (joined.includes("searchFlights")) return ToolCallTokens;
      if (joined.includes("tool-result-text")) return ToolCallTokens;
      if (joined.includes("recent")) return UserMessageTokens;
      return 1;
    });

    const deps = createTestDeps();
    const messages = createTestMessages();
    createChatAgent(deps, messages, { desiredMaxTokens: 4096, stepLimit: 20 });

    expect(mockToolLoopAgent).toHaveBeenCalled();
    const toolLoopConfig = mockToolLoopAgent.mock.calls[0]?.[0];
    const prepareStep = unsafeCast<{ prepareStep?: unknown }>(
      toolLoopConfig
    ).prepareStep;
    expect(typeof prepareStep).toBe("function");

    const stepMessages = unsafeCast<import("ai").ModelMessage[]>([
      { content: "system", role: "system" },
      { content: "old", role: "user" },
      {
        content: [
          {
            input: { query: "paris" },
            toolCallId: "call-1",
            toolName: "searchFlights",
            type: "tool-call",
          },
        ],
        role: "assistant",
      },
      {
        content: [
          {
            output: { type: "text", value: "tool-result-text" },
            toolCallId: "call-1",
            type: "tool-result",
          },
        ],
        role: "tool",
      },
      { content: "recent", role: "user" },
    ]);

    const prepared = await unsafeCast<
      (args: { messages: import("ai").ModelMessage[]; stepNumber: number }) => unknown
    >(prepareStep)({ messages: stepMessages, stepNumber: 1 });

    const keptMessages =
      unsafeCast<{ messages?: import("ai").ModelMessage[] }>(prepared).messages ?? [];

    expect(keptMessages.map((m) => m.role)).toEqual([
      "system",
      "assistant",
      "tool",
      "user",
    ]);
    expect(keptMessages.map((m) => m.content)).toEqual([
      "system",
      stepMessages[2]?.content,
      stepMessages[3]?.content,
      "recent",
    ]);
  });
});

describe("validateChatMessages", () => {
  it("should pass valid messages", () => {
    const validMessages = createTestMessages();

    const result = validateChatMessages(validMessages);
    expect(result.valid).toBe(true);
  });

  it("should return error for invalid attachments", async () => {
    vi.resetModules();

    vi.doMock("@/app/api/_helpers/attachments", () => ({
      extractTexts: () => ["test message"],
      validateImageAttachments: vi.fn(() => ({
        error: "Invalid attachment",
        reason: "Unsupported format",
        valid: false,
      })),
    }));

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
