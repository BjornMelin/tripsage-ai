/** @vitest-environment node */

import { afterEach, describe, expect, it, vi } from "vitest";

const RECEIVER_CTOR = vi.hoisted(() => vi.fn());
const EMIT_ALERT_ONCE = vi.hoisted(() => vi.fn());
const GET_ENV = vi.hoisted(() => vi.fn());
const GET_ENV_FALLBACK = vi.hoisted(() => vi.fn());

vi.mock("@upstash/qstash", () => ({
  Receiver: class Receiver {
    constructor(args: unknown) {
      RECEIVER_CTOR(args);
    }
  },
}));

vi.mock("@/lib/env/server", () => ({
  getServerEnvVar: (...args: unknown[]) => GET_ENV(...args),
  getServerEnvVarWithFallback: (...args: unknown[]) => GET_ENV_FALLBACK(...args),
}));

vi.mock("@/lib/telemetry/degraded-mode", () => ({
  emitOperationalAlertOncePerWindow: (...args: unknown[]) => EMIT_ALERT_ONCE(...args),
}));

const LOGGER_ERROR = vi.hoisted(() => vi.fn());

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: () => ({
    debug: vi.fn(),
    error: LOGGER_ERROR,
    info: vi.fn(),
    warn: vi.fn(),
  }),
}));

afterEach(() => {
  RECEIVER_CTOR.mockReset();
  EMIT_ALERT_ONCE.mockReset();
  GET_ENV.mockReset();
  GET_ENV_FALLBACK.mockReset();
  LOGGER_ERROR.mockReset();
});

describe("verifyQstashRequest", () => {
  it("does not log raw signature on verification errors", async () => {
    const { verifyQstashRequest } = await import("@/lib/qstash/receiver");

    const receiver = {
      verify: vi.fn(() => Promise.reject(new Error("boom"))),
    };

    const signature = "very-secret-signature";
    const req = new Request("https://example.com/api/jobs/test", {
      body: JSON.stringify({ ok: true }),
      headers: {
        "Content-Type": "application/json",
        "upstash-signature": signature,
      },
      method: "POST",
    });

    const result = await verifyQstashRequest(req, receiver as never);
    expect(result.ok).toBe(false);
    if (result.ok) throw new Error("Expected failure");
    expect(result.response.status).toBe(401);

    expect(LOGGER_ERROR).toHaveBeenCalledWith(
      "QStash signature verification failed",
      expect.not.objectContaining({ signature })
    );
  });

  it("returns 489 when payload exceeds maxBytes", async () => {
    const { verifyQstashRequest } = await import("@/lib/qstash/receiver");

    const receiver = {
      verify: vi.fn(() => Promise.resolve(true)),
    };

    const signature = "sig";
    const req = new Request("https://example.com/api/jobs/test", {
      body: "x".repeat(1024),
      headers: {
        "Content-Type": "application/json",
        "upstash-signature": signature,
      },
      method: "POST",
    });

    const result = await verifyQstashRequest(req, receiver as never, { maxBytes: 10 });
    expect(result.ok).toBe(false);
    if (result.ok) throw new Error("Expected failure");
    expect(result.reason).toBe("payload_too_large");
    expect(result.response.status).toBe(489);
    expect(result.response.headers.get("Upstash-NonRetryable-Error")).toBe("true");
    expect(receiver.verify).not.toHaveBeenCalled();
  });

  it("returns 489 when request body has already been read", async () => {
    const { verifyQstashRequest } = await import("@/lib/qstash/receiver");

    const receiver = {
      verify: vi.fn(() => Promise.resolve(true)),
    };

    const signature = "sig";
    const req = new Request("https://example.com/api/jobs/test", {
      body: JSON.stringify({ ok: true }),
      headers: {
        "Content-Type": "application/json",
        "upstash-signature": signature,
      },
      method: "POST",
    });

    // Consume the body once to force Request.bodyUsed=true.
    await req.text();

    const result = await verifyQstashRequest(req, receiver as never);
    expect(result.ok).toBe(false);
    if (result.ok) throw new Error("Expected failure");
    expect(result.reason).toBe("body_read_error");
    expect(result.response.status).toBe(489);
    expect(result.response.headers.get("Upstash-NonRetryable-Error")).toBe("true");
    expect(receiver.verify).not.toHaveBeenCalled();
  });
});

describe("getQstashReceiver", () => {
  it("throws when QSTASH_CURRENT_SIGNING_KEY is missing", async () => {
    GET_ENV.mockReturnValue("");
    GET_ENV_FALLBACK.mockReturnValue("");

    const { getQstashReceiver } = await import("@/lib/qstash/receiver");

    expect(() => getQstashReceiver()).toThrow(/QSTASH_CURRENT_SIGNING_KEY/);
    expect(RECEIVER_CTOR).not.toHaveBeenCalled();
  });

  it("emits a deduped alert when QSTASH_NEXT_SIGNING_KEY is missing", async () => {
    GET_ENV.mockReturnValue("current");
    GET_ENV_FALLBACK.mockReturnValue("");

    const { getQstashReceiver } = await import("@/lib/qstash/receiver");

    getQstashReceiver();

    expect(EMIT_ALERT_ONCE).toHaveBeenCalledWith({
      attributes: expect.objectContaining({
        "alert.category": "config_drift",
        "config.current_key_set": true,
        "config.next_key_set": false,
        "docs.rotation_url": "https://upstash.com/docs/qstash/howto/roll-signing-keys",
        "docs.url": "https://upstash.com/docs/qstash/howto/signature",
      }),
      event: "qstash.next_signing_key_missing",
      severity: "warning",
      windowMs: 6 * 60 * 60 * 1000,
    });

    expect(RECEIVER_CTOR).toHaveBeenCalledWith({
      currentSigningKey: "current",
      nextSigningKey: "current",
    });
  });

  it("does not emit a key-rotation alert when QSTASH_NEXT_SIGNING_KEY is present", async () => {
    GET_ENV.mockReturnValue("current");
    GET_ENV_FALLBACK.mockReturnValue("next");

    const { getQstashReceiver } = await import("@/lib/qstash/receiver");

    getQstashReceiver();

    expect(EMIT_ALERT_ONCE).not.toHaveBeenCalled();
    expect(RECEIVER_CTOR).toHaveBeenCalledWith({
      currentSigningKey: "current",
      nextSigningKey: "next",
    });
  });
});
