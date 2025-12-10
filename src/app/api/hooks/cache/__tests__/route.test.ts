/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { WebhookPayload } from "@/lib/webhooks/payload";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/helpers/route";

type ParseAndVerify = (req: Request) => Promise<ParseResult>;
type BumpTags = (tags: string[]) => Promise<number>;

type ParseResult = { ok: boolean; payload?: WebhookPayload };
type CacheRouteModule = typeof import("../route");

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

const parseAndVerifyMock = vi.hoisted(() => vi.fn<ParseAndVerify>());
const bumpTagsMock = vi.hoisted(() => vi.fn<BumpTags>(async () => 1));

vi.mock("@/lib/cache/tags", () => ({
  bumpTags: (tags: string[]) => bumpTagsMock(tags),
}));

// Mock telemetry span
vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: (
    _name: string,
    _opts: unknown,
    fn: (span: Record<string, unknown>) => unknown
  ) =>
    fn({
      addEvent: vi.fn(),
      recordException: vi.fn(),
      setAttribute: vi.fn(),
    }),
  withTelemetrySpanSync: (
    _name: string,
    _opts: unknown,
    fn: (span: Record<string, unknown>) => unknown
  ) =>
    fn({
      addEvent: vi.fn(),
      recordException: vi.fn(),
      setAttribute: vi.fn(),
    }),
}));

// Mock rate limiter
vi.mock("@/lib/webhooks/rate-limit", () => ({
  checkWebhookRateLimit: vi.fn(async () => ({ success: true })),
  createRateLimitHeaders: vi.fn(() => ({})),
}));

// Mock idempotency
vi.mock("@/lib/idempotency/redis", () => ({
  tryReserveKey: vi.fn(async () => true),
}));

// Mock buildEventKey
vi.mock("@/lib/webhooks/payload", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/webhooks/payload")>();
  return {
    ...actual,
    buildEventKey: vi.fn(() => "event-key-test"),
    parseAndVerify: (req: Request) => parseAndVerifyMock(req),
  };
});

function makeRequest(body: unknown, headers: Record<string, string> = {}) {
  return createMockNextRequest({
    body,
    headers,
    method: "POST",
    url: "http://localhost/api/hooks/cache",
  });
}

describe("POST /api/hooks/cache", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    parseAndVerifyMock.mockReset();
    bumpTagsMock.mockReset();
    bumpTagsMock.mockResolvedValue(1);
  });

  const loadRoute = async (): Promise<CacheRouteModule> => {
    return await import("../route");
  };

  it("returns 401 when signature verification fails", async () => {
    parseAndVerifyMock.mockResolvedValue({ ok: false });
    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    expect(res.status).toBe(401);
  });

  it("returns 401 when payload is missing (H3 abstraction behavior)", async () => {
    // Handler abstraction returns 401 for all parseAndVerify failures
    parseAndVerifyMock.mockResolvedValue({ ok: true, payload: undefined });
    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    expect(res.status).toBe(401);
    const json = await res.json();
    expect(json.error).toBe("invalid_signature");
  });

  it("processes empty table names via cache registry fallback", async () => {
    // Handler abstraction passes payload as-is; cache registry returns default tags
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: {},
        table: "",
        type: "INSERT",
      },
    });
    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.ok).toBe(true);
    // Empty table gets default tags from registry
    expect(bumpTagsMock).toHaveBeenCalledWith(["search", "cache"]);
  });

  it("returns correct tags for trips table", async () => {
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: { id: "trip-123" },
        table: "trips",
        type: "INSERT",
      },
    });

    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    const json = await res.json();

    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    expect(bumpTagsMock).toHaveBeenCalledWith([
      "trip",
      "user_trips",
      "trip_search",
      "search",
      "search_cache",
    ]);
  });

  it("returns correct tags for flights table", async () => {
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: { id: "flight-123" },
        table: "flights",
        type: "UPDATE",
      },
    });

    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    const json = await res.json();

    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    expect(bumpTagsMock).toHaveBeenCalledWith([
      "flight",
      "flight_search",
      "search",
      "search_cache",
    ]);
  });

  it("returns correct tags for accommodations table", async () => {
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: { id: "accom-123" },
        table: "accommodations",
        type: "DELETE",
      },
    });

    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    const json = await res.json();

    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    expect(bumpTagsMock).toHaveBeenCalledWith([
      "accommodation",
      "hotel_search",
      "search",
      "search_cache",
    ]);
  });

  it("returns correct tags for search_destinations table", async () => {
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: { id: "search-123" },
        table: "search_destinations",
        type: "INSERT",
      },
    });

    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    const json = await res.json();

    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    expect(bumpTagsMock).toHaveBeenCalledWith(["search", "search_cache"]);
  });

  it("returns correct tags for trip_collaborators table", async () => {
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: { id: "collab-123" },
        table: "trip_collaborators",
        type: "INSERT",
      },
    });

    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    const json = await res.json();

    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    expect(bumpTagsMock).toHaveBeenCalledWith(["trips", "users", "search"]);
  });

  it("returns correct tags for chat_messages table", async () => {
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: { id: "msg-123" },
        table: "chat_messages",
        type: "INSERT",
      },
    });

    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    const json = await res.json();

    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    expect(bumpTagsMock).toHaveBeenCalledWith([
      "memory",
      "conversation",
      "chat_memory",
    ]);
  });

  it("returns correct tags for chat_sessions table", async () => {
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: { id: "session-123" },
        table: "chat_sessions",
        type: "UPDATE",
      },
    });

    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    const json = await res.json();

    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    expect(bumpTagsMock).toHaveBeenCalledWith([
      "memory",
      "conversation",
      "chat_memory",
    ]);
  });

  it("returns generic tags for unknown table", async () => {
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: { id: "unknown-123" },
        table: "some_unknown_table",
        type: "INSERT",
      },
    });

    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    const json = await res.json();

    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    expect(bumpTagsMock).toHaveBeenCalledWith(["search", "cache"]);
  });

  it("returns bumped count in response", async () => {
    bumpTagsMock.mockResolvedValue(5);
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: { id: "trip-123" },
        table: "trips",
        type: "INSERT",
      },
    });

    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    const json = await res.json();

    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    expect(json.bumped).toBe(5);
  });
});
