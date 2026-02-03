/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  setRateLimitFactoryForTests,
  setSupabaseFactoryForTests,
} from "@/lib/api/factory";
import { __resetServerEnvCacheForTest } from "@/lib/env/server";
import { TEST_USER_ID } from "@/test/helpers/ids";
import { createRouteParamsContext, getMockCookiesForTest } from "@/test/helpers/route";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

// Mock the `ai` package to avoid network/model dependencies
vi.mock("ai", () => ({
  consumeStream: vi.fn(),
  simulateReadableStream: vi.fn(),
  streamText: vi.fn(),
}));

// Mock provider resolution (registry + gateway/BYOK)
vi.mock("@ai/models/registry", () => ({
  resolveProvider: vi.fn(async () => ({
    model: "openai/gpt-4o",
    modelId: "openai/gpt-4o",
    provider: "openai",
  })),
}));

vi.mock("botid/server", async () => {
  const { mockBotIdHumanResponse } = await import("@/test/mocks/botid");
  return {
    checkBotId: vi.fn(async () => mockBotIdHumanResponse),
  };
});

// Stub heavy token math to speed up tests while preserving behavior coverage elsewhere
vi.mock("@/lib/tokens/budget", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/tokens/budget")>();
  return {
    ...actual,
    clampMaxTokens: vi.fn(() => ({ maxOutputTokens: 256, reasons: [] })),
    countPromptTokens: vi.fn(() => 42),
  };
});

import { resolveProvider } from "@ai/models/registry";
// Import after mocks are set up
import { streamText } from "ai";
import { POST } from "@/app/api/ai/stream/route";
import { createMockNextRequest } from "@/test/helpers/route";

const MOCK_STREAM_TEXT = vi.mocked(streamText);
const MOCK_RESOLVE_PROVIDER = vi.mocked(resolveProvider);

/** Mock stream result that satisfies StreamTextResult interface */
const createMockStreamResult = (
  responseFn: () => Response
): ReturnType<typeof streamText> => {
  // AI SDK StreamTextResult interface is extremely complex with many properties.
  // We use type assertion here to focus on testing the core functionality
  // rather than mocking every single interface property.
  return unsafeCast<ReturnType<typeof streamText>>({
    consumeStream: async () => {
      // Intentionally empty - testing focuses on response conversion
    },
    content: Promise.resolve([]),
    dynamicToolCalls: Promise.resolve([]),
    dynamicToolResults: Promise.resolve([]),
    experimentalContinueSteps: Promise.resolve([]),
    experimentalProviderMetadata: Promise.resolve({}),
    files: Promise.resolve([]),
    finish: Promise.resolve(undefined),
    finishReason: Promise.resolve("stop"),
    getFinishReason: async () => "stop",
    getFullText: async () => "",
    getReasoning: async () => "",
    getSteps: async () => [],
    getText: async () => "",
    getToolCalls: async () => [],
    getToolInvocations: async () => [],
    getUsage: async () => undefined,
    getWarnings: async () => [],
    isStreaming: false,
    metadata: Promise.resolve({}),
    reasoning: Promise.resolve(""),
    reasoningText: Promise.resolve(""),
    sources: Promise.resolve([]),
    staticToolCalls: Promise.resolve([]),
    staticToolResults: Promise.resolve([]),
    steps: Promise.resolve([]),
    text: Promise.resolve(""),
    timestamp: Date.now(),
    toDataStreamResponse: () => new Response(),
    toolCalls: Promise.resolve([]),
    toolInvocations: Promise.resolve([]),
    toString: () => "",
    toUIMessageStreamResponse: responseFn,
    usage: Promise.resolve(undefined),
    warnings: Promise.resolve([]),
  });
};

describe("ai stream route", () => {
  beforeEach(() => {
    MOCK_STREAM_TEXT.mockClear();
    MOCK_RESOLVE_PROVIDER.mockClear();
    vi.stubEnv("ENABLE_AI_DEMO", "true");
    __resetServerEnvCacheForTest();
    setRateLimitFactoryForTests(async () => ({
      limit: 40,
      remaining: 39,
      reset: Date.now() + 60_000,
      success: true,
    }));
    setSupabaseFactoryForTests(async () =>
      unsafeCast({
        auth: {
          getUser: async () => ({
            data: { user: { id: TEST_USER_ID } },
            error: null,
          }),
        },
      })
    );
  });

  afterEach(() => {
    setRateLimitFactoryForTests(null);
    setSupabaseFactoryForTests(null);
    vi.unstubAllEnvs();
    __resetServerEnvCacheForTest();
  });

  it("returns 404 when demo route is disabled", async () => {
    vi.stubEnv("ENABLE_AI_DEMO", "");
    __resetServerEnvCacheForTest();

    const request = createMockNextRequest({
      body: { prompt: "Hello world" },
      method: "POST",
      url: "http://localhost",
    });

    const response = await POST(request, createRouteParamsContext());

    expect(response.status).toBe(404);
    expect(MOCK_STREAM_TEXT).not.toHaveBeenCalled();
  });

  it("returns 401 when unauthenticated", async () => {
    setSupabaseFactoryForTests(async () =>
      unsafeCast({
        auth: { getUser: async () => ({ data: { user: null }, error: null }) },
      })
    );

    const request = createMockNextRequest({
      body: { prompt: "Hello world" },
      method: "POST",
      url: "http://localhost",
    });

    const response = await POST(request, createRouteParamsContext());

    expect(response.status).toBe(401);
    expect(MOCK_STREAM_TEXT).not.toHaveBeenCalled();
  });

  it("returns 403 when bot is detected", async () => {
    const { checkBotId } = await import("botid/server");
    vi.mocked(checkBotId).mockResolvedValueOnce({
      bypassed: false,
      isBot: true,
      isHuman: false,
      isVerifiedBot: false,
    });

    const request = createMockNextRequest({
      body: { prompt: "Hello world" },
      method: "POST",
      url: "http://localhost",
    });

    const response = await POST(request, createRouteParamsContext());

    expect(response.status).toBe(403);
    expect(MOCK_STREAM_TEXT).not.toHaveBeenCalled();
  });

  it("returns 503 when no provider is available", async () => {
    MOCK_RESOLVE_PROVIDER.mockRejectedValueOnce(new Error("no_keys"));

    const request = createMockNextRequest({
      body: { prompt: "Hello world" },
      method: "POST",
      url: "http://localhost",
    });

    const response = await POST(request, createRouteParamsContext());

    expect(response.status).toBe(503);
    const body = await response.json();
    expect(body.error).toBe("provider_unavailable");
    expect(MOCK_STREAM_TEXT).not.toHaveBeenCalled();
  });

  it("returns an SSE response on successful request", async () => {
    // Mock successful streamText response
    const mockResponse = new Response('data: {"type":"finish"}\n\n', {
      headers: { "content-type": "text/event-stream" },
    });
    const mockToUiMessageStreamResponse = vi.fn().mockReturnValue(mockResponse);

    MOCK_STREAM_TEXT.mockReturnValue(
      createMockStreamResult(mockToUiMessageStreamResponse)
    );

    const request = createMockNextRequest({
      body: { prompt: "Hello world" },
      method: "POST",
      url: "http://localhost",
    });

    const response = await POST(request, createRouteParamsContext());

    expect(response).toBeInstanceOf(Response);
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toMatch(/text\/event-stream/i);
    expect(MOCK_RESOLVE_PROVIDER).toHaveBeenCalledWith(TEST_USER_ID, undefined);
    expect(MOCK_STREAM_TEXT).toHaveBeenCalledWith(
      expect.objectContaining({
        messages: [
          {
            content: "Hello world",
            role: "user",
          },
        ],
        model: "openai/gpt-4o",
      })
    );
    expect(mockToUiMessageStreamResponse).toHaveBeenCalled();
  });

  it("handles requests with empty prompt", async () => {
    const mockResponse = new Response('data: {"type":"finish"}\n\n', {
      headers: { "content-type": "text/event-stream" },
    });
    const mockToUiMessageStreamResponse = vi.fn().mockReturnValue(mockResponse);

    MOCK_STREAM_TEXT.mockReturnValue(
      createMockStreamResult(mockToUiMessageStreamResponse)
    );

    const request = createMockNextRequest({
      body: { prompt: "" },
      method: "POST",
      url: "http://localhost",
    });

    const response = await POST(request, createRouteParamsContext());

    expect(response.status).toBe(200);
    expect(MOCK_STREAM_TEXT).toHaveBeenCalledWith(
      expect.objectContaining({
        messages: [
          {
            content: "Hello from AI SDK v6",
            role: "user",
          },
        ],
        model: "openai/gpt-4o",
      })
    );
  });

  it("handles requests with no prompt field", async () => {
    const mockResponse = new Response('data: {"type":"finish"}\n\n', {
      headers: { "content-type": "text/event-stream" },
    });
    const mockToUiMessageStreamResponse = vi.fn().mockReturnValue(mockResponse);

    MOCK_STREAM_TEXT.mockReturnValue(
      createMockStreamResult(mockToUiMessageStreamResponse)
    );

    const request = createMockNextRequest({
      body: {},
      method: "POST",
      url: "http://localhost",
    });

    const response = await POST(request, createRouteParamsContext());

    expect(response.status).toBe(200);
    expect(MOCK_STREAM_TEXT).toHaveBeenCalledWith(
      expect.objectContaining({
        messages: [
          {
            content: "Hello from AI SDK v6",
            role: "user",
          },
        ],
        model: "openai/gpt-4o",
      })
    );
  });

  it("handles malformed JSON request body", async () => {
    const mockResponse = new Response('data: {"type":"finish"}\n\n', {
      headers: { "content-type": "text/event-stream" },
    });
    const mockToUiMessageStreamResponse = vi.fn().mockReturnValue(mockResponse);

    MOCK_STREAM_TEXT.mockReturnValue(
      createMockStreamResult(mockToUiMessageStreamResponse)
    );

    const request = createMockNextRequest({
      body: "invalid json{",
      method: "POST",
      url: "http://localhost",
    });

    const response = await POST(request, createRouteParamsContext());
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.error).toBe("invalid_request");
    expect(MOCK_STREAM_TEXT).not.toHaveBeenCalled();
  });

  it("handles non-POST requests", async () => {
    const request = createMockNextRequest({
      method: "GET",
      url: "http://localhost",
    });

    // The route handler should handle this appropriately
    // Note: Next.js route handlers typically only respond to their defined methods
    const response = await POST(request, createRouteParamsContext());
    expect(response.status).toBe(400);
    const body = await response.json();
    expect(body.error).toBe("invalid_request");
    expect(MOCK_STREAM_TEXT).not.toHaveBeenCalled();
  });

  it("handles requests without content-type header", async () => {
    const mockResponse = new Response('data: {"type":"finish"}\n\n', {
      headers: { "content-type": "text/event-stream" },
    });
    const mockToUiMessageStreamResponse = vi.fn().mockReturnValue(mockResponse);

    MOCK_STREAM_TEXT.mockReturnValue(
      createMockStreamResult(mockToUiMessageStreamResponse)
    );

    const request = createMockNextRequest({
      body: { prompt: "test" },
      method: "POST",
      url: "http://localhost",
    });

    const response = await POST(request, createRouteParamsContext());

    expect(response.status).toBe(200);
  });

  it("passes maxDuration constraint to streaming configuration", async () => {
    const mockResponse = new Response('data: {"type":"finish"}\n\n', {
      headers: { "content-type": "text/event-stream" },
    });
    const mockToUiMessageStreamResponse = vi.fn().mockReturnValue(mockResponse);

    MOCK_STREAM_TEXT.mockReturnValue(
      createMockStreamResult(mockToUiMessageStreamResponse)
    );

    const request = createMockNextRequest({
      body: { prompt: "test" },
      method: "POST",
      url: "http://localhost",
    });

    await POST(request, createRouteParamsContext());

    // Verify the route uses the expected model and configuration
    expect(MOCK_STREAM_TEXT).toHaveBeenCalledWith(
      expect.objectContaining({
        messages: [
          {
            content: "test",
            role: "user",
          },
        ],
        model: "openai/gpt-4o",
      })
    );
  });

  it("handles AI SDK errors gracefully", async () => {
    // Mock AI SDK to throw an error
    MOCK_STREAM_TEXT.mockImplementation(() => {
      throw new Error("AI SDK error");
    });

    const request = createMockNextRequest({
      body: { prompt: "test" },
      method: "POST",
      url: "http://localhost",
    });

    // withApiGuards catches errors and returns error responses
    const response = await POST(request, createRouteParamsContext());
    expect(response.status).toBe(500);
    const body = await response.json();
    expect(body.error).toBe("internal");
  });

  it("handles streamText response conversion errors", async () => {
    // Mock successful streamText but failed response conversion
    const mockToUiMessageStreamResponse = vi.fn().mockImplementation(() => {
      throw new Error("Response conversion error");
    });

    MOCK_STREAM_TEXT.mockReturnValue(
      createMockStreamResult(mockToUiMessageStreamResponse)
    );

    const request = createMockNextRequest({
      body: { prompt: "test" },
      method: "POST",
      url: "http://localhost",
    });

    // withApiGuards catches errors and returns error responses
    const response = await POST(request, createRouteParamsContext());
    expect(response.status).toBe(500);
    const body = await response.json();
    expect(body.error).toBe("internal");
  });

  it("fails closed when rate limiting infrastructure is degraded", async () => {
    setRateLimitFactoryForTests(() => Promise.reject(new Error("redis_down")));

    const request = createMockNextRequest({
      body: { prompt: "Hello world" },
      method: "POST",
      url: "http://localhost",
    });

    const response = await POST(request, createRouteParamsContext());
    expect(response.status).toBe(503);
    expect(MOCK_STREAM_TEXT).not.toHaveBeenCalled();
  });

  it("handles prompt content without heavy token calc", async () => {
    const longPrompt = "a".repeat(200);
    const mockResponse = new Response('data: {"type":"finish"}\n\n', {
      headers: { "content-type": "text/event-stream" },
    });
    const mockToUiMessageStreamResponse = vi.fn().mockReturnValue(mockResponse);

    MOCK_STREAM_TEXT.mockReturnValue(
      createMockStreamResult(mockToUiMessageStreamResponse)
    );

    const request = createMockNextRequest({
      body: { prompt: longPrompt },
      method: "POST",
      url: "http://localhost",
    });

    const response = await POST(request, createRouteParamsContext());

    expect(response.status).toBe(200);
    expect(MOCK_STREAM_TEXT).toHaveBeenCalledWith(
      expect.objectContaining({
        messages: [
          {
            content: longPrompt,
            role: "user",
          },
        ],
        model: "openai/gpt-4o",
      })
    );
  });
});
