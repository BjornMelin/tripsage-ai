/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { resolveRedirectUrl } from "@/lib/auth/redirect";

describe("resolveRedirectUrl", () => {
  it("returns fallback when redirect is missing", () => {
    expect(resolveRedirectUrl()).toBe("/dashboard");
  });

  it("returns fallback when redirect is an empty string", () => {
    expect(resolveRedirectUrl("")).toBe("/dashboard");
  });

  it("returns fallback when redirect is only whitespace", () => {
    expect(resolveRedirectUrl("   \t  ")).toBe("/dashboard");
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

  it("allows hosts on the APP_BASE_URL allowlist", () => {
    const prevSiteUrl = process.env.NEXT_PUBLIC_SITE_URL;
    const prevAppBaseUrl = process.env.APP_BASE_URL;
    try {
      process.env.NEXT_PUBLIC_SITE_URL = "https://primary.example.com";
      process.env.APP_BASE_URL = "https://app.example.com";
      expect(resolveRedirectUrl("https://app.example.com/settings")).toBe(
        "https://app.example.com/settings"
      );
    } finally {
      if (prevSiteUrl === undefined) {
        Reflect.deleteProperty(process.env, "NEXT_PUBLIC_SITE_URL");
      } else {
        process.env.NEXT_PUBLIC_SITE_URL = prevSiteUrl;
      }

      if (prevAppBaseUrl === undefined) {
        Reflect.deleteProperty(process.env, "APP_BASE_URL");
      } else {
        process.env.APP_BASE_URL = prevAppBaseUrl;
      }
    }
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

  it("returns fallback for malformed URLs", () => {
    expect(resolveRedirectUrl("http://[::1")).toBe("/dashboard");
    expect(resolveRedirectUrl("http://")).toBe("/dashboard");
  });

  it("rejects non-http protocols", () => {
    expect(resolveRedirectUrl("javascript:alert(1)")).toBe("/dashboard");
    expect(resolveRedirectUrl("data:text/plain,hello")).toBe("/dashboard");
  });
});
