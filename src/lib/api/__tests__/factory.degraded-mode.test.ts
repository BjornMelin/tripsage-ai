/** @vitest-environment node */

import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import type { setRateLimitFactoryForTests } from "@/lib/api/factory";
import { unsafeCast } from "@/test/helpers/unsafe-cast";

const EMIT_ALERT = vi.hoisted(() => vi.fn());

vi.mock("@/lib/telemetry/alerts", () => ({
  emitOperationalAlert: (...args: Parameters<typeof EMIT_ALERT>) => EMIT_ALERT(...args),
}));

type RateLimitFactory = Parameters<typeof setRateLimitFactoryForTests>[0];

const setupTestWithRateLimitFactory = async (rateLimitFactory: RateLimitFactory) => {
  const { resetDegradedModeAlertStateForTests } = await import(
    "@/lib/telemetry/degraded-mode"
  );
  resetDegradedModeAlertStateForTests();
  EMIT_ALERT.mockReset();

  const { setRateLimitFactoryForTests, setSupabaseFactoryForTests, withApiGuards } =
    await import("@/lib/api/factory");

  setSupabaseFactoryForTests(async () => unsafeCast({}));
  setRateLimitFactoryForTests(rateLimitFactory);

  return { withApiGuards };
};

describe("withApiGuards degraded-mode policy", () => {
  afterEach(async () => {
    const { setRateLimitFactoryForTests, setSupabaseFactoryForTests } = await import(
      "@/lib/api/factory"
    );
    setRateLimitFactoryForTests(null);
    setSupabaseFactoryForTests(null);
  });

  it("defaults to fail_closed for auth:* rate limit keys", async () => {
    const { withApiGuards } = await setupTestWithRateLimitFactory(() =>
      Promise.reject(new Error("redis_down"))
    );

    const handler = withApiGuards({
      rateLimit: "auth:login",
      schema: z.strictObject({ ok: z.boolean() }),
    })(async () => new Response("ok", { status: 200 }));

    const req = new NextRequest("https://example.com/api/test", {
      body: JSON.stringify({ ok: true }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });

    const res = await handler(req, { params: Promise.resolve({}) });
    expect(res.status).toBe(503);
    expect(EMIT_ALERT).not.toHaveBeenCalled();
  });

  it("fails closed when rate limiting enforcement errors", async () => {
    const { withApiGuards } = await setupTestWithRateLimitFactory(() =>
      Promise.reject(new Error("redis_down"))
    );

    const handler = withApiGuards({
      degradedMode: "fail_closed",
      rateLimit: "trips:create",
      schema: z.strictObject({ ok: z.boolean() }),
    })(async () => new Response("ok", { status: 200 }));

    const req = new NextRequest("https://example.com/api/test", {
      body: JSON.stringify({ ok: true }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });

    const res = await handler(req, { params: Promise.resolve({}) });

    expect(res.status).toBe(503);
    expect(EMIT_ALERT).not.toHaveBeenCalled();
  });

  it("fails closed when rate limiting times out", async () => {
    const { withApiGuards } = await setupTestWithRateLimitFactory(async () => ({
      limit: 40,
      reason: "timeout",
      remaining: 0,
      reset: 0,
      success: true,
    }));

    const handler = withApiGuards({
      degradedMode: "fail_closed",
      rateLimit: "trips:create",
      schema: z.strictObject({ ok: z.boolean() }),
    })(async () => new Response("ok", { status: 200 }));

    const req = new NextRequest("https://example.com/api/test", {
      body: JSON.stringify({ ok: true }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });

    const res = await handler(req, { params: Promise.resolve({}) });

    expect(res.status).toBe(503);
    expect(EMIT_ALERT).not.toHaveBeenCalled();
  });

  it("fails open and emits a deduped alert when configured", async () => {
    const { resetDegradedModeAlertStateForTests } = await import(
      "@/lib/telemetry/degraded-mode"
    );
    resetDegradedModeAlertStateForTests();
    EMIT_ALERT.mockReset();

    const { setRateLimitFactoryForTests, setSupabaseFactoryForTests, withApiGuards } =
      await import("@/lib/api/factory");

    setSupabaseFactoryForTests(async () => unsafeCast({}));
    setRateLimitFactoryForTests(() => Promise.reject(new Error("redis_down")));

    const handlerFn = vi.fn(async () => new Response("ok", { status: 200 }));
    const handler = withApiGuards({
      degradedMode: "fail_open",
      rateLimit: "trips:create",
      schema: z.strictObject({ ok: z.boolean() }),
    })(handlerFn);

    const req1 = new NextRequest("https://example.com/api/test", {
      body: JSON.stringify({ ok: true }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });
    const res1 = await handler(req1, { params: Promise.resolve({}) });
    expect(res1.status).toBe(200);

    const req2 = new NextRequest("https://example.com/api/test", {
      body: JSON.stringify({ ok: true }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });
    const res2 = await handler(req2, { params: Promise.resolve({}) });
    expect(res2.status).toBe(200);

    expect(handlerFn).toHaveBeenCalledTimes(2);
    expect(EMIT_ALERT).toHaveBeenCalledTimes(1);
    expect(EMIT_ALERT).toHaveBeenCalledWith(
      "ratelimit.degraded",
      expect.objectContaining({
        attributes: expect.objectContaining({
          degradedMode: "fail_open",
          rateLimitKey: "trips:create",
        }),
      })
    );
  });

  it("fails open and emits a deduped alert when rate limiting times out", async () => {
    const { resetDegradedModeAlertStateForTests } = await import(
      "@/lib/telemetry/degraded-mode"
    );
    resetDegradedModeAlertStateForTests();
    EMIT_ALERT.mockReset();

    const { setRateLimitFactoryForTests, setSupabaseFactoryForTests, withApiGuards } =
      await import("@/lib/api/factory");

    setSupabaseFactoryForTests(async () => unsafeCast({}));
    setRateLimitFactoryForTests(async () => ({
      limit: 40,
      reason: "timeout",
      remaining: 0,
      reset: 0,
      success: true,
    }));

    const handlerFn = vi.fn(async () => new Response("ok", { status: 200 }));
    const handler = withApiGuards({
      degradedMode: "fail_open",
      rateLimit: "trips:create",
      schema: z.strictObject({ ok: z.boolean() }),
    })(handlerFn);

    const req1 = new NextRequest("https://example.com/api/test", {
      body: JSON.stringify({ ok: true }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });
    const res1 = await handler(req1, { params: Promise.resolve({}) });
    expect(res1.status).toBe(200);

    const req2 = new NextRequest("https://example.com/api/test", {
      body: JSON.stringify({ ok: true }),
      headers: { "content-type": "application/json" },
      method: "POST",
    });
    const res2 = await handler(req2, { params: Promise.resolve({}) });
    expect(res2.status).toBe(200);

    expect(handlerFn).toHaveBeenCalledTimes(2);
    expect(EMIT_ALERT).toHaveBeenCalledTimes(1);
    expect(EMIT_ALERT).toHaveBeenCalledWith(
      "ratelimit.degraded",
      expect.objectContaining({
        attributes: expect.objectContaining({
          degradedMode: "fail_open",
          rateLimitKey: "trips:create",
          reason: "timeout",
        }),
      })
    );
  });
});
