/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import type { WebhookPayload } from "@/lib/webhooks/payload";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/helpers/route";

type ParseAndVerify = (req: Request) => Promise<ParseResult>;
type BuildEventKey = (payload: WebhookPayload) => string;
type TryReserveKey = (key: string, ttlSeconds?: number) => Promise<boolean>;
type SendNotifications = (
  payload: WebhookPayload,
  eventKey: string
) => Promise<{ emailed?: boolean; webhookPosted?: boolean }>;

type ParseResult = { ok: boolean; payload?: WebhookPayload };
type TripsRouteModule = typeof import("../route");

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

const parseAndVerifyMock = vi.hoisted(() => vi.fn<ParseAndVerify>());
const buildEventKeyMock = vi.hoisted(() => vi.fn<BuildEventKey>(() => "event-key-1"));
const tryReserveKeyMock = vi.hoisted(() => vi.fn<TryReserveKey>(async () => true));
const sendCollaboratorNotificationsMock = vi.hoisted(() =>
  vi.fn<SendNotifications>(async () => ({ emailed: true, webhookPosted: false }))
);
const envStore = vi.hoisted<Record<string, string | undefined>>(() => ({
  NEXT_PUBLIC_SITE_URL: "http://localhost:3000",
  NEXT_PUBLIC_SUPABASE_URL: "https://supabase.test",
  QSTASH_TOKEN: "qstash-token",
  SUPABASE_SERVICE_ROLE_KEY: "service-role",
}));
const afterCallbacks = vi.hoisted<Array<() => unknown>>(() => []);

function createSupabaseStub() {
  const limit = vi.fn(async () => ({ error: null }));
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

vi.mock("@/lib/notifications/collaborators", () => ({
  sendCollaboratorNotifications: (payload: WebhookPayload, eventKey: string) =>
    sendCollaboratorNotificationsMock(payload, eventKey),
}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: (key: string) => {
    const value = (envStore as Record<string, string | undefined>)[key];
    if (!value) {
      throw new Error(`Missing env ${key}`);
    }
    return value;
  },
  getServerEnvVarWithFallback: (key: string, fallback?: string) => {
    const value = (envStore as Record<string, string | undefined>)[key];
    return (value ?? fallback) as string;
  },
}));

vi.mock("@supabase/supabase-js", () => ({
  createClient: vi.fn(() => supabaseFactory()),
}));

// Mock QStash client for enqueue testing
type TryEnqueueJobResult =
  | { messageId: string; success: true }
  | { error: Error | null; success: false };
type TryEnqueueJob = (
  jobType: string,
  payload: unknown,
  path: string
) => Promise<TryEnqueueJobResult>;

const tryEnqueueJobMock = vi.hoisted(() =>
  vi.fn<TryEnqueueJob>(async () => ({ messageId: "msg_test", success: true }))
);

vi.mock("@/lib/qstash/client", () => ({
  tryEnqueueJob: (jobType: string, payload: unknown, path: string) =>
    tryEnqueueJobMock(jobType, payload, path),
}));

vi.mock("next/server", async () => {
  const actual = (await vi.importActual("next/server")) as Record<string, unknown>;
  return {
    ...actual,
    after: (callback: () => unknown) => {
      afterCallbacks.push(callback);
    },
  };
});

// Mock route helpers
vi.mock("@/lib/api/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/route-helpers")>(
    "@/lib/api/route-helpers"
  );
  return {
    ...actual,
    withRequestSpan: vi.fn((_name, _attrs, fn) => fn()),
  };
});

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

function makeRequest(body: unknown, headers: Record<string, string> = {}) {
  return createMockNextRequest({
    body,
    headers,
    method: "POST",
    url: "http://localhost/api/hooks/trips",
  });
}

describe("POST /api/hooks/trips", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    parseAndVerifyMock.mockReset();
    buildEventKeyMock.mockReset();
    buildEventKeyMock.mockReturnValue("event-key-1");
    tryReserveKeyMock.mockReset();
    sendCollaboratorNotificationsMock.mockReset();
    tryEnqueueJobMock.mockReset();
    tryEnqueueJobMock.mockResolvedValue({ messageId: "msg_test", success: true });
    afterCallbacks.length = 0;
    envStore.NEXT_PUBLIC_SUPABASE_URL = "https://supabase.test";
    envStore.SUPABASE_SERVICE_ROLE_KEY = "service-role";
    envStore.QSTASH_TOKEN = "qstash-token";
    supabaseFactory = () => createSupabaseStub();
  });

  const loadRoute = async (): Promise<TripsRouteModule> => {
    return await import("../route");
  };

  it("returns 401 when signature or payload is invalid", async () => {
    parseAndVerifyMock.mockResolvedValue({ ok: false });
    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    expect(res.status).toBe(401);
  });

  it("skips non-trip_collaborators tables", async () => {
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
        record: { id: "1", trip_id: 42 },
        table: "trip_collaborators",
        type: "INSERT",
      },
    });
    tryReserveKeyMock.mockResolvedValue(false);
    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    const json = await res.json();
    expect(res.status).toBe(200);
    expect(json.duplicate).toBe(true);
    expect(tryReserveKeyMock).toHaveBeenCalledWith("event-key-1", 300);
  });

  it("enqueues to QStash when configured", async () => {
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: { id: "1", trip_id: 99 },
        table: "trip_collaborators",
        type: "INSERT",
      },
    });
    tryReserveKeyMock.mockResolvedValue(true);

    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}, { host: "localhost:3000" }));
    const json = await res.json();
    expect(res.status).toBe(200);
    expect(json.enqueued).toBe(true);
    // tryEnqueueJob is called with job type, payload, and path
    expect(tryEnqueueJobMock).toHaveBeenCalledWith(
      "notify-collaborators",
      { eventKey: "event-key-1", payload: expect.any(Object) },
      "/api/jobs/notify-collaborators"
    );
  });

  it("uses after() fallback when QStash is not configured", async () => {
    // Mock tryEnqueueJob to return failure (simulates QStash unavailable)
    tryEnqueueJobMock.mockResolvedValue({ error: null, success: false });
    parseAndVerifyMock.mockResolvedValue({
      ok: true,
      payload: {
        oldRecord: null,
        record: { id: "1", trip_id: 77 },
        table: "trip_collaborators",
        type: "INSERT",
      },
    });
    tryReserveKeyMock.mockResolvedValue(true);
    sendCollaboratorNotificationsMock.mockResolvedValue({
      emailed: true,
      webhookPosted: false,
    });

    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    const json = await res.json();
    expect(res.status).toBe(200);
    expect(json.fallback).toBe(true);
    expect(afterCallbacks.length).toBe(1);
    expect(sendCollaboratorNotificationsMock).not.toHaveBeenCalled();
    await afterCallbacks[0]?.();
    expect(sendCollaboratorNotificationsMock).toHaveBeenCalledWith(
      expect.objectContaining({ table: "trip_collaborators" }),
      "event-key-1"
    );
  });
});
