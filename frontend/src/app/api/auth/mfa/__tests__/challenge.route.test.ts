/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { makeJsonRequest } from "@/test/api-request-factory";
import { mockApiRouteAuthUser, resetApiRouteMocks } from "@/test/api-route-helpers";
import { createRouteParamsContext } from "@/test/route-helpers";

describe("POST /api/auth/mfa/challenge", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    vi.doMock("@/lib/security/mfa", () => ({
      challengeTotp: vi.fn(async () => ({ challengeId: "challenge-abc" })),
    }));
  });

  afterEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
  });

  it("issues a challenge", async () => {
    const { POST } = await import("../challenge/route");
    const res = await POST(
      makeJsonRequest("http://localhost/api/auth/mfa/challenge", {
        factorId: crypto.randomUUID(),
      }),
      createRouteParamsContext()
    );
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.data.challengeId).toBe("challenge-abc");
  });

  it("returns 400 for invalid payload", async () => {
    const { POST } = await import("../challenge/route");
    const res = await POST(
      makeJsonRequest("http://localhost/api/auth/mfa/challenge", {
        factorId: "not-a-uuid",
      }),
      createRouteParamsContext()
    );
    expect(res.status).toBe(400);
  });

  it("returns 401 when unauthenticated", async () => {
    mockApiRouteAuthUser(null);
    const { POST } = await import("../challenge/route");
    const res = await POST(
      makeJsonRequest("http://localhost/api/auth/mfa/challenge", {
        factorId: crypto.randomUUID(),
      }),
      createRouteParamsContext()
    );
    expect(res.status).toBe(401);
  });

  it("returns 500 when challenge fails", async () => {
    vi.doMock("@/lib/security/mfa", () => ({
      challengeTotp: vi.fn(() => {
        throw new Error("boom");
      }),
    }));
    const { POST } = await import("../challenge/route");
    const res = await POST(
      makeJsonRequest("http://localhost/api/auth/mfa/challenge", {
        factorId: crypto.randomUUID(),
      }),
      createRouteParamsContext()
    );
    expect(res.status).toBeGreaterThanOrEqual(500);
  });
});
