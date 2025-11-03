/**
 * @fileoverview Integration tests for chat sessions and messages API routes,
 * covering session CRUD operations, message management, and route interactions
 * with mocked Supabase database operations.
 */

import { describe, expect, it, vi } from "vitest";
import { GET as MSG_GET, POST as MSG_POST } from "../[id]/messages/route";
import { DELETE as SESS_ID_DELETE, GET as SESS_ID_GET } from "../[id]/route";
import { GET as SESS_GET, POST as SESS_POST } from "../route";

/**
 * Builds a mock Request object for testing API routes.
 *
 * @param method - HTTP method for the request.
 * @param url - Request URL string.
 * @param body - Optional request body object to be JSON stringified.
 * @param headers - Optional additional headers to merge with defaults.
 * @returns Mock Request object for testing.
 */
function buildReq(method: string, url: string, body?: any, headers?: any): any {
  return new Request(url, {
    body: body ? JSON.stringify(body) : undefined,
    headers: { "content-type": "application/json", ...(headers || {}) },
    method,
  }) as any;
}

vi.mock("@/lib/supabase/server", () => {
  const store: Record<string, any[]> = { chat_messages: [], chat_sessions: [] };
  return {
    createServerSupabase: vi.fn(async () => ({
      auth: {
        getUser: vi.fn(async () => ({ data: { user: { id: "u1" } } })),
      },
      from: vi.fn((table: string) => {
        const rows = store[table] ?? (store[table] = []);
        const api: any = {
          _rows: rows,
          delete: vi.fn(() => ({
            eq: vi.fn(() => ({
              eq: vi.fn(async () => {
                store[table] = [];
                return { error: null };
              }),
            })),
          })),
          eq: vi.fn(() => api),
          insert: vi.fn(async (payload: any) => {
            if (Array.isArray(payload)) {
              for (const p of payload) rows.push(p);
            } else {
              rows.push(payload);
            }
            return { error: null };
          }),
          limit: vi.fn(() => api),
          maybeSingle: vi.fn(async () => ({ data: api._rows[0] ?? null, error: null })),
          order: vi.fn(async () => ({ data: api._rows, error: null })),
          select: vi.fn(() => api),
        };
        return api;
      }),
    })),
  };
});

describe("chat sessions/messages routes", () => {
  it("creates and lists sessions", async () => {
    const resCreate = await SESS_POST(
      buildReq("POST", "http://x/sessions", { title: "Trip" })
    );
    expect(resCreate.status).toBe(201);
    const { id } = (await resCreate.json()) as any;
    expect(typeof id).toBe("string");

    const resList = await SESS_GET();
    expect(resList.status).toBe(200);
    const list = (await resList.json()) as any[];
    expect(list.length).toBe(1);
    expect(list[0].id).toBe(id);
  });

  it("gets and deletes a session", async () => {
    // create
    const resCreate = await SESS_POST(buildReq("POST", "http://x/sessions", {}));
    const { id } = (await resCreate.json()) as any;
    // get
    const resGet = await SESS_ID_GET(
      {} as any,
      { params: Promise.resolve({ id }) } as any
    );
    expect(resGet.status).toBe(200);
    // delete
    const resDel = await SESS_ID_DELETE(
      {} as any,
      { params: Promise.resolve({ id }) } as any
    );
    expect(resDel.status).toBe(204);
  });

  it("creates and lists messages for a session", async () => {
    // create session
    const resCreate = await SESS_POST(buildReq("POST", "http://x/sessions", {}));
    const { id } = (await resCreate.json()) as any;

    // post message
    const resMsg = await MSG_POST(
      buildReq("POST", `http://x/sessions/${id}/messages`, {
        parts: [{ text: "hi", type: "text" }],
        role: "user",
      }),
      { params: Promise.resolve({ id }) } as any
    );
    expect(resMsg.status).toBe(201);

    // list messages
    const resList = await MSG_GET(
      {} as any,
      { params: Promise.resolve({ id }) } as any
    );
    expect(resList.status).toBe(200);
    const msgs = (await resList.json()) as any[];
    expect(Array.isArray(msgs)).toBe(true);
  });
});
