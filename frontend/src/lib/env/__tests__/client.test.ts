import { beforeEach, describe, expect, it, vi } from "vitest";

describe("env/client", () => {
  beforeEach(() => {
    vi.resetModules();
    // Clear NEXT_PUBLIC_ vars
    const keys = Object.keys(process.env).filter((k) => k.startsWith("NEXT_PUBLIC_"));
    for (const key of keys) {
      Reflect.deleteProperty(process.env, key);
    }
  });

  describe("getClientEnv", () => {
    it("should return validated client environment", async () => {
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");
      vi.stubEnv("NEXT_PUBLIC_APP_NAME", "TestApp");

      // Re-import to get fresh validation
      vi.resetModules();
      const { getClientEnv: freshGetClientEnv } = await import("../client");

      const env = freshGetClientEnv();
      expect(env.NEXT_PUBLIC_SUPABASE_URL).toBe("https://test.supabase.co");
      expect(env.NEXT_PUBLIC_SUPABASE_ANON_KEY).toBe("test-anon-key");
      expect(env.NEXT_PUBLIC_APP_NAME).toBe("TestApp");
    });

    it("should throw on missing required variables in production", async () => {
      vi.stubEnv("NODE_ENV", "production");
      // Missing NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY

      vi.resetModules();
      await expect(async () => {
        const { getClientEnv: freshGetClientEnv } = await import("../client");
        freshGetClientEnv();
      }).rejects.toThrow();
    });

    it("should return valid dummy values in development when validation fails", async () => {
      vi.stubEnv("NODE_ENV", "development");
      // Missing required vars

      vi.resetModules();
      const { getClientEnv: freshGetClientEnv } = await import("../client");

      const env = freshGetClientEnv();
      expect(env.NEXT_PUBLIC_APP_NAME).toBe("TripSage");
      expect(env.NEXT_PUBLIC_SUPABASE_ANON_KEY).toBe("dummy-dev-anon-key");
      expect(env.NEXT_PUBLIC_SUPABASE_URL).toBe("http://localhost:54321");
    });
  });

  describe("getClientEnvVar", () => {
    it("should return environment variable value", async () => {
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");

      vi.resetModules();
      const { getClientEnvVar: freshGetClientEnvVar } = await import("../client");

      const url = freshGetClientEnvVar("NEXT_PUBLIC_SUPABASE_URL");
      expect(url).toBe("https://test.supabase.co");
    });

    it("should throw when variable is missing", async () => {
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");
      // Missing NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY

      vi.resetModules();
      const { getClientEnvVar: freshGetClientEnvVar } = await import("../client");

      expect(() =>
        freshGetClientEnvVar("NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY")
      ).toThrow("is not defined");
    });
  });

  describe("getClientEnvVarWithFallback", () => {
    it("should return environment variable value when present", async () => {
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");

      vi.resetModules();
      const { getClientEnvVarWithFallback: freshGetClientEnvVarWithFallback } =
        await import("../client");

      const url = freshGetClientEnvVarWithFallback(
        "NEXT_PUBLIC_SUPABASE_URL",
        "fallback"
      );
      expect(url).toBe("https://test.supabase.co");
    });

    it("should return fallback when variable is missing", async () => {
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");

      vi.resetModules();
      const { getClientEnvVarWithFallback: freshGetClientEnvVarWithFallback } =
        await import("../client");

      const value = freshGetClientEnvVarWithFallback(
        "NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY",
        "fallback"
      );
      expect(value).toBe("fallback");
    });
  });

  describe("getGoogleMapsBrowserKey", () => {
    it("should return Google Maps browser API key when configured", async () => {
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");
      vi.stubEnv("NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY", "test-browser-key");

      vi.resetModules();
      const { getGoogleMapsBrowserKey: freshGetGoogleMapsBrowserKey } = await import(
        "../client"
      );

      const key = freshGetGoogleMapsBrowserKey();
      expect(key).toBe("test-browser-key");
    });

    it("should return undefined when key is not configured", async () => {
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");
      // Missing NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY

      vi.resetModules();
      const { getGoogleMapsBrowserKey: freshGetGoogleMapsBrowserKey } = await import(
        "../client"
      );

      const key = freshGetGoogleMapsBrowserKey();
      expect(key).toBeUndefined();
    });
  });

  describe("publicEnv", () => {
    it("should export frozen public environment object", async () => {
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");

      vi.resetModules();
      const { publicEnv: freshPublicEnv } = await import("../client");

      expect(freshPublicEnv).toBeDefined();
      expect(Object.isFrozen(freshPublicEnv)).toBe(true);
      expect(freshPublicEnv.NEXT_PUBLIC_SUPABASE_URL).toBe("https://test.supabase.co");
    });
  });
});
