/** @vitest-environment node */

import { describe, expect, it, vi } from "vitest";
import { withEnv } from "@/test/utils/with-env";

const REQUIRED_PUBLIC_ENV = {
  NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "test-publishable-key",
  NEXT_PUBLIC_SUPABASE_URL: "https://test.supabase.co",
} as const;

function LoadClientOrigin() {
  return import("../client-origin");
}

describe("client-origin", () => {
  it("prefers NEXT_PUBLIC_SITE_URL", async () => {
    await withEnv(
      {
        ...REQUIRED_PUBLIC_ENV,
        NEXT_PUBLIC_APP_URL: "https://app.example.com",
        NEXT_PUBLIC_BASE_URL: "https://base.example.com",
        NEXT_PUBLIC_SITE_URL: "https://site.example.com",
      },
      async () => {
        const { getClientOrigin } = await LoadClientOrigin();
        expect(getClientOrigin()).toBe("https://site.example.com");
      }
    );
  });

  it("falls back through base URL and app URL", async () => {
    await withEnv(
      {
        ...REQUIRED_PUBLIC_ENV,
        NEXT_PUBLIC_APP_URL: "https://app.example.com",
        NEXT_PUBLIC_BASE_URL: "https://base.example.com",
        NEXT_PUBLIC_SITE_URL: undefined,
      },
      async () => {
        const { getClientOrigin } = await LoadClientOrigin();
        expect(getClientOrigin()).toBe("https://base.example.com");
      }
    );

    await withEnv(
      {
        ...REQUIRED_PUBLIC_ENV,
        NEXT_PUBLIC_APP_URL: "https://app.example.com",
        NEXT_PUBLIC_BASE_URL: undefined,
        NEXT_PUBLIC_SITE_URL: undefined,
      },
      async () => {
        const { getClientOrigin } = await LoadClientOrigin();
        expect(getClientOrigin()).toBe("https://app.example.com");
      }
    );
  });

  it("falls back to localhost without logging raw diagnostics", async () => {
    await withEnv(
      {
        ...REQUIRED_PUBLIC_ENV,
        NEXT_PUBLIC_APP_URL: undefined,
        NEXT_PUBLIC_BASE_URL: undefined,
        NEXT_PUBLIC_SITE_URL: undefined,
      },
      async () => {
        const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => undefined);
        const { getClientOrigin } = await LoadClientOrigin();

        expect(getClientOrigin()).toBe("http://localhost:3000");
        expect(warnSpy).not.toHaveBeenCalled();
        warnSpy.mockRestore();
      }
    );
  });

  it("converts relative paths to absolute URLs", async () => {
    await withEnv(
      {
        ...REQUIRED_PUBLIC_ENV,
        NEXT_PUBLIC_APP_URL: undefined,
        NEXT_PUBLIC_BASE_URL: undefined,
        NEXT_PUBLIC_SITE_URL: "https://site.example.com",
      },
      async () => {
        const { toClientAbsoluteUrl } = await LoadClientOrigin();

        expect(toClientAbsoluteUrl("/dashboard")).toBe(
          "https://site.example.com/dashboard"
        );
        expect(toClientAbsoluteUrl("https://other.example.com/path")).toBe(
          "https://other.example.com/path"
        );
      }
    );
  });
});
