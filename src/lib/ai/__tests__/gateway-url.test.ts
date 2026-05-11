/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

const getServerEnvVarWithFallbackMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/env/server", () => ({
  getServerEnvVarWithFallback: getServerEnvVarWithFallbackMock,
}));

describe("validateGatewayBaseUrl", () => {
  beforeEach(() => {
    vi.resetModules();
    getServerEnvVarWithFallbackMock.mockReset();
    getServerEnvVarWithFallbackMock.mockImplementation(
      (_key: string, fallback) => fallback
    );
  });

  it("rejects explicit non-default ports on allowlisted Gateway hosts", async () => {
    const { validateGatewayBaseUrl } = await import("../gateway-url");

    const result = validateGatewayBaseUrl("https://ai-gateway.vercel.sh:8443/v3/ai", {
      source: "team",
    });

    expect(result).toEqual({ ok: false, reason: "port_not_allowed" });
  });

  it("allows the implicit HTTPS port on allowlisted Gateway hosts", async () => {
    const { validateGatewayBaseUrl } = await import("../gateway-url");

    const result = validateGatewayBaseUrl("https://ai-gateway.vercel.sh/v3/ai", {
      source: "team",
    });

    expect(result).toEqual({
      baseUrl: "https://ai-gateway.vercel.sh/v3/ai",
      host: "ai-gateway.vercel.sh",
      ok: true,
      source: "team",
    });
  });
});
