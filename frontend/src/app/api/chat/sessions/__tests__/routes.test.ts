/**
 * @fileoverview Integration tests for chat sessions and messages API routes,
 * covering session CRUD operations, message management, and route interactions
 * with mocked Supabase database operations.
 */

import type { NextRequest } from "next/server";
import { describe, expect, it, vi } from "vitest";
import { GET as MSG_GET, POST as MSG_POST } from "../[id]/messages/route";
import { DELETE as SESS_ID_DELETE, GET as SESS_ID_GET } from "../[id]/route";
import { GET as SESS_GET, POST as SESS_POST } from "../route";

/**
 * Builds a mock NextRequest object for testing API routes.
 *
 * @param method - HTTP method for the request.
 * @param url - Request URL string.
 * @param body - Optional request body object to be JSON stringified.
 * @param headers - Optional additional headers to merge with defaults.
 * @returns Mock NextRequest object for testing.
 */
function buildReq(
  method: string,
  url: string,
  body?: unknown,
  headers?: Record<string, string>
): NextRequest {
  const request = new Request(url, {
    body: body ? JSON.stringify(body) : undefined,
    headers: { "content-type": "application/json", ...(headers || {}) },
    method,
  });

  // Create a mock NextRequest by defining properties on the Request object
  const nextRequest = request as NextRequest & {
    cookies: { delete: () => void; get: () => string | undefined; set: () => void };
    nextUrl: URL;
    page: { name?: string; params?: Record<string, string> };
    ua: { browser?: { name?: string; version?: string }; device?: { type?: string } };
  };

  Object.defineProperty(nextRequest, "cookies", {
    value: {
      delete: vi.fn(),
      get: vi.fn(() => undefined),
      getAll: vi.fn(() => []),
      has: vi.fn(() => false),
      set: vi.fn(),
    },
    writable: false,
  });

  Object.defineProperty(nextRequest, "nextUrl", {
    value: new URL(url),
    writable: false,
  });

  Object.defineProperty(nextRequest, "page", {
    value: {},
    writable: false,
  });

  Object.defineProperty(nextRequest, "ua", {
    value: {
      browser: { name: "test", version: "1.0" },
      cpu: { architecture: "test" },
      device: { model: "test", type: "desktop", vendor: "test" },
      engine: { name: "test", version: "1.0" },
      os: { name: "test", version: "1.0" },
      ua: "test-user-agent",
    },
    writable: false,
  });

  return nextRequest;
}

vi.mock("@/lib/supabase/server", () => {
  type StoreRow = Record<string, unknown>;
  type MockQueryBuilder = {
    _rows: StoreRow[];
    delete: ReturnType<typeof vi.fn>;
    eq: ReturnType<typeof vi.fn>;
    insert: ReturnType<typeof vi.fn>;
    limit: ReturnType<typeof vi.fn>;
    maybeSingle: ReturnType<typeof vi.fn>;
    order: ReturnType<typeof vi.fn>;
    select: ReturnType<typeof vi.fn>;
  };

  const store: Record<string, StoreRow[]> = { chat_messages: [], chat_sessions: [] };
  return {
    createServerSupabase: vi.fn(async () => ({
      auth: {
        getUser: vi.fn(async () => ({ data: { user: { id: "u1" } } })),
      },
      from: vi.fn((table: string) => {
        if (!store[table]) {
          store[table] = [];
        }
        const rows = store[table];
        const api: MockQueryBuilder = {
          _rows: rows,
          delete: vi.fn(() => ({
            eq: vi.fn(() => ({
              eq: vi.fn(() => {
                store[table] = [];
                return Promise.resolve({ error: null });
              }),
            })),
          })),
          eq: vi.fn(() => api),
          insert: vi.fn((payload: unknown) => {
            if (Array.isArray(payload)) {
              for (const p of payload) rows.push(p);
            } else {
              rows.push(payload as StoreRow);
            }
            return Promise.resolve({ error: null });
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
    const { id } = (await resCreate.json()) as { id: string };
    expect(typeof id).toBe("string");

    const resList = await SESS_GET();
    expect(resList.status).toBe(200);
    const list = (await resList.json()) as Array<{ id: string }>;
    expect(list.length).toBe(1);
    expect(list[0].id).toBe(id);
  });

  it("gets and deletes a session", async () => {
    // create
    const resCreate = await SESS_POST(buildReq("POST", "http://x/sessions", {}));
    const { id } = (await resCreate.json()) as { id: string };
    // get
    const resGet = await SESS_ID_GET(buildReq("GET", "http://x/"), {
      params: Promise.resolve({ id }),
    });
    expect(resGet.status).toBe(200);
    // delete
    const resDel = await SESS_ID_DELETE(buildReq("DELETE", "http://x/"), {
      params: Promise.resolve({ id }),
    });
    expect(resDel.status).toBe(204);
  });

  it("creates and lists messages for a session", async () => {
    // create session
    const resCreate = await SESS_POST(buildReq("POST", "http://x/sessions", {}));
    const { id } = (await resCreate.json()) as { id: string };

    // post message
    const resMsg = await MSG_POST(
      buildReq("POST", `http://x/sessions/${id}/messages`, {
        parts: [{ text: "hi", type: "text" }],
        role: "user",
      }),
      {
        params: Promise.resolve({ id }),
      }
    );
    expect(resMsg.status).toBe(201);

    // list messages
    const resList = await MSG_GET(buildReq("GET", "http://x/"), {
      params: Promise.resolve({ id }),
    });
    expect(resList.status).toBe(200);
    const msgs = (await resList.json()) as Array<unknown>;
    expect(Array.isArray(msgs)).toBe(true);
  });
});
