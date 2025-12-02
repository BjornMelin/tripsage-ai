/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { resolveRedirectUrl } from "@/lib/auth/redirect";

describe("resolveRedirectUrl", () => {
  it("returns fallback when redirect is missing", () => {
    expect(resolveRedirectUrl()).toBe("/dashboard");
  });

  it("allows relative redirects on the same origin", () => {
    expect(resolveRedirectUrl("/welcome")).toBe("/welcome");
  });

  it("rejects external hosts not on the allowlist", () => {
    expect(resolveRedirectUrl("https://evil.example.com")).toBe("/dashboard");
  });

  it("rejects protocol-relative redirects", () => {
    expect(resolveRedirectUrl("//evil.example.com/path")).toBe("/dashboard");
  });

  it("allows hosts on the allowlist", () => {
    const prev = process.env.NEXT_PUBLIC_SITE_URL;
    try {
      process.env.NEXT_PUBLIC_SITE_URL = "https://app.example.com";
      expect(resolveRedirectUrl("https://app.example.com/ok")).toBe(
        "https://app.example.com/ok"
      );
    } finally {
      if (prev === undefined) {
        Reflect.deleteProperty(process.env, "NEXT_PUBLIC_SITE_URL");
      } else {
        process.env.NEXT_PUBLIC_SITE_URL = prev;
      }
    }
  });
});
