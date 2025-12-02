/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { RouteParamsContext } from "@/lib/api/factory";
import { makeJsonRequest } from "@/test/api-request-factory";
import { resetApiRouteMocks } from "@/test/api-route-helpers";

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
      { params: {} } as unknown as RouteParamsContext
    );
    expect(res.status).toBe(200);
    const json = await res.json();
    expect(json.data.challengeId).toBe("challenge-abc");
  });
});
