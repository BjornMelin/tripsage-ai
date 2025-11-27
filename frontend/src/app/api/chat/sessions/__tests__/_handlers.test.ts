/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import {
  createMessage,
  createSession,
  deleteSession,
  getSession,
  listMessages,
  listSessions,
} from "../_handlers";

/**
 * Creates a mock Supabase client for testing with in-memory data stores.
 *
 * @param userId - User ID for authentication mocking, or null for unauthenticated.
 * @param store - In-memory data store for sessions and messages.
 * @returns Mock Supabase client with basic CRUD operations.
 */
type SessionRow = { id: string; [key: string]: unknown };
type MessageRow = { sessionId: string; [key: string]: unknown };

type MockSupabaseClient = {
  auth: {
    getUser: ReturnType<typeof vi.fn>;
  };
  from: ReturnType<typeof vi.fn>;
};

function supabase(
  userId: string | null,
  store: { sessions: SessionRow[]; messages: MessageRow[] }
): MockSupabaseClient {
  return {
    auth: {
      getUser: vi.fn(async () => ({ data: { user: userId ? { id: userId } : null } })),
    },
    from: vi.fn((table: string) => {
      if (table === "chat_sessions") {
        return {
          delete: vi.fn().mockReturnThis(),
          eq: vi.fn().mockReturnThis(),
          insert: vi.fn((row: SessionRow) => {
            store.sessions.push(row);
            return {
              select: vi.fn().mockReturnValue({
                single: vi.fn().mockResolvedValue({
                  data: row,
                  error: null,
                }),
              }),
            };
          }),
          maybeSingle: vi.fn(async () => ({
            data: store.sessions.find((s) => s.id) ?? null,
            error: null,
          })),
          order: vi.fn().mockResolvedValue({
            data: store.sessions.filter((s) => s.userId === userId),
            error: null,
          }),
          select: vi.fn().mockReturnThis(),
        };
      }
      if (table === "chat_messages") {
        return {
          eq: vi.fn().mockReturnThis(),
          insert: vi.fn((row: MessageRow) => {
            store.messages.push(row);
            return {
              select: vi.fn().mockReturnValue({
                single: vi.fn().mockResolvedValue({
                  data: row,
                  error: null,
                }),
              }),
            };
          }),
          order: vi.fn().mockResolvedValue({
            data: store.messages.filter((m) => m.session_id),
            error: null,
          }),
          select: vi.fn().mockReturnThis(),
        };
      }
      return {};
    }),
  };
}

describe("sessions _handlers", () => {
  it("create/list session happy path", async () => {
    const store = { messages: [] as MessageRow[], sessions: [] as SessionRow[] };
    const s = supabase("u1", store) as unknown as TypedServerSupabase;
    const res1 = await createSession({ supabase: s, userId: "u1" }, "Trip");
    expect(res1.status).toBe(201);
    const res2 = await listSessions({ supabase: s, userId: "u1" });
    expect(res2.status).toBe(200);
  });

  it("get/delete session auth gating", async () => {
    const store = {
      messages: [],
      sessions: [
        { createdAt: "", id: "s1", metadata: {}, updatedAt: "", userId: "u2" },
      ],
    };
    const s = supabase("u2", store) as unknown as TypedServerSupabase;
    const g = await getSession({ supabase: s, userId: "u2" }, "s1");
    expect(g.status).toBe(200);
    const d = await deleteSession({ supabase: s, userId: "u2" }, "s1");
    expect(d.status).toBe(204);
  });

  it("list/create messages happy path", async () => {
    const store = {
      messages: [] as MessageRow[],
      sessions: [{ id: "s1", userId: "u3" }],
    };
    const s = supabase("u3", store) as unknown as TypedServerSupabase;
    const r1 = await createMessage({ supabase: s, userId: "u3" }, "s1", {
      parts: [{ text: "hi", type: "text" }],
      role: "user",
    });
    expect(r1.status).toBe(201);
    const r2 = await listMessages({ supabase: s, userId: "u3" }, "s1");
    expect(r2.status).toBe(200);
  });
});
