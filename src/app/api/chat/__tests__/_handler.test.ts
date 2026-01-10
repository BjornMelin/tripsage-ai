/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockModel } from "@/test/ai-sdk/mock-model";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { createMockSupabaseClient } from "@/test/mocks/supabase";

vi.mock("server-only", () => ({}));

const insertSingleMock = vi.hoisted(() => vi.fn());
const updateSingleMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/supabase/typed-helpers", () => ({
  insertSingle: insertSingleMock,
  updateSingle: updateSingleMock,
}));

vi.mock("@/lib/memory/orchestrator", () => ({
  handleMemoryIntent: vi.fn(async () => ({ context: [] })),
}));

vi.mock("@/lib/memory/turn-utils", () => ({
  createTextMemoryTurn: vi.fn(() => ({ content: "", role: "assistant" })),
  persistMemoryTurn: vi.fn(async () => undefined),
  uiMessageToMemoryTurn: vi.fn(() => ({ content: "", role: "user" })),
}));

const captured = vi.hoisted(() => ({
  responseOptions: null as unknown,
  streamOptions: null as unknown,
  uiOptions: null as unknown,
  writer: null as unknown,
}));

const toUIMessageStreamMock = vi.hoisted(() =>
  vi.fn((options: unknown) => {
    captured.uiOptions = options;
    return new ReadableStream();
  })
);

const streamTextMock = vi.hoisted(() =>
  vi.fn(() => ({
    toUIMessageStream: toUIMessageStreamMock,
  }))
);

const createUIMessageStreamMock = vi.hoisted(() =>
  vi.fn(
    (options: {
      execute: (input: { writer: unknown }) => void;
      onFinish?: unknown;
      originalMessages?: unknown;
    }) => {
      const writer = {
        merge: vi.fn(),
        onError: undefined,
        write: vi.fn(),
      };
      captured.writer = writer;
      captured.streamOptions = options;
      options.execute({ writer });
      return new ReadableStream();
    }
  )
);

const createUIMessageStreamResponseMock = vi.hoisted(() =>
  vi.fn((options: unknown) => {
    captured.responseOptions = options;
    return new Response("ok", { status: 200 });
  })
);

vi.mock("ai", async () => {
  const actual = await vi.importActual<typeof import("ai")>("ai");
  return {
    ...actual,
    createUIMessageStream: createUIMessageStreamMock,
    createUIMessageStreamResponse: createUIMessageStreamResponseMock,
    streamText: streamTextMock,
  };
});

describe("handleChat", () => {
  beforeEach(() => {
    insertSingleMock.mockReset();
    updateSingleMock.mockReset();
    streamTextMock.mockClear();
    toUIMessageStreamMock.mockClear();
    createUIMessageStreamMock.mockClear();
    createUIMessageStreamResponseMock.mockClear();
    captured.uiOptions = null;
    captured.streamOptions = null;
    captured.responseOptions = null;
    captured.writer = null;
  });

  it("passes consumeSseStream and updates persistence on abort", async () => {
    const { consumeStream } = await import("ai");
    const { handleChat } = await import("../_handler");

    const userId = "11111111-1111-4111-8111-111111111111";
    const sessionId = "22222222-2222-4222-8222-222222222222";

    const supabase = createMockSupabaseClient({
      selectResults: {
        chat_sessions: {
          data: { id: sessionId, user_id: userId },
          error: null,
        },
      },
      user: { id: userId },
    });

    let messageInsertId = 100;
    insertSingleMock.mockImplementation((_client, table: string) => {
      if (table === "chat_messages") {
        messageInsertId += 1;
        return { data: { id: messageInsertId }, error: null };
      }
      return { data: null, error: null };
    });

    updateSingleMock.mockResolvedValue({ data: null, error: null });

    await handleChat(
      {
        resolveProvider: async () => ({
          model: createMockModel(),
          modelId: "gpt-4o",
          provider: "openai",
        }),
        supabase:
          unsafeCast<import("@/lib/supabase/server").TypedServerSupabase>(supabase),
      },
      {
        messages: [
          {
            id: "msg-1",
            parts: [{ text: "Hello", type: "text" }],
            role: "user",
          },
        ],
        sessionId,
        userId,
      }
    );

    expect(createUIMessageStreamResponseMock).toHaveBeenCalledTimes(1);
    const responseOpts = captured.responseOptions as {
      consumeSseStream?: unknown;
    };
    const streamOpts = captured.streamOptions as {
      onFinish?: (event: unknown) => PromiseLike<void> | void;
    };
    const uiOpts = captured.uiOptions as {
      messageMetadata?: (options: {
        part: {
          type: string;
          finishReason?: string;
          totalUsage?: unknown;
        };
      }) => unknown;
      sendSources?: boolean;
    };
    expect(typeof responseOpts.consumeSseStream).toBe("function");
    expect(responseOpts.consumeSseStream).toBe(consumeStream);
    expect(typeof uiOpts.messageMetadata).toBe("function");
    expect(uiOpts.sendSources).toBe(true);

    const usage = { completionTokens: 2, promptTokens: 1, totalTokens: 3 };
    const startMetadata = uiOpts.messageMetadata?.({ part: { type: "start" } }) as {
      requestId?: string;
      sessionId?: string;
    };
    expect(startMetadata).toMatchObject({ sessionId });
    expect(typeof startMetadata?.requestId).toBe("string");
    expect(
      uiOpts.messageMetadata?.({
        part: { finishReason: "stop", totalUsage: usage, type: "finish" },
      })
    ).toEqual({
      finishReason: "stop",
      requestId: expect.any(String),
      sessionId,
      totalUsage: usage,
    });

    await streamOpts.onFinish?.({
      finishReason: undefined,
      isAborted: true,
      isContinuation: false,
      messages: [],
      responseMessage: {
        id: "assistant-1",
        parts: [{ text: "partial answer", type: "text" }],
        role: "assistant",
      },
    });

    expect(updateSingleMock).toHaveBeenCalledTimes(1);
    const update = updateSingleMock.mock.calls[0]?.[2] as {
      content?: unknown;
      metadata?: unknown;
    };
    expect(typeof update.content).toBe("string");
    expect(update.content).toContain("partial answer");
    expect(update.metadata).toEqual(
      expect.objectContaining({ isAborted: true, status: "aborted" })
    );
  });

  it("returns provider_unavailable when provider resolution fails", async () => {
    const { handleChat } = await import("../_handler");

    const userId = "99999999-9999-4999-8999-999999999999";
    const sessionId = "88888888-8888-4888-8888-888888888888";

    const supabase = createMockSupabaseClient({
      selectResults: {
        chat_sessions: {
          data: { id: sessionId, user_id: userId },
          error: null,
        },
      },
      user: { id: userId },
    });

    const response = await handleChat(
      {
        resolveProvider: () => {
          throw new Error("No provider keys configured.");
        },
        supabase:
          unsafeCast<import("@/lib/supabase/server").TypedServerSupabase>(supabase),
      },
      {
        messages: [
          {
            id: "msg-1",
            parts: [{ text: "Hello", type: "text" }],
            role: "user",
          },
        ],
        sessionId,
        userId,
      }
    );

    expect(response.status).toBe(503);
    const json = await response.json();
    expect(json).toEqual(
      expect.objectContaining({
        error: "provider_unavailable",
      })
    );
  });

  it("does not 500 when history contains legacy model tool-call parts", async () => {
    const { handleChat } = await import("../_handler");

    const userId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
    const sessionId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

    const supabase = createMockSupabaseClient({
      selectResults: {
        chat_messages: {
          data: [
            {
              content: JSON.stringify([
                {
                  args: { query: "london" },
                  toolCallId: "call-legacy-1",
                  toolName: "webSearch",
                  type: "tool-call",
                },
              ]),
              id: 1,
              metadata: {},
              role: "assistant",
              session_id: sessionId,
              user_id: userId,
            },
          ],
          error: null,
        },
        chat_sessions: {
          data: { id: sessionId, user_id: userId },
          error: null,
        },
        chat_tool_calls: {
          data: [
            {
              arguments: { query: "london" },
              error_message: null,
              id: 1,
              message_id: 1,
              result: { fromCache: false, results: [], tookMs: 1 },
              status: "completed",
              tool_id: "call-legacy-1",
              tool_name: "webSearch",
            },
          ],
          error: null,
        },
      },
      user: { id: userId },
    });

    let messageInsertId = 100;
    insertSingleMock.mockImplementation((_client, table: string) => {
      if (table === "chat_messages") {
        messageInsertId += 1;
        return { data: { id: messageInsertId }, error: null };
      }
      return { data: null, error: null };
    });

    updateSingleMock.mockResolvedValue({ data: null, error: null });

    const res = await handleChat(
      {
        resolveProvider: async () => ({
          model: createMockModel(),
          modelId: "gpt-4o",
          provider: "openai",
        }),
        supabase:
          unsafeCast<import("@/lib/supabase/server").TypedServerSupabase>(supabase),
      },
      {
        messages: [
          {
            id: "msg-1",
            parts: [{ text: "Hello", type: "text" }],
            role: "user",
          },
        ],
        sessionId,
        userId,
      }
    );

    expect(res.status).toBe(200);
    expect(createUIMessageStreamResponseMock).toHaveBeenCalledTimes(1);
  });
});
