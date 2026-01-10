/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";

async function loadResolver() {
  const module = await import("@/lib/auth/redirect");
  return module.resolveRedirectUrl;
}

async function withEnv<T>(
  values: Record<string, string | undefined>,
  fn: (resolveRedirectUrl: Awaited<ReturnType<typeof loadResolver>>) => T | Promise<T>
): Promise<T> {
  const prev = new Map<string, string | undefined>();
  for (const [key, value] of Object.entries(values)) {
    prev.set(key, process.env[key]);
    if (value === undefined) {
      Reflect.deleteProperty(process.env, key);
    } else {
      process.env[key] = value;
    }
  }

  vi.resetModules();
  try {
    return await fn(await loadResolver());
  } finally {
    vi.resetModules();
    for (const [key, value] of prev.entries()) {
      if (value === undefined) {
        Reflect.deleteProperty(process.env, key);
      } else {
        process.env[key] = value;
      }
    }
  }
}

describe("resolveRedirectUrl", () => {
  it("returns fallback when redirect is missing", async () => {
    await withEnv({}, (resolveRedirectUrl) => {
      expect(resolveRedirectUrl()).toBe("/dashboard");
    });
  });

  it("returns fallback when redirect is an empty string", async () => {
    await withEnv({}, (resolveRedirectUrl) => {
      expect(resolveRedirectUrl("")).toBe("/dashboard");
    });
  });

  it("returns fallback when redirect is only whitespace", async () => {
    await withEnv({}, (resolveRedirectUrl) => {
      expect(resolveRedirectUrl("   \t  ")).toBe("/dashboard");
    });
  });

  it("allows relative redirects on the same origin", async () => {
    await withEnv({}, (resolveRedirectUrl) => {
      expect(resolveRedirectUrl("/welcome")).toBe("/welcome");
    });
  });

  it("rejects external hosts not on the allowlist", async () => {
    await withEnv({}, (resolveRedirectUrl) => {
      expect(resolveRedirectUrl("https://evil.example.com")).toBe("/dashboard");
    });
  });

  it("rejects protocol-relative redirects", async () => {
    await withEnv({}, (resolveRedirectUrl) => {
      expect(resolveRedirectUrl("//evil.example.com/path")).toBe("/dashboard");
    });
  });

  it("allows hosts on the APP_BASE_URL allowlist", async () => {
    await withEnv(
      {
        APP_BASE_URL: "https://app.example.com",
        NEXT_PUBLIC_SITE_URL: "https://primary.example.com",
      },
      (resolveRedirectUrl) => {
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
      (resolveRedirectUrl) => {
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
      (resolveRedirectUrl) => {
        expect(resolveRedirectUrl("/welcome", { absolute: true })).toBe(
          "https://app.example.com/welcome"
        );
      }
    );
  });

  it("returns fallback for malformed URLs", async () => {
    await withEnv({}, (resolveRedirectUrl) => {
      expect(resolveRedirectUrl("http://[::1")).toBe("/dashboard");
      expect(resolveRedirectUrl("http://")).toBe("/dashboard");
    });
  });

  it("rejects non-http protocols", async () => {
    await withEnv({}, (resolveRedirectUrl) => {
      expect(resolveRedirectUrl("javascript:alert(1)")).toBe("/dashboard");
      expect(resolveRedirectUrl("data:text/plain,hello")).toBe("/dashboard");
    });
  });
});
