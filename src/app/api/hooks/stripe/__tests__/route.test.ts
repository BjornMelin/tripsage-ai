/** @vitest-environment node */

import Stripe from "stripe";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { RateLimitResult } from "@/lib/webhooks/rate-limit";
import { createMockNextRequest } from "@/test/helpers/route";

type StripeRouteModule = typeof import("../route");

vi.mock("server-only", () => ({}));

const WEBHOOK_SECRET = "whsec_test_webhook_secret";
const stripe = new Stripe("sk_test_123", { typescript: true });
const MAX_WEBHOOK_BYTES = 256 * 1024;

type ReserveKeyOptions = {
  degradedMode?: "fail_closed" | "fail_open";
  failOpen?: boolean;
  ttlSeconds?: number;
};

type TryReserveKey = (
  key: string,
  ttlSecondsOrOptions?: number | ReserveKeyOptions
) => Promise<boolean>;

type ReleaseKey = (
  key: string,
  options?: Pick<ReserveKeyOptions, "degradedMode" | "failOpen">
) => Promise<boolean>;

const tryReserveKeyMock = vi.hoisted(() => vi.fn<TryReserveKey>(async () => true));
const releaseKeyMock = vi.hoisted(() => vi.fn<ReleaseKey>(async () => true));

vi.mock("@/lib/idempotency/redis", () => ({
  IdempotencyServiceUnavailableError: class IdempotencyServiceUnavailableError extends Error {
    constructor() {
      super("Idempotency service unavailable: Redis not configured");
      this.name = "IdempotencyServiceUnavailableError";
    }
  },
  releaseKey: releaseKeyMock,
  tryReserveKey: tryReserveKeyMock,
}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: (key: string) => {
    if (key === "STRIPE_WEBHOOK_SECRET") return WEBHOOK_SECRET;
    throw new Error(`Unexpected env var access in test: ${key}`);
  },
}));

vi.mock("@/lib/payments/stripe-client", () => ({
  getStripeClient: () => stripe,
}));

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: (
    _name: string,
    _opts: unknown,
    fn: (
      span: { addEvent: (name: string, attrs: Record<string, unknown>) => void } & {
        recordException: (err: unknown) => void;
        setAttribute: (key: string, value: unknown) => void;
      }
    ) => unknown
  ) =>
    fn({
      addEvent: vi.fn(),
      recordException: vi.fn(),
      setAttribute: vi.fn(),
    }),
}));

const checkWebhookRateLimitMock = vi.hoisted(() =>
  vi.fn<() => Promise<RateLimitResult>>(async () => ({ success: true }))
);
const createRateLimitHeadersMock = vi.hoisted(() => vi.fn(() => ({})));

vi.mock("@/lib/webhooks/rate-limit", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/lib/webhooks/rate-limit")>();
  return {
    ...original,
    checkWebhookRateLimit: checkWebhookRateLimitMock,
    createRateLimitHeaders: createRateLimitHeadersMock,
  };
});

function makeRequest(body: string, headers: Record<string, string> = {}) {
  return createMockNextRequest({
    body,
    headers: {
      "content-type": "application/json",
      ...headers,
    },
    method: "POST",
    url: "http://localhost/api/hooks/stripe",
  });
}

function makeEventPayload(type: string) {
  return {
    api_version: "2024-06-20",
    created: 1_600_000_000,
    data: {
      object: {
        id: "pi_test_123",
        object: "payment_intent",
        status: "succeeded",
      },
    },
    id: "evt_test_123",
    livemode: false,
    object: "event",
    pending_webhooks: 1,
    request: {
      id: null,
      idempotency_key: null,
    },
    type,
  } as const;
}

async function loadRoute(): Promise<StripeRouteModule> {
  return await import("../route");
}

describe("POST /api/hooks/stripe", () => {
  let dateNowSpy: ReturnType<typeof vi.spyOn> | null = null;

  beforeEach(() => {
    vi.clearAllMocks();
    tryReserveKeyMock.mockReset();
    releaseKeyMock.mockReset();
    tryReserveKeyMock.mockResolvedValue(true);
    releaseKeyMock.mockResolvedValue(true);

    // Stripe webhook signature verification validates the timestamp. Fix Date.now()
    // so generated test headers and verification both use the same "current" time.
    dateNowSpy = vi.spyOn(Date, "now").mockReturnValue(1_700_000_000_000);
  });

  afterEach(() => {
    dateNowSpy?.mockRestore();
    dateNowSpy = null;
  });

  it("returns 401 when stripe-signature header is missing", async () => {
    const { POST } = await loadRoute();
    const res = await POST(
      makeRequest(JSON.stringify(makeEventPayload("payment_intent.succeeded")))
    );
    expect(res.status).toBe(401);
    const json = await res.json();
    expect(json.error).toBe("missing_signature");
  });

  it("returns 401 when signature verification fails", async () => {
    const payload = JSON.stringify(makeEventPayload("payment_intent.succeeded"));
    const badHeader = stripe.webhooks.generateTestHeaderString({
      payload,
      secret: "whsec_wrong_secret",
    });

    const { POST } = await loadRoute();
    const res = await POST(makeRequest(payload, { "stripe-signature": badHeader }));
    expect(res.status).toBe(401);
    const json = await res.json();
    expect(json.error).toBe("invalid_signature");
  });

  it("returns 429 when rate limit is exceeded", async () => {
    checkWebhookRateLimitMock.mockResolvedValueOnce({
      reason: "rate_limited",
      success: false,
    });

    const payload = JSON.stringify(makeEventPayload("payment_intent.succeeded"));
    const header = stripe.webhooks.generateTestHeaderString({
      payload,
      secret: WEBHOOK_SECRET,
    });

    const { POST } = await loadRoute();
    const res = await POST(makeRequest(payload, { "stripe-signature": header }));
    expect(res.status).toBe(429);
    const json = await res.json();
    expect(json.error).toBe("rate_limit_exceeded");
  });

  it("returns 413 when request body exceeds size limit", async () => {
    const payload = JSON.stringify(makeEventPayload("payment_intent.succeeded"));
    const header = stripe.webhooks.generateTestHeaderString({
      payload,
      secret: WEBHOOK_SECRET,
    });

    const { POST } = await loadRoute();
    const res = await POST(
      makeRequest(payload, {
        "content-length": String(MAX_WEBHOOK_BYTES + 1),
        "stripe-signature": header,
      })
    );
    expect(res.status).toBe(413);
    const json = await res.json();
    expect(json.error).toBe("payload_too_large");
  });

  it("returns 200 and acknowledges valid events", async () => {
    const payload = JSON.stringify(makeEventPayload("payment_intent.succeeded"));
    const header = stripe.webhooks.generateTestHeaderString({
      payload,
      secret: WEBHOOK_SECRET,
    });

    const { POST } = await loadRoute();
    const res = await POST(makeRequest(payload, { "stripe-signature": header }));
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.received).toBe(true);
    expect(json.type).toBe("payment_intent.succeeded");
  });

  it("returns 200 and marks duplicates when idempotency key already exists", async () => {
    tryReserveKeyMock.mockResolvedValue(false);

    const payload = JSON.stringify(makeEventPayload("payment_intent.succeeded"));
    const header = stripe.webhooks.generateTestHeaderString({
      payload,
      secret: WEBHOOK_SECRET,
    });

    const { POST } = await loadRoute();
    const res = await POST(makeRequest(payload, { "stripe-signature": header }));
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.duplicate).toBe(true);
  });

  it("acknowledges v2.* event notification types safely", async () => {
    const payload = JSON.stringify(makeEventPayload("v2.core.account.updated"));
    const header = stripe.webhooks.generateTestHeaderString({
      payload,
      secret: WEBHOOK_SECRET,
    });

    const { POST } = await loadRoute();
    const res = await POST(makeRequest(payload, { "stripe-signature": header }));
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.ok).toBe(true);
    expect(json.type).toBe("v2.core.account.updated");
  });
});
