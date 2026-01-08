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
  uiOptions: null as unknown,
}));

const toUIMessageStreamResponseMock = vi.hoisted(() =>
  vi.fn((options: unknown) => {
    captured.uiOptions = options;
    return new Response("ok", { status: 200 });
  })
);

const streamTextMock = vi.hoisted(() =>
  vi.fn(() => ({
    toUIMessageStreamResponse: toUIMessageStreamResponseMock,
  }))
);

vi.mock("ai", async () => {
  const actual = await vi.importActual<typeof import("ai")>("ai");
  return { ...actual, streamText: streamTextMock };
});

describe("handleChat", () => {
  beforeEach(() => {
    insertSingleMock.mockReset();
    updateSingleMock.mockReset();
    streamTextMock.mockClear();
    toUIMessageStreamResponseMock.mockClear();
    captured.uiOptions = null;
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

    expect(toUIMessageStreamResponseMock).toHaveBeenCalledTimes(1);
    const opts = captured.uiOptions as {
      consumeSseStream?: unknown;
      onFinish?: (event: unknown) => PromiseLike<void> | void;
    };
    expect(typeof opts.consumeSseStream).toBe("function");
    expect(opts.consumeSseStream).toBe(consumeStream);
    expect(typeof opts.onFinish).toBe("function");

    await opts.onFinish?.({
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
    expect(toUIMessageStreamResponseMock).toHaveBeenCalledTimes(1);
  });
});
