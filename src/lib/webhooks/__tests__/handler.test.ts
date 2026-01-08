/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  WebhookConflictError,
  WebhookDuplicateError,
  WebhookRateLimitedError,
  WebhookTimeoutError,
  WebhookUnauthorizedError,
  WebhookUpstreamError,
  WebhookValidationError,
} from "../errors";
import { createWebhookHandler } from "../handler";

type ParseAndVerifyResult =
  | {
      ok: true;
      payload: {
        occurredAt: string;
        oldRecord: null;
        record: { id: string };
        schema: string;
        table: string;
        type: string;
      };
    }
  | { ok: false; reason: string };

type ParseAndVerify = (
  req: Request,
  options?: { maxBytes?: number }
) => Promise<ParseAndVerifyResult>;

const parseAndVerifyMock = vi.hoisted(() =>
  vi.fn<ParseAndVerify>(async () => ({
    ok: true,
    payload: {
      occurredAt: "2025-12-10T12:00:00.000Z",
      oldRecord: null,
      record: { id: "rec-1" },
      schema: "public",
      table: "test_table",
      type: "INSERT",
    },
  }))
);

const buildEventKeyMock = vi.hoisted(() => vi.fn(() => "event-key"));
const tryReserveKeyMock = vi.hoisted(() => vi.fn(async () => true));
const releaseKeyMock = vi.hoisted(() =>
  vi.fn(async (_key: string, _opts?: unknown) => true)
);
const checkRateLimitMock = vi.hoisted(() => vi.fn(async () => ({ success: true })));
const spanAttributes = vi.hoisted(() => [] as Array<[string, unknown]>);

vi.mock("../payload", () => ({
  buildEventKey: buildEventKeyMock,
  parseAndVerify: parseAndVerifyMock,
}));

vi.mock("@/lib/idempotency/redis", () => ({
  IdempotencyServiceUnavailableError: class IdempotencyServiceUnavailableError extends Error {
    constructor() {
      super("Idempotency service unavailable: Redis not configured");
      this.name = "IdempotencyServiceUnavailableError";
    }
  },
  releaseKey: (key: string, opts?: unknown) => releaseKeyMock(key, opts),
  tryReserveKey: tryReserveKeyMock,
}));

vi.mock("../rate-limit", async (importOriginal) => {
  const original = await importOriginal<typeof import("../rate-limit")>();
  return {
    ...original,
    checkWebhookRateLimit: checkRateLimitMock,
    createRateLimitHeaders: () => ({}),
  };
});

vi.mock("@/lib/telemetry/span", () => ({
  withTelemetrySpan: async (
    _name: string,
    _opts: unknown,
    fn: (span: {
      setAttribute: (k: string, v: unknown) => void;
      recordException: () => void;
    }) => unknown
  ) =>
    fn({
      recordException: vi.fn(),
      setAttribute: (k: string, v: unknown) => {
        spanAttributes.push([k, v]);
      },
    }),
}));

describe("createWebhookHandler", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    spanAttributes.length = 0;
  });

  it("returns 413 when payload is too large (bounded body read)", async () => {
    parseAndVerifyMock.mockResolvedValueOnce({
      ok: false,
      reason: "payload_too_large",
    });

    const handler = createWebhookHandler({
      handle: async () => ({}),
      maxBodySize: 10,
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));

    expect(parseAndVerifyMock).toHaveBeenCalledWith(expect.anything(), {
      maxBytes: 10,
    });
    expect(res.status).toBe(413);
    expect(await res.json()).toEqual({
      code: "VALIDATION_ERROR",
      error: "payload_too_large",
    });
  });

  it("returns 401 when signature verification fails", async () => {
    parseAndVerifyMock.mockResolvedValueOnce({
      ok: false,
      reason: "invalid_signature",
    });

    const handler = createWebhookHandler({
      handle: async () => ({}),
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));

    expect(res.status).toBe(401);
    expect(await res.json()).toEqual({
      code: "UNAUTHORIZED",
      error: "invalid_signature",
    });
  });

  it("returns 400 when JSON parsing fails", async () => {
    parseAndVerifyMock.mockResolvedValueOnce({
      ok: false,
      reason: "invalid_json",
    });

    const handler = createWebhookHandler({
      handle: async () => ({}),
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));

    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({
      code: "VALIDATION_ERROR",
      error: "invalid_request",
    });
  });

  it("returns 400 when payload shape validation fails", async () => {
    parseAndVerifyMock.mockResolvedValueOnce({
      ok: false,
      reason: "invalid_payload_shape",
    });

    const handler = createWebhookHandler({
      handle: async () => ({}),
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));

    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({
      code: "VALIDATION_ERROR",
      error: "invalid_request",
    });
  });

  it("returns 503 when verification fails due to missing secret", async () => {
    parseAndVerifyMock.mockResolvedValueOnce({
      ok: false,
      reason: "missing_secret_env",
    });

    const handler = createWebhookHandler({
      handle: async () => ({}),
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));

    expect(res.status).toBe(503);
    expect(await res.json()).toEqual({
      code: "SERVICE_UNAVAILABLE",
      error: "internal_error",
    });
  });

  it("returns 503 when verification fails due to body read errors", async () => {
    parseAndVerifyMock.mockResolvedValueOnce({
      ok: false,
      reason: "body_read_error",
    });

    const handler = createWebhookHandler({
      handle: async () => ({}),
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));

    expect(res.status).toBe(503);
    expect(await res.json()).toEqual({
      code: "SERVICE_UNAVAILABLE",
      error: "internal_error",
    });
  });

  it("returns generic message for validation errors", async () => {
    const handler = createWebhookHandler({
      handle() {
        throw new WebhookValidationError();
      },
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));
    const body = (await res.json()) as Record<string, unknown>;

    expect(res.status).toBe(400);
    expect(body).toEqual({ code: "VALIDATION_ERROR", error: "invalid_request" });
    expect(spanAttributes.some(([k]) => k === "webhook.error_message")).toBe(true);
  });

  it("maps typed webhook errors to explicit status codes", async () => {
    const handler = createWebhookHandler({
      handle() {
        throw new WebhookConflictError();
      },
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));
    expect(res.status).toBe(409);
    expect(await res.json()).toEqual({ code: "CONFLICT", error: "conflict" });
  });

  it("returns 200 + duplicate payload for duplicate errors", async () => {
    const handler = createWebhookHandler({
      handle() {
        throw new WebhookDuplicateError();
      },
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ duplicate: true, ok: true });
  });

  it("returns Retry-After for rate limited errors", async () => {
    const handler = createWebhookHandler({
      handle() {
        throw new WebhookRateLimitedError("rate_limit_exceeded", {
          retryAfterSeconds: 60,
        });
      },
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));
    expect(res.status).toBe(429);
    expect(res.headers.get("Retry-After")).toBe("60");
    expect(await res.json()).toEqual({
      code: "RATE_LIMITED",
      error: "rate_limit_exceeded",
    });
  });

  it("returns 401 for unauthorized errors", async () => {
    const handler = createWebhookHandler({
      handle() {
        throw new WebhookUnauthorizedError();
      },
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));
    expect(res.status).toBe(401);
    expect(await res.json()).toEqual({ code: "UNAUTHORIZED", error: "unauthorized" });
  });

  it("returns 504 for timeout errors", async () => {
    const handler = createWebhookHandler({
      handle() {
        throw new WebhookTimeoutError();
      },
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));
    expect(res.status).toBe(504);
    expect(await res.json()).toEqual({ code: "TIMEOUT", error: "internal_error" });
  });

  it("returns 502 for upstream errors", async () => {
    const handler = createWebhookHandler({
      handle() {
        throw new WebhookUpstreamError();
      },
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));
    expect(res.status).toBe(502);
    expect(await res.json()).toEqual({
      code: "UPSTREAM_ERROR",
      error: "internal_error",
    });
  });

  it("maps idempotency unavailability to 503", async () => {
    const { IdempotencyServiceUnavailableError } = await import(
      "@/lib/idempotency/redis"
    );

    tryReserveKeyMock.mockRejectedValueOnce(new IdempotencyServiceUnavailableError());

    const handler = createWebhookHandler({
      handle: async () => ({}),
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));
    expect(res.status).toBe(503);
    expect(await res.json()).toEqual({
      code: "SERVICE_UNAVAILABLE",
      error: "internal_error",
    });
  });

  it("masks unexpected errors as internal_error", async () => {
    const handler = createWebhookHandler({
      handle() {
        throw new Error("boom");
      },
      name: "test",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));
    const body = (await res.json()) as Record<string, unknown>;

    expect(res.status).toBe(500);
    expect(body).toEqual({ code: "UNKNOWN", error: "internal_error" });
    const recorded = spanAttributes.find(([k]) => k === "webhook.error_message");
    expect(recorded?.[1]).toBe("boom");
  });

  it("reserves idempotency key even when table is filtered out", async () => {
    const handler = createWebhookHandler({
      handle: async () => ({}),
      name: "test",
      tableFilter: "other_table",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));
    const body = (await res.json()) as Record<string, unknown>;

    expect(body).toEqual({ ok: true, skipped: true });
    expect(tryReserveKeyMock).toHaveBeenCalledWith("event-key", {
      degradedMode: "fail_closed",
      ttlSeconds: 300,
    });
    const scope = spanAttributes.find(([k]) => k === "webhook.idempotency_scope");
    expect(scope?.[1]).toBe("global");
    const skipped = spanAttributes.find(([k]) => k === "webhook.skipped");
    expect(skipped?.[1]).toBe(true);
  });

  it("returns duplicate when idempotency key already exists even if table mismatches", async () => {
    tryReserveKeyMock.mockResolvedValueOnce(false);

    const handler = createWebhookHandler({
      handle: async () => ({}),
      name: "test",
      tableFilter: "other_table",
    });

    const res = await handler(new NextRequest("https://example.com/api/hooks/test"));
    const body = (await res.json()) as Record<string, unknown>;

    expect(body).toEqual({ duplicate: true, ok: true });
    expect(spanAttributes.find(([k]) => k === "webhook.duplicate")?.[1]).toBe(true);
    // Table filter should not run after duplicate short-circuit
    const skipped = spanAttributes.find(([k]) => k === "webhook.skipped");
    expect(skipped).toBeUndefined();
  });
});
