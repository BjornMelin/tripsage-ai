/** @vitest-environment node */

import type { NotifyJob } from "@schemas/webhooks";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createMockNextRequest, getMockCookiesForTest } from "@/test/route-helpers";

type ReceiverVerify = (args: {
  body: string;
  signature: string;
  url: string;
}) => Promise<boolean>;
type TryReserveKey = (key: string, ttlSeconds?: number) => Promise<boolean>;
type SendNotifications = (
  payload: NotifyJob["payload"],
  eventKey: string
) => Promise<{ emailed?: boolean; webhookPosted?: boolean }>;

type RouteModule = typeof import("../route");

// Mock next/headers cookies() BEFORE any imports that use it
vi.mock("next/headers", () => ({
  cookies: vi.fn(() =>
    Promise.resolve(getMockCookiesForTest({ "sb-access-token": "test-token" }))
  ),
}));

const envStore = vi.hoisted<Record<string, string | undefined>>(() => ({
  QSTASH_CURRENT_SIGNING_KEY: "current",
  QSTASH_NEXT_SIGNING_KEY: "next",
}));

const receiverVerifyMock = vi.hoisted(() => vi.fn<ReceiverVerify>());
const tryReserveKeyMock = vi.hoisted(() => vi.fn<TryReserveKey>(async () => true));
const sendNotificationsMock = vi.hoisted(() =>
  vi.fn<SendNotifications>(async () => ({ emailed: true, webhookPosted: false }))
);

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

vi.mock("@upstash/qstash", () => ({
  Receiver: class {
    verify = (args: Parameters<ReceiverVerify>[0]) => receiverVerifyMock(args);
  },
}));

vi.mock("@/lib/idempotency/redis", () => ({
  tryReserveKey: (key: string, ttl?: number) => tryReserveKeyMock(key, ttl),
}));

vi.mock("@/lib/notifications/collaborators", () => ({
  sendCollaboratorNotifications: (payload: NotifyJob["payload"], eventKey: string) =>
    sendNotificationsMock(payload, eventKey),
}));

// Mock route helpers
vi.mock("@/lib/next/route-helpers", async () => {
  const actual = await vi.importActual<typeof import("@/lib/next/route-helpers")>(
    "@/lib/next/route-helpers"
  );
  return {
    ...actual,
    withRequestSpan: vi.fn(async (_name, _attrs, fn) => {
      const span = {
        recordException: vi.fn(),
        setAttribute: vi.fn(),
      };
      try {
        return await fn(span);
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error("withRequestSpan error", error);
        throw error;
      }
    }),
  };
});

function makeRequest(
  body: NotifyJob | Record<string, unknown>,
  headers?: Record<string, string>
) {
  return createMockNextRequest({
    body,
    headers: {
      "Upstash-Signature": "sig",
      ...headers,
    },
    method: "POST",
    url: "http://localhost/api/jobs/notify-collaborators",
  });
}

const validJob: NotifyJob = {
  eventKey: "trip_collaborators:INSERT:1",
  payload: {
    occurredAt: "2025-11-13T03:00:00Z",
    oldRecord: null,
    record: { id: "abc", table: "trip_collaborators" } as Record<string, unknown>,
    table: "trip_collaborators",
    type: "INSERT",
  },
};

describe("POST /api/jobs/notify-collaborators", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    receiverVerifyMock.mockReset();
    tryReserveKeyMock.mockReset();
    sendNotificationsMock.mockReset();
    receiverVerifyMock.mockResolvedValue(true);
    tryReserveKeyMock.mockResolvedValue(true);
    envStore.QSTASH_CURRENT_SIGNING_KEY = "current";
    envStore.QSTASH_NEXT_SIGNING_KEY = "next";
  });

  const loadRoute = async (): Promise<RouteModule> => {
    return await import("../route");
  };

  it("returns 500 when signing keys are missing", async () => {
    envStore.QSTASH_CURRENT_SIGNING_KEY = undefined;
    const { POST } = await loadRoute();
    const res = await POST(makeRequest(validJob));
    expect(res.status).toBe(500);
    const json = await res.json();
    expect(json.error).toMatch(/not configured/i);
  });

  it("returns 401 when signature verification fails", async () => {
    receiverVerifyMock.mockResolvedValue(false);
    const { POST } = await loadRoute();
    const res = await POST(makeRequest(validJob));
    expect(res.status).toBe(401);
    expect(await res.json()).toEqual({ error: "invalid qstash signature" });
  });

  it("returns 400 on invalid job payload", async () => {
    const { POST } = await loadRoute();
    const res = await POST(makeRequest({}));
    expect(res.status).toBe(400);
    const json = await res.json();
    expect(json.error).toBe("invalid job payload");
  });

  it("marks duplicates when idempotency guard fails", async () => {
    tryReserveKeyMock.mockResolvedValue(false);
    const { POST } = await loadRoute();
    const res = await POST(makeRequest(validJob));
    const json = await res.json();
    expect(res.status).toBe(200);
    expect(json.duplicate).toBe(true);
    expect(sendNotificationsMock).not.toHaveBeenCalled();
  });

  it("succeeds when payload and signature are valid", async () => {
    const { POST } = await loadRoute();
    const res = await POST(makeRequest(validJob));
    const json = await res.json();
    expect(res.status).toBe(200);
    expect(json.ok).toBe(true);
    expect(sendNotificationsMock).toHaveBeenCalledWith(
      validJob.payload,
      validJob.eventKey
    );
  });
});
