/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import type { TypedAdminSupabase } from "@/lib/supabase/admin";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { handleMemorySyncJob } from "../_handler";

const SESSION_ID = "123e4567-e89b-12d3-a456-426614174000";
const USER_ID = "11111111-1111-4111-8111-111111111111";

type ExistingTurn = Record<string, unknown>;

function createSupabaseMock({ existingTurns = [] as ExistingTurn[] } = {}) {
  const turnsInsertSpy = vi.fn().mockResolvedValue({ error: null });

  const chatSessionsSelectBuilder = {
    eq: vi.fn(),
    single: vi.fn().mockResolvedValue({ data: { id: SESSION_ID }, error: null }),
  };
  chatSessionsSelectBuilder.eq.mockReturnValue(chatSessionsSelectBuilder);

  const memoriesSessionSelectBuilder = {
    eq: vi.fn(),
    single: vi.fn().mockResolvedValue({ data: { id: SESSION_ID }, error: null }),
  };
  memoriesSessionSelectBuilder.eq.mockReturnValue(memoriesSessionSelectBuilder);

  const memoriesSessionsSelect = vi.fn(() => memoriesSessionSelectBuilder);
  const memoriesSessionsUpdate = vi.fn(() => ({
    eq: vi.fn().mockResolvedValue({ data: null, error: null }),
  }));

  const turnsSelectBuilder = {
    eq: vi.fn(),
    in: vi.fn().mockResolvedValue({ data: existingTurns, error: null }),
  };
  turnsSelectBuilder.eq.mockReturnValue(turnsSelectBuilder);

  const fromMemories = (table: string) => {
    if (table === "sessions") {
      return {
        insert: vi.fn().mockResolvedValue({ error: null }),
        select: memoriesSessionsSelect,
        update: memoriesSessionsUpdate,
      };
    }
    if (table === "turns") {
      return {
        insert: turnsInsertSpy,
        select: vi.fn(() => turnsSelectBuilder),
      };
    }
    return {};
  };

  const fromPublic = (table: string) => {
    if (table === "chat_sessions") {
      return {
        select: vi.fn(() => chatSessionsSelectBuilder),
        update: vi.fn(() => ({
          eq: vi.fn().mockResolvedValue({ data: null, error: null }),
        })),
      };
    }
    return {};
  };

  const supabase = {
    from: vi.fn(fromPublic),
    schema: vi.fn(() => ({
      from: vi.fn(fromMemories),
    })),
  };

  return { supabase: unsafeCast<TypedAdminSupabase>(supabase), turnsInsertSpy };
}

describe("handleMemorySyncJob", () => {
  it("preserves valid message timestamps", async () => {
    const { supabase, turnsInsertSpy } = createSupabaseMock();
    const now = "2025-01-01T00:00:00Z";
    const messageTimestamp = "2024-12-31T12:00:00Z";

    await handleMemorySyncJob(
      { clock: { now: () => now }, supabase },
      {
        conversationMessages: [
          {
            content: "Hello world",
            role: "user",
            timestamp: messageTimestamp,
          },
        ],
        sessionId: SESSION_ID,
        syncType: "conversation",
        userId: USER_ID,
      }
    );

    expect(turnsInsertSpy).toHaveBeenCalledTimes(1);
    const inserts = unsafeCast<unknown[]>(turnsInsertSpy.mock.calls[0]?.[0]);
    const insert = unsafeCast<Record<string, unknown>>(inserts[0]);
    expect(insert.created_at).toBe(messageTimestamp);
  });

  it("falls back to clock when timestamps are invalid", async () => {
    const { supabase, turnsInsertSpy } = createSupabaseMock();
    const now = "2025-01-01T00:00:00Z";

    await handleMemorySyncJob(
      { clock: { now: () => now }, supabase },
      {
        conversationMessages: [
          {
            content: "Hello world",
            role: "user",
            timestamp: "not-a-date",
          },
        ],
        sessionId: SESSION_ID,
        syncType: "conversation",
        userId: USER_ID,
      }
    );

    expect(turnsInsertSpy).toHaveBeenCalledTimes(1);
    const inserts = unsafeCast<unknown[]>(turnsInsertSpy.mock.calls[0]?.[0]);
    const insert = unsafeCast<Record<string, unknown>>(inserts[0]);
    expect(insert.created_at).toBe(now);
  });

  it("does not dedupe turns with different tool metadata", async () => {
    const { supabase, turnsInsertSpy } = createSupabaseMock({
      existingTurns: [
        {
          attachments: [],
          content: { text: "Hello world" },
          created_at: "2024-12-31T12:00:00Z",
          role: "assistant",
          tool_calls: [],
          tool_results: [],
        },
      ],
    });

    await handleMemorySyncJob(
      { clock: { now: () => "2025-01-01T00:00:00Z" }, supabase },
      {
        conversationMessages: [
          {
            content: "Hello world",
            metadata: {
              toolCalls: [{ args: { ok: true }, name: "test-tool" }],
            },
            role: "assistant",
            timestamp: "2024-12-31T12:00:00Z",
          },
        ],
        sessionId: SESSION_ID,
        syncType: "conversation",
        userId: USER_ID,
      }
    );

    expect(turnsInsertSpy).toHaveBeenCalledTimes(1);
    const inserts = unsafeCast<unknown[]>(turnsInsertSpy.mock.calls[0]?.[0]);
    expect(inserts).toHaveLength(1);
  });
});
