/**
 * @fileoverview Unit tests for chat sessions handler functions, testing session and
 * message CRUD operations with mocked Supabase client and authentication.
 */

import { describe, expect, it, vi } from "vitest";
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
type MessageRow = { session_id: string; [key: string]: unknown };

function supabase(
  userId: string | null,
  store: { sessions: SessionRow[]; messages: MessageRow[] }
) {
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
            return { error: null };
          }),
          maybeSingle: vi.fn(async () => ({
            data: store.sessions.find((s) => s.id) ?? null,
            error: null,
          })),
          order: vi.fn().mockResolvedValue({
            data: store.sessions.filter((s) => s.user_id === userId),
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
            return { error: null };
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
  } as any;
}

describe("sessions _handlers", () => {
  it("create/list session happy path", async () => {
    const store = { messages: [] as MessageRow[], sessions: [] as SessionRow[] };
    const s = supabase("u1", store);
    const res1 = await createSession({ supabase: s }, "Trip");
    expect(res1.status).toBe(201);
    const res2 = await listSessions({ supabase: s });
    expect(res2.status).toBe(200);
  });

  it("get/delete session auth gating", async () => {
    const store = {
      messages: [],
      sessions: [
        { created_at: "", id: "s1", metadata: {}, updated_at: "", user_id: "u2" },
      ],
    };
    const s = supabase("u2", store);
    const g = await getSession({ supabase: s }, "s1");
    expect(g.status).toBe(200);
    const d = await deleteSession({ supabase: s }, "s1");
    expect(d.status).toBe(204);
  });

  it("list/create messages happy path", async () => {
    const store = {
      messages: [] as MessageRow[],
      sessions: [{ id: "s1", user_id: "u3" }],
    };
    const s = supabase("u3", store);
    const r1 = await createMessage({ supabase: s }, "s1", {
      parts: [{ text: "hi", type: "text" }],
      role: "user",
    });
    expect(r1.status).toBe(201);
    const r2 = await listMessages({ supabase: s }, "s1");
    expect(r2.status).toBe(200);
  });
});
