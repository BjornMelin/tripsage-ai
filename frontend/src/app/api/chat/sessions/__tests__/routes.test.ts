import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/route-helpers";
import { GET as MSG_GET, POST as MSG_POST } from "../[id]/messages/route";
import { DELETE as SESS_ID_DELETE, GET as SESS_ID_GET } from "../[id]/route";
import { GET as SESS_GET, POST as SESS_POST } from "../route";

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

// Mock Supabase server client
vi.mock("@/lib/supabase/server", () => {
  type StoreRow = Record<string, unknown>;
  type MockQueryBuilder = {
    rows: StoreRow[];
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
          maybeSingle: vi.fn(async () => ({ data: api.rows[0] ?? null, error: null })),
          order: vi.fn(async () => ({ data: api.rows, error: null })),
          rows,
          select: vi.fn(() => api),
        };
        return api;
      }),
    })),
  };
});

// Mock Redis
vi.mock("@/lib/redis", () => ({
  getRedis: vi.fn(() => Promise.resolve({})),
}));

// Mock route helpers
vi.mock("@/lib/next/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/next/route-helpers")>(
    "@/lib/next/route-helpers"
  );
  return {
    ...actual,
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

describe("/api/chat/sessions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  it("creates and lists sessions", async () => {
    const resCreate = await SESS_POST(
      createMockNextRequest({
        body: { title: "Trip" },
        method: "POST",
        url: "http://x/sessions",
      })
    );
    expect(resCreate.status).toBe(201);
    const { id } = (await resCreate.json()) as { id: string };
    expect(typeof id).toBe("string");

    const resList = await SESS_GET(
      createMockNextRequest({
        method: "GET",
        url: "http://x/sessions",
      })
    );
    expect(resList.status).toBe(200);
    const list = (await resList.json()) as Array<{ id: string }>;
    expect(list.length).toBe(1);
    expect(list[0].id).toBe(id);
  });

  it("gets and deletes a session", async () => {
    // create
    const resCreate = await SESS_POST(
      createMockNextRequest({
        body: {},
        method: "POST",
        url: "http://x/sessions",
      })
    );
    const { id } = (await resCreate.json()) as { id: string };
    // get
    const resGet = await SESS_ID_GET(
      createMockNextRequest({
        method: "GET",
        url: "http://x/",
      }),
      {
        params: Promise.resolve({ id }),
      }
    );
    expect(resGet.status).toBe(200);
    // delete
    const resDel = await SESS_ID_DELETE(
      createMockNextRequest({
        method: "DELETE",
        url: "http://x/",
      }),
      {
        params: Promise.resolve({ id }),
      }
    );
    expect(resDel.status).toBe(204);
  });

  it("creates and lists messages for a session", async () => {
    // create session
    const resCreate = await SESS_POST(
      createMockNextRequest({
        body: {},
        method: "POST",
        url: "http://x/sessions",
      })
    );
    const { id } = (await resCreate.json()) as { id: string };

    // post message
    const resMsg = await MSG_POST(
      createMockNextRequest({
        body: {
          parts: [{ text: "hi", type: "text" }],
          role: "user",
        },
        method: "POST",
        url: `http://x/sessions/${id}/messages`,
      }),
      {
        params: Promise.resolve({ id }),
      }
    );
    expect(resMsg.status).toBe(201);

    // list messages
    const resList = await MSG_GET(
      createMockNextRequest({
        method: "GET",
        url: "http://x/",
      }),
      {
        params: Promise.resolve({ id }),
      }
    );
    expect(resList.status).toBe(200);
    const msgs = (await resList.json()) as Array<unknown>;
    expect(Array.isArray(msgs)).toBe(true);
  });
});
