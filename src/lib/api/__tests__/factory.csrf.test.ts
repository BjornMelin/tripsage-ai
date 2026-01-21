/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  createRouteParamsContext,
  mockApiRouteAuthUser,
  mockApiRouteCookies,
  resetApiRouteMocks,
} from "@/test/helpers/api-route";

const REQUIRE_SAME_ORIGIN = vi.hoisted(() => vi.fn(() => ({ ok: true })));

vi.mock("server-only", () => ({}));

vi.mock("@/lib/security/csrf", () => ({
  requireSameOrigin: REQUIRE_SAME_ORIGIN,
}));

describe("withApiGuards CSRF gating", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    mockApiRouteCookies({ "sb-access-token": "test-token" });
    mockApiRouteAuthUser({ id: "test-user" });
    REQUIRE_SAME_ORIGIN.mockClear();
  });

  it("skips CSRF checks for non-mutating requests", async () => {
    const { withApiGuards } = await import("@/lib/api/factory");
    const handler = withApiGuards({
      auth: true,
      botId: false,
      csrf: true,
    })(async () => new Response("ok", { status: 200 }));

    const req = new NextRequest("http://localhost:3000/api/test", {
      method: "GET",
    });
    const res = await handler(req, createRouteParamsContext());

    expect(res.status).toBe(200);
    expect(REQUIRE_SAME_ORIGIN).not.toHaveBeenCalled();
  });

  it("runs CSRF checks for mutating requests", async () => {
    const { withApiGuards } = await import("@/lib/api/factory");
    const handler = withApiGuards({
      auth: true,
      botId: false,
      csrf: true,
    })(async () => new Response("ok", { status: 200 }));

    const req = new NextRequest("http://localhost:3000/api/test", {
      method: "POST",
    });
    const res = await handler(req, createRouteParamsContext());

    expect(res.status).toBe(200);
    expect(REQUIRE_SAME_ORIGIN).toHaveBeenCalledTimes(1);
  });

  it("bypasses CSRF checks when Authorization header is present", async () => {
    const { withApiGuards } = await import("@/lib/api/factory");
    const handler = withApiGuards({
      auth: true,
      botId: false,
      csrf: true,
    })(async () => new Response("ok", { status: 200 }));

    const req = new NextRequest("http://localhost:3000/api/test", {
      headers: { authorization: "Bearer test-token" },
      method: "POST",
    });
    const res = await handler(req, createRouteParamsContext());

    expect(res.status).toBe(200);
    expect(REQUIRE_SAME_ORIGIN).not.toHaveBeenCalled();
  });
});
