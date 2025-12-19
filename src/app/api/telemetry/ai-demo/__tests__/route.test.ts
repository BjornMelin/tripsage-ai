/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  setRateLimitFactoryForTests,
  setSupabaseFactoryForTests,
} from "@/lib/api/factory";
import { __resetServerEnvCacheForTest } from "@/lib/env/server";
import { createMockNextRequest, createRouteParamsContext } from "@/test/helpers/route";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

const EMIT_ALERT = vi.hoisted(() => vi.fn());

vi.mock("@/lib/telemetry/alerts", () => ({
  emitOperationalAlert: (...args: Parameters<typeof EMIT_ALERT>) => EMIT_ALERT(...args),
}));

import { POST } from "@/app/api/telemetry/ai-demo/route";

describe("/api/telemetry/ai-demo", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubEnv("ENABLE_AI_DEMO", "true");
    vi.stubEnv("TELEMETRY_AI_DEMO_KEY", "test-telemetry-ai-demo-key-1234567890");
    vi.stubEnv("TELEMETRY_HASH_SECRET", "test-telemetry-hash-secret-1234567890");
    __resetServerEnvCacheForTest();

    setSupabaseFactoryForTests(async () => unsafeCast({}));
    setRateLimitFactoryForTests(async () => ({
      limit: 10,
      remaining: 9,
      reset: Date.now() + 60_000,
      success: true,
    }));
  });

  afterEach(() => {
    setRateLimitFactoryForTests(null);
    setSupabaseFactoryForTests(null);
    vi.unstubAllEnvs();
    __resetServerEnvCacheForTest();
  });

  it("returns 404 when demo is disabled", async () => {
    vi.stubEnv("ENABLE_AI_DEMO", "");
    __resetServerEnvCacheForTest();

    const res = await POST(
      createMockNextRequest({
        body: { status: "success" },
        headers: { "x-internal-key": "test-telemetry-ai-demo-key-1234567890" },
        method: "POST",
        url: "http://localhost/api/telemetry/ai-demo",
      }),
      createRouteParamsContext()
    );

    expect(res.status).toBe(404);
    expect(EMIT_ALERT).not.toHaveBeenCalled();
  });

  it("returns 404 when TELEMETRY_AI_DEMO_KEY is missing (security: consistent 404)", async () => {
    vi.stubEnv("TELEMETRY_AI_DEMO_KEY", "");
    __resetServerEnvCacheForTest();

    const res = await POST(
      createMockNextRequest({
        body: { status: "success" },
        method: "POST",
        url: "http://localhost/api/telemetry/ai-demo",
      }),
      createRouteParamsContext()
    );

    // Returns 404 to avoid leaking whether endpoint exists but is misconfigured vs disabled
    expect(res.status).toBe(404);
    expect(EMIT_ALERT).not.toHaveBeenCalled();
  });

  it("returns 401 when internal key is missing/invalid", async () => {
    const res = await POST(
      createMockNextRequest({
        body: { status: "success" },
        method: "POST",
        url: "http://localhost/api/telemetry/ai-demo",
      }),
      createRouteParamsContext()
    );

    expect(res.status).toBe(401);
    expect(EMIT_ALERT).not.toHaveBeenCalled();
  });

  it("returns 400 when detail exceeds cap", async () => {
    const res = await POST(
      createMockNextRequest({
        body: { detail: "a".repeat(2001), status: "error" },
        headers: { "x-internal-key": "test-telemetry-ai-demo-key-1234567890" },
        method: "POST",
        url: "http://localhost/api/telemetry/ai-demo",
      }),
      createRouteParamsContext()
    );

    expect(res.status).toBe(400);
    expect(EMIT_ALERT).not.toHaveBeenCalled();
  });

  it("returns 413 when body exceeds MAX_BODY_BYTES", async () => {
    const res = await POST(
      createMockNextRequest({
        body: { detail: "a".repeat(16 * 1024), status: "error" },
        headers: { "x-internal-key": "test-telemetry-ai-demo-key-1234567890" },
        method: "POST",
        url: "http://localhost/api/telemetry/ai-demo",
      }),
      createRouteParamsContext()
    );

    expect(res.status).toBe(413);
    expect(EMIT_ALERT).not.toHaveBeenCalled();
  });

  it("fails closed when rate limiting infrastructure is degraded", async () => {
    setRateLimitFactoryForTests(() => Promise.reject(new Error("redis_down")));

    const res = await POST(
      createMockNextRequest({
        body: { status: "error" },
        headers: { "x-internal-key": "test-telemetry-ai-demo-key-1234567890" },
        method: "POST",
        url: "http://localhost/api/telemetry/ai-demo",
      }),
      createRouteParamsContext()
    );

    expect(res.status).toBe(503);
    expect(EMIT_ALERT).not.toHaveBeenCalled();
  });

  it("does not emit raw detail in alert attributes", async () => {
    const detail = "user@example.com secret-like text";

    const res = await POST(
      createMockNextRequest({
        body: { detail, status: "error" },
        headers: { "x-internal-key": "test-telemetry-ai-demo-key-1234567890" },
        method: "POST",
        url: "http://localhost/api/telemetry/ai-demo",
      }),
      createRouteParamsContext()
    );

    expect(res.status).toBe(200);
    expect(EMIT_ALERT).toHaveBeenCalledTimes(1);

    const [_event, options] = EMIT_ALERT.mock.calls[0] ?? [];
    expect(_event).toBe("ai_demo.stream");
    expect(options).toMatchObject({
      attributes: {
        detail_hash: expect.any(String),
        detail_length: detail.length,
        has_detail: true,
        status: "error",
      },
      severity: "warning",
    });

    expect(options.attributes).not.toHaveProperty("detail");
    expect(JSON.stringify(options.attributes)).not.toContain(detail);
  });
});
