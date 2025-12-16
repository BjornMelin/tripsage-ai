/** @vitest-environment jsdom */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("client-origin", () => {
  beforeEach(() => {
    vi.resetModules();
    // Clear NEXT_PUBLIC_ vars
    const keys = Object.keys(process.env).filter((k) => k.startsWith("NEXT_PUBLIC_"));
    for (const key of keys) {
      Reflect.deleteProperty(process.env, key);
    }
    // Set required env vars for client.ts validation
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");
    vi.stubEnv("NODE_ENV", "development");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  describe("getClientOrigin", () => {
    it("should return window.location.origin in browser", async () => {
      // jsdom sets window.location.origin to http://localhost:3000 (with port)
      expect(typeof window).toBe("object");
      expect(window.location.origin).toBe("http://localhost:3000");

      const { getClientOrigin } = await import("../client-origin");
      expect(getClientOrigin()).toBe("http://localhost:3000");
    });

    it("should return NEXT_PUBLIC_SITE_URL when window is unavailable", async () => {
      vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://tripsage.ai");

      // Simulate server-side by removing window
      const originalWindow = globalThis.window;
      // biome-ignore lint/suspicious/noExplicitAny: test utility
      (globalThis as any).window = undefined;

      vi.resetModules();
      const { getClientOrigin } = await import("../client-origin");
      expect(getClientOrigin()).toBe("https://tripsage.ai");

      globalThis.window = originalWindow;
    });

    it("should fall back to NEXT_PUBLIC_BASE_URL when SITE_URL is not set", async () => {
      vi.stubEnv("NEXT_PUBLIC_BASE_URL", "https://fallback.example.com");

      const originalWindow = globalThis.window;
      // biome-ignore lint/suspicious/noExplicitAny: test utility
      (globalThis as any).window = undefined;

      vi.resetModules();
      const { getClientOrigin } = await import("../client-origin");
      expect(getClientOrigin()).toBe("https://fallback.example.com");

      globalThis.window = originalWindow;
    });

    it("should fall back to localhost when no env vars are set", async () => {
      const originalWindow = globalThis.window;
      // biome-ignore lint/suspicious/noExplicitAny: test utility
      (globalThis as any).window = undefined;

      vi.resetModules();
      const { getClientOrigin } = await import("../client-origin");
      expect(getClientOrigin()).toBe("http://localhost:3000");

      globalThis.window = originalWindow;
    });

    it("should warn in development when window exists but no env vars are set", async () => {
      const consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {
        // no-op: suppress console output in test
      });

      // Clear BASE_URL if set
      Reflect.deleteProperty(process.env, "NEXT_PUBLIC_BASE_URL");

      // Mock window with no location.origin
      const originalWindow = globalThis.window;
      // biome-ignore lint/suspicious/noExplicitAny: test utility
      (globalThis as any).window = {};

      vi.resetModules();
      const { getClientOrigin } = await import("../client-origin");
      expect(getClientOrigin()).toBe("http://localhost:3000");
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining(
          "No NEXT_PUBLIC_SITE_URL or NEXT_PUBLIC_BASE_URL configured"
        )
      );

      globalThis.window = originalWindow;
      consoleWarnSpy.mockRestore();
    });
  });

  describe("toClientAbsoluteUrl", () => {
    it("should return absolute URLs unchanged", async () => {
      const { toClientAbsoluteUrl } = await import("../client-origin");
      expect(toClientAbsoluteUrl("https://example.com/path")).toBe(
        "https://example.com/path"
      );
      expect(toClientAbsoluteUrl("http://localhost:3000/api")).toBe(
        "http://localhost:3000/api"
      );
    });

    it("should convert relative paths to absolute URLs using origin", async () => {
      // In jsdom, window.location.origin is "http://localhost:3000"
      const { toClientAbsoluteUrl } = await import("../client-origin");
      expect(toClientAbsoluteUrl("/api/test")).toBe("http://localhost:3000/api/test");
      expect(toClientAbsoluteUrl("/auth/callback")).toBe(
        "http://localhost:3000/auth/callback"
      );
    });

    it("should handle paths with query strings", async () => {
      const { toClientAbsoluteUrl } = await import("../client-origin");
      expect(toClientAbsoluteUrl("/api/search?q=test")).toBe(
        "http://localhost:3000/api/search?q=test"
      );
    });
  });
});
