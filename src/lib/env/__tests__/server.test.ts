/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  __resetServerEnvCacheForTest,
  getServerEnv,
  getServerEnvVar,
  getServerEnvVarWithFallback,
} from "../server";

describe("env/server", () => {
  beforeEach(() => {
    // Set up required env vars for tests
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");
    __resetServerEnvCacheForTest();
    vi.resetModules();
  });

  describe("getServerEnv", () => {
    it("should throw when called on client side", () => {
      // Mock window to simulate client environment
      const originalWindow = (globalThis as { window?: unknown }).window;
      // In tests, jsdom defines a Window-like object; replace it with a
      // plain object so getServerEnv() treats it as a client-only context.
      (globalThis as { window?: unknown }).window = {};

      try {
        expect(() => getServerEnv()).toThrow("cannot be called on client side");
      } finally {
        // Restore
        (globalThis as { window?: unknown }).window = originalWindow;
      }
    });

    it("should return validated server environment", () => {
      vi.stubEnv("NODE_ENV", "test");
      vi.stubEnv("GOOGLE_MAPS_SERVER_API_KEY", "test-server-key-for-google-maps-api");

      const env = getServerEnv();
      expect(env).toBeDefined();
      expect(env.NODE_ENV).toBe("test");
      expect(env.GOOGLE_MAPS_SERVER_API_KEY).toBe(
        "test-server-key-for-google-maps-api"
      );
    });

    it("should throw on invalid environment", () => {
      vi.stubEnv("NODE_ENV", "invalid");

      expect(() => getServerEnv()).toThrow("Environment validation failed");
    });
  });

  describe("getServerEnvVar", () => {
    it("should return environment variable value", () => {
      vi.stubEnv("GOOGLE_MAPS_SERVER_API_KEY", "test-key-for-google-maps-server-api");

      const value = getServerEnvVar("GOOGLE_MAPS_SERVER_API_KEY");
      expect(value).toBe("test-key-for-google-maps-server-api");
    });

    it("should throw when variable is missing", () => {
      Reflect.deleteProperty(process.env, "GOOGLE_MAPS_SERVER_API_KEY");

      expect(() => getServerEnvVar("GOOGLE_MAPS_SERVER_API_KEY")).toThrow(
        "is not defined"
      );
    });
  });

  describe("getServerEnvVarWithFallback", () => {
    it("should return environment variable value when present", () => {
      vi.stubEnv("GOOGLE_MAPS_SERVER_API_KEY", "test-key-for-google-maps-server-api");

      const value = getServerEnvVarWithFallback(
        "GOOGLE_MAPS_SERVER_API_KEY",
        "fallback"
      );
      expect(value).toBe("test-key-for-google-maps-server-api");
    });

    it("should return fallback when variable is missing", () => {
      Reflect.deleteProperty(process.env, "GOOGLE_MAPS_SERVER_API_KEY");

      const value = getServerEnvVarWithFallback(
        "GOOGLE_MAPS_SERVER_API_KEY",
        "fallback"
      );
      expect(value).toBe("fallback");
    });
  });

  describe("getGoogleMapsServerKey", () => {
    it("should return Google Maps server API key", async () => {
      vi.stubEnv("GOOGLE_MAPS_SERVER_API_KEY", "test-server-key-for-google-maps-api");
      vi.resetModules();
      const { getGoogleMapsServerKey: freshGetGoogleMapsServerKey } = await import(
        "../server"
      );

      const key = freshGetGoogleMapsServerKey();
      expect(key).toBe("test-server-key-for-google-maps-api");
    });

    it("should throw when key is missing", async () => {
      Reflect.deleteProperty(process.env, "GOOGLE_MAPS_SERVER_API_KEY");
      vi.resetModules();
      const { getGoogleMapsServerKey: freshGetGoogleMapsServerKey } = await import(
        "../server"
      );

      expect(() => freshGetGoogleMapsServerKey()).toThrow("is not defined");
    });

    it("should throw when key is 'undefined' string", async () => {
      vi.stubEnv("GOOGLE_MAPS_SERVER_API_KEY", "undefined");
      vi.resetModules();
      const { getGoogleMapsServerKey: freshGetGoogleMapsServerKey } = await import(
        "../server"
      );

      // Validation rejects short/invalid values (including the literal "undefined" string)
      expect(() => freshGetGoogleMapsServerKey()).toThrow(/GOOGLE_MAPS_SERVER_API_KEY/);
    });
  });
});
