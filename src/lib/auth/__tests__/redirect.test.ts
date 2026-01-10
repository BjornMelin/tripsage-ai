/** @vitest-environment node */

import { describe, expect, it } from "vitest";
import { withEnv } from "@/test/utils/with-env";

async function loadResolver() {
  const module = await import("@/lib/auth/redirect");
  return module.resolveRedirectUrl;
}

const emptyOriginEnv = {
  APP_BASE_URL: undefined,
  NEXT_PUBLIC_SITE_URL: undefined,
};

describe("resolveRedirectUrl", () => {
  it("returns fallback when redirect is missing", async () => {
    await withEnv(emptyOriginEnv, async () => {
      const resolveRedirectUrl = await loadResolver();
      expect(resolveRedirectUrl()).toBe("/dashboard");
    });
  });

  it("returns fallback when redirect is an empty string", async () => {
    await withEnv(emptyOriginEnv, async () => {
      const resolveRedirectUrl = await loadResolver();
      expect(resolveRedirectUrl("")).toBe("/dashboard");
    });
  });

  it("returns fallback when redirect is only whitespace", async () => {
    await withEnv(emptyOriginEnv, async () => {
      const resolveRedirectUrl = await loadResolver();
      expect(resolveRedirectUrl("   \t  ")).toBe("/dashboard");
    });
  });

  it("allows relative redirects on the same origin", async () => {
    await withEnv(emptyOriginEnv, async () => {
      const resolveRedirectUrl = await loadResolver();
      expect(resolveRedirectUrl("/welcome")).toBe("/welcome");
    });
  });

  it("rejects external hosts not on the allowlist", async () => {
    await withEnv(emptyOriginEnv, async () => {
      const resolveRedirectUrl = await loadResolver();
      expect(resolveRedirectUrl("https://evil.example.com")).toBe("/dashboard");
    });
  });

  it("rejects protocol-relative redirects", async () => {
    await withEnv(emptyOriginEnv, async () => {
      const resolveRedirectUrl = await loadResolver();
      expect(resolveRedirectUrl("//evil.example.com/path")).toBe("/dashboard");
    });
  });

  it("allows hosts on the APP_BASE_URL allowlist", async () => {
    await withEnv(
      {
        APP_BASE_URL: "https://app.example.com",
        NEXT_PUBLIC_SITE_URL: "https://primary.example.com",
      },
      async () => {
        const resolveRedirectUrl = await loadResolver();
        expect(resolveRedirectUrl("https://app.example.com/settings")).toBe(
          "/settings"
        );
        expect(
          resolveRedirectUrl("https://app.example.com/settings", { absolute: true })
        ).toBe("https://app.example.com/settings");
      }
    );
  });

  it("allows hosts on the allowlist", async () => {
    await withEnv(
      {
        NEXT_PUBLIC_SITE_URL: "https://app.example.com",
      },
      async () => {
        const resolveRedirectUrl = await loadResolver();
        expect(resolveRedirectUrl("https://app.example.com/ok")).toBe("/ok");
        expect(
          resolveRedirectUrl("https://app.example.com/ok", { absolute: true })
        ).toBe("https://app.example.com/ok");
      }
    );
  });

  it("returns absolute when requested for relative inputs", async () => {
    await withEnv(
      {
        NEXT_PUBLIC_SITE_URL: "https://app.example.com",
      },
      async () => {
        const resolveRedirectUrl = await loadResolver();
        expect(resolveRedirectUrl("/welcome", { absolute: true })).toBe(
          "https://app.example.com/welcome"
        );
      }
    );
  });

  it("returns fallback for malformed URLs", async () => {
    await withEnv(emptyOriginEnv, async () => {
      const resolveRedirectUrl = await loadResolver();
      expect(resolveRedirectUrl("http://[::1")).toBe("/dashboard");
      expect(resolveRedirectUrl("http://")).toBe("/dashboard");
    });
  });

  it("rejects non-http protocols", async () => {
    await withEnv(emptyOriginEnv, async () => {
      const resolveRedirectUrl = await loadResolver();
      expect(resolveRedirectUrl("javascript:alert(1)")).toBe("/dashboard");
      expect(resolveRedirectUrl("data:text/plain,hello")).toBe("/dashboard");
    });
  });
});
