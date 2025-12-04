/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  createRouteParamsContext,
  makeJsonRequest,
  mockApiRouteAuthUser,
  resetApiRouteMocks,
} from "@/test/helpers/api-route";

const challengeTotp = vi.hoisted(() => vi.fn());

vi.mock("@/lib/security/mfa", () => ({ challengeTotp }));

describe("POST /api/auth/mfa/challenge", () => {
  beforeEach(() => {
    resetApiRouteMocks();
    challengeTotp.mockReset();
    challengeTotp.mockResolvedValue({ challengeId: "challenge-abc" });
  });

  afterEach(() => {
    resetApiRouteMocks();
    challengeTotp.mockReset();
  });

  it("issues a challenge", async () => {
    const { POST } = await import("../challenge/route");
    const factorId = "11111111-1111-4111-8111-111111111111";
    const res = await POST(
      makeJsonRequest("http://localhost/api/auth/mfa/challenge", {
        factorId,
      }),
      createRouteParamsContext()
    );
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.data.challengeId).toBe("challenge-abc");
    expect(challengeTotp).toHaveBeenCalledTimes(1);
    expect(challengeTotp).toHaveBeenCalledWith(expect.anything(), { factorId });
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
    expect(challengeTotp).not.toHaveBeenCalled();
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
    expect(challengeTotp).not.toHaveBeenCalled();
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
    expect(res.status).toBe(500);
  });
});
