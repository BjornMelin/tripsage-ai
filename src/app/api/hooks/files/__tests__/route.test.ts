/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { WebhookPayload } from "@/lib/webhooks/payload";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/helpers/route";

type ParseAndVerify = (req: Request) => Promise<ParseResult>;
type BuildEventKey = (payload: WebhookPayload) => string;
type TryReserveKey = (key: string, ttlSeconds?: number) => Promise<boolean>;

type ParseResult = { ok: boolean; payload?: WebhookPayload };
type FilesRouteModule = typeof import("../route");

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

const parseAndVerifyMock = vi.hoisted(() => vi.fn<ParseAndVerify>());
const buildEventKeyMock = vi.hoisted(() =>
  vi.fn<BuildEventKey>(() => "file-event-key-1")
);
const tryReserveKeyMock = vi.hoisted(() => vi.fn<TryReserveKey>(async () => true));

function createSupabaseStub(error: Error | null = null) {
  const single = vi.fn(async () => ({
    data: error ? null : { id: "file-123" },
    error,
  }));
  const limit = vi.fn(() => ({ single }));
  const eq = vi.fn(() => ({ limit }));
  const select = vi.fn(() => ({ eq }));
  const from = vi.fn(() => ({ select }));
  return { from };
}

let supabaseFactory = () => createSupabaseStub();

vi.mock("@/lib/webhooks/payload", () => ({
  buildEventKey: (payload: WebhookPayload) => buildEventKeyMock(payload),
  parseAndVerify: (req: Request) => parseAndVerifyMock(req),
}));

vi.mock("@/lib/idempotency/redis", () => ({
  tryReserveKey: (key: string, ttl?: number) => tryReserveKeyMock(key, ttl),
}));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminSupabase: vi.fn(() => supabaseFactory()),
}));

// Mock telemetry span
vi.mock("@/lib/telemetry/span", () => ({
  recordErrorOnSpan: vi.fn(),
  recordTelemetryEvent: vi.fn(),
  sanitizeAttributes: vi.fn((attrs) => attrs),
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

function makeRequest(body: unknown, headers: Record<string, string> = {}) {
  return createMockNextRequest({
    body,
    headers,
    method: "POST",
    url: "http://localhost/api/hooks/files",
  });
}

describe("POST /api/hooks/files", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    parseAndVerifyMock.mockReset();
    buildEventKeyMock.mockReset();
    buildEventKeyMock.mockReturnValue("file-event-key-1");
    tryReserveKeyMock.mockReset();
    tryReserveKeyMock.mockResolvedValue(true);
    supabaseFactory = () => createSupabaseStub();
  });

  const loadRoute = async (): Promise<FilesRouteModule> => {
    return await import("../route");
  };

  it("returns 401 when signature or payload is invalid", async () => {
    parseAndVerifyMock.mockResolvedValue({ ok: false });
    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    expect(res.status).toBe(401);
  });

  it("returns 401 when payload is missing", async () => {
    parseAndVerifyMock.mockResolvedValue({ ok: true, payload: undefined });
    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    expect(res.status).toBe(401);
  });

  it("skips non-file_attachments tables", async () => {
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: {},
        table: "other_table",
        type: "INSERT",
      },
    });
    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    const json = await res.json();
    expect(res.status).toBe(200);
    expect(json.skipped).toBe(true);
  });

  it("marks duplicates via idempotency guard", async () => {
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: { id: "file-123", upload_status: "uploading" },
        table: "file_attachments",
        type: "INSERT",
      },
    });
    tryReserveKeyMock.mockResolvedValue(false);
    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    const json = await res.json();
    expect(res.status).toBe(200);
    expect(json.duplicate).toBe(true);
    expect(json.ok).toBe(true);
    expect(tryReserveKeyMock).toHaveBeenCalledWith("file-event-key-1", 300);
  });

  it("processes INSERT with uploading status successfully", async () => {
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: { id: "file-123", upload_status: "uploading" },
        table: "file_attachments",
        type: "INSERT",
      },
    });
    tryReserveKeyMock.mockResolvedValue(true);
    supabaseFactory = () => createSupabaseStub(null);

    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    const json = await res.json();
    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    expect(json.duplicate).toBeUndefined();
    expect(json.skipped).toBeUndefined();
  });

  it("returns 500 on Supabase query error", async () => {
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: { id: "file-123", upload_status: "uploading" },
        table: "file_attachments",
        type: "INSERT",
      },
    });
    tryReserveKeyMock.mockResolvedValue(true);
    supabaseFactory = () => createSupabaseStub(new Error("Database error"));

    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    expect(res.status).toBe(500);
  });

  it("skips DB check for non-INSERT operations", async () => {
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: { id: "file-123", upload_status: "completed" },
        record: { id: "file-123", upload_status: "completed" },
        table: "file_attachments",
        type: "UPDATE",
      },
    });
    tryReserveKeyMock.mockResolvedValue(true);
    const selectSpy = vi.fn();
    supabaseFactory = () => {
      const stub = createSupabaseStub();
      stub.from = vi.fn(() => ({ select: selectSpy }));
      return stub;
    };

    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    const json = await res.json();
    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    // select should not be called for UPDATE
    expect(selectSpy).not.toHaveBeenCalled();
  });

  it("skips DB check for non-uploading status", async () => {
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: { id: "file-123", upload_status: "completed" },
        table: "file_attachments",
        type: "INSERT",
      },
    });
    tryReserveKeyMock.mockResolvedValue(true);
    const selectSpy = vi.fn();
    supabaseFactory = () => {
      const stub = createSupabaseStub();
      stub.from = vi.fn(() => ({ select: selectSpy }));
      return stub;
    };

    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    const json = await res.json();
    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    // select should not be called when status is not "uploading"
    expect(selectSpy).not.toHaveBeenCalled();
  });
});
