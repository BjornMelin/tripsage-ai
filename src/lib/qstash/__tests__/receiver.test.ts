/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";

const LOGGER_ERROR = vi.hoisted(() => vi.fn());

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: () => ({
    debug: vi.fn(),
    error: LOGGER_ERROR,
    info: vi.fn(),
    warn: vi.fn(),
  }),
}));

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

  it("returns 413 when payload exceeds maxBytes", async () => {
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
    expect(result.response.status).toBe(413);
    expect(receiver.verify).not.toHaveBeenCalled();
  });

  it("returns 400 when request body has already been read", async () => {
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
    expect(result.response.status).toBe(400);
    expect(receiver.verify).not.toHaveBeenCalled();
  });
});
