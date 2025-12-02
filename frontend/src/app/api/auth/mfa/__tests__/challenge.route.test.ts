/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { makeJsonRequest } from "@/test/api-request-factory";
import { mockApiRouteAuthUser, resetApiRouteMocks } from "@/test/api-route-helpers";
import { createRouteParamsContext } from "@/test/route-helpers";

const challengeTotp = vi.hoisted(() => vi.fn());

vi.mock("@/lib/security/mfa", () => ({ challengeTotp }));

describe("POST /api/auth/mfa/challenge", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    challengeTotp.mockReset();
    challengeTotp.mockResolvedValue({ challengeId: "challenge-abc" });
  });

  afterEach(() => {
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
    challengeTotp.mockImplementationOnce(() => {
      throw new Error("boom");
    });
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
