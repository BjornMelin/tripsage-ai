import { describe, expect, it } from "vitest";

import nextConfig from "../../next.config";

describe("next.config.ts", () => {
  it("keeps baseline security headers enabled", async () => {
    const headersFn = nextConfig.headers;
    expect(headersFn).toBeTypeOf("function");
    if (typeof headersFn !== "function") {
      throw new Error("Expected nextConfig.headers to be a function");
    }

    const rules = await headersFn();
    expect(Array.isArray(rules)).toBe(true);

    const globalRule = rules.find((rule) => rule.source === "/:path*");
    expect(globalRule).toBeDefined();

    const headers = globalRule?.headers ?? [];
    expect(headers).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ key: "X-Frame-Options" }),
        expect.objectContaining({ key: "X-Content-Type-Options" }),
        expect.objectContaining({ key: "Referrer-Policy" }),
        expect.objectContaining({ key: "Permissions-Policy" }),
      ])
    );

    expect(rules).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ source: "/_next/static/:path*" }),
        expect.objectContaining({ source: "/static/:path*" }),
      ])
    );
  });

  it("keeps image content security policy enabled", () => {
    expect(nextConfig.images?.contentSecurityPolicy).toMatch(/default-src 'self'/);
  });
});
