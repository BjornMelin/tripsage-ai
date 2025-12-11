/** @vitest-environment node */

import { createHmac } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { WebhookPayload } from "@/lib/webhooks/payload";

const GET_ENV = vi.hoisted(() => vi.fn());
const EMIT_ALERT = vi.hoisted(() => vi.fn());

vi.mock("@/lib/env/server", () => ({
  getServerEnvVarWithFallback: (...args: Parameters<typeof GET_ENV>) =>
    GET_ENV(...args),
}));

vi.mock("@/lib/telemetry/alerts", () => ({
  emitOperationalAlert: (...args: Parameters<typeof EMIT_ALERT>) => EMIT_ALERT(...args),
}));

vi.mock("@opentelemetry/api", () => ({
  SpanStatusCode: { ERROR: 2, OK: 1 },
  trace: {
    getActiveSpan: () => ({
      addEvent: vi.fn(),
      end: vi.fn(),
      recordException: vi.fn(),
      setStatus: vi.fn(),
    }),
    getTracer: () => ({
      startActiveSpan: (
        _name: string,
        maybeOptions: unknown,
        maybeCb?: (span: unknown) => unknown
      ) => {
        const cb = typeof maybeOptions === "function" ? maybeOptions : maybeCb;
        const span = {
          addEvent: vi.fn(),
          end: vi.fn(),
          recordException: vi.fn(),
          setStatus: vi.fn(),
        };
        return cb ? cb(span) : undefined;
      },
    }),
  },
}));

const { buildEventKey, parseAndVerify } = await import("@/lib/webhooks/payload");

/** Helper to compute HMAC signature for test requests */
function computeSignature(body: string, secret: string): string {
  return createHmac("sha256", Buffer.from(secret, "utf8"))
    .update(body, "utf8")
    .digest("hex");
}

describe("buildEventKey", () => {
  it("includes table, type, and occurredAt", () => {
    const p: WebhookPayload = {
      occurredAt: "2025-11-13T03:00:00Z",
      oldRecord: null,
      record: { id: "abc" },
      table: "trip_collaborators",
      type: "INSERT",
    };
    const key = buildEventKey(p);
    expect(key).toContain("trip_collaborators:INSERT:2025-11-13T03:00:00Z");
    expect(key).toContain(":abc");
  });

  it("hashes record when id missing", () => {
    const p: WebhookPayload = {
      occurredAt: "2025-11-13T03:00:00Z",
      oldRecord: null,
      record: { name: "foo" },
      table: "trips",
      type: "UPDATE",
    };
    const key = buildEventKey(p);
    expect(key).toMatch(/trips:UPDATE:2025-11-13T03:00:00Z:[0-9a-f]{16}$/);
  });
});

describe("parseAndVerify", () => {
  const TestSecret = "test-webhook-secret";

  beforeEach(() => {
    vi.clearAllMocks();
    GET_ENV.mockReturnValue(TestSecret);
  });

  it("fails when secret missing and emits alert", async () => {
    GET_ENV.mockReturnValueOnce("");
    const body = JSON.stringify({ record: {}, table: "trips", type: "INSERT" });
    const req = new Request("https://example.com/api/hooks/trips", {
      body,
      headers: {
        "Content-Type": "application/json",
        "x-signature-hmac": computeSignature(body, TestSecret),
      },
      method: "POST",
    });
    const result = await parseAndVerify(req);
    expect(result.ok).toBe(false);
    expect(EMIT_ALERT).toHaveBeenCalledWith("webhook.verification_failed", {
      attributes: { reason: "missing_secret_env" },
    });
  });

  it("fails when signature header missing", async () => {
    const req = new Request("https://example.com/api/hooks/trips", {
      body: JSON.stringify({ record: {}, table: "trips", type: "INSERT" }),
      headers: { "Content-Type": "application/json" },
      method: "POST",
    });
    const result = await parseAndVerify(req);
    expect(result.ok).toBe(false);
    expect(EMIT_ALERT).toHaveBeenCalledWith("webhook.verification_failed", {
      attributes: { reason: "missing_signature" },
    });
  });

  it("fails when signature invalid", async () => {
    const req = new Request("https://example.com/api/hooks/trips", {
      body: JSON.stringify({ record: {}, table: "trips", type: "INSERT" }),
      headers: {
        "Content-Type": "application/json",
        "x-signature-hmac": "invalid-signature",
      },
      method: "POST",
    });
    const result = await parseAndVerify(req);
    expect(result.ok).toBe(false);
    expect(EMIT_ALERT).toHaveBeenCalledWith("webhook.verification_failed", {
      attributes: { reason: "invalid_signature" },
    });
  });

  it("fails when JSON invalid", async () => {
    const body = "not-json";
    const req = new Request("https://example.com/api/hooks/trips", {
      body,
      headers: {
        "Content-Type": "application/json",
        "x-signature-hmac": computeSignature(body, TestSecret),
      },
      method: "POST",
    });
    const result = await parseAndVerify(req);
    expect(result.ok).toBe(false);
    expect(EMIT_ALERT).toHaveBeenCalledWith("webhook.verification_failed", {
      attributes: { reason: "invalid_json" },
    });
  });

  it("fails when payload shape invalid", async () => {
    const body = JSON.stringify({ record: {}, table: "", type: "INSERT" });
    const req = new Request("https://example.com/api/hooks/trips", {
      body,
      headers: {
        "Content-Type": "application/json",
        "x-signature-hmac": computeSignature(body, TestSecret),
      },
      method: "POST",
    });
    const result = await parseAndVerify(req);
    expect(result.ok).toBe(false);
    expect(EMIT_ALERT).toHaveBeenCalledWith("webhook.verification_failed", {
      attributes: { reason: "invalid_payload_shape" },
    });
  });

  it("returns payload when verification succeeds", async () => {
    const body = JSON.stringify({
      occurred_at: "2025-11-13T03:00:00Z",
      old_record: null,
      record: { id: "abc123" },
      table: "trip_collaborators",
      type: "UPDATE",
    });
    const req = new Request("https://example.com/api/hooks/trips", {
      body,
      headers: {
        "Content-Type": "application/json",
        "x-signature-hmac": computeSignature(body, TestSecret),
      },
      method: "POST",
    });
    const result = await parseAndVerify(req);
    expect(result.ok).toBe(true);
    expect(result.payload).toMatchObject({
      occurredAt: "2025-11-13T03:00:00Z",
      record: { id: "abc123" },
      table: "trip_collaborators",
      type: "UPDATE",
    });
    expect(EMIT_ALERT).not.toHaveBeenCalled();
  });
});
