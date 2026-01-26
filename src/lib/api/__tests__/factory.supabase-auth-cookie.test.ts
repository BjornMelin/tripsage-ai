/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import { z } from "zod";
import {
  createRouteParamsContext,
  makeJsonRequest,
  mockApiRouteAuthUser,
  mockApiRouteCookies,
  resetApiRouteMocks,
} from "@/test/helpers/api-route";
import { TEST_USER_ID } from "@/test/helpers/ids";

vi.mock("server-only", () => ({}));

describe("withApiGuards auth credentials detection", () => {
  it("accepts Supabase SSR auth-token cookies", async () => {
    resetApiRouteMocks();
    mockApiRouteCookies({ "sb-127-auth-token": "test-auth-token" });
    mockApiRouteAuthUser({ id: TEST_USER_ID });

    const { withApiGuards } = await import("@/lib/api/factory");

    const handler = withApiGuards({
      auth: true,
      botId: false,
      schema: z.strictObject({ ok: z.boolean() }),
    })(async () => new Response("ok", { status: 200 }));

    const req = makeJsonRequest("/api/test", { ok: true });
    const res = await handler(req, createRouteParamsContext());

    expect(res.status).toBe(200);
  });

  it("accepts chunked Supabase SSR auth-token cookies", async () => {
    resetApiRouteMocks();
    mockApiRouteCookies({
      "sb-127-auth-token.0": "test-auth-token-part-0",
      "sb-127-auth-token.1": "test-auth-token-part-1",
    });
    mockApiRouteAuthUser({ id: TEST_USER_ID });

    const { withApiGuards } = await import("@/lib/api/factory");

    const handler = withApiGuards({
      auth: true,
      botId: false,
      schema: z.strictObject({ ok: z.boolean() }),
    })(async () => new Response("ok", { status: 200 }));

    const req = makeJsonRequest("/api/test", { ok: true });
    const res = await handler(req, createRouteParamsContext());

    expect(res.status).toBe(200);
  });
});
