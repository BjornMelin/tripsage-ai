import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getGoogleMapsServerKey,
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
    vi.resetModules();
  });

  describe("getServerEnv", () => {
    it("should throw when called on client side", () => {
      // Mock window to simulate client environment
      const originalWindow = global.window;
      Object.defineProperty(global, "window", {
        configurable: true,
        value: {},
        writable: true,
      });

      try {
        expect(() => getServerEnv()).toThrow("cannot be called on client side");
      } finally {
        // Restore
        if (originalWindow) {
          Object.defineProperty(global, "window", {
            configurable: true,
            value: originalWindow,
            writable: true,
          });
        } else {
          (global as { window?: unknown }).window = undefined;
        }
      }
    });

    it("should return validated server environment", () => {
      vi.stubEnv("NODE_ENV", "test");
      vi.stubEnv("GOOGLE_MAPS_SERVER_API_KEY", "test-server-key");

      const env = getServerEnv();
      expect(env).toBeDefined();
      expect(env.NODE_ENV).toBe("test");
      expect(env.GOOGLE_MAPS_SERVER_API_KEY).toBe("test-server-key");
    });

    it("should throw on invalid environment", () => {
      vi.stubEnv("NODE_ENV", "invalid");

      expect(() => getServerEnv()).toThrow("Environment validation failed");
    });
  });

  describe("getServerEnvVar", () => {
    it("should return environment variable value", () => {
      vi.stubEnv("GOOGLE_MAPS_SERVER_API_KEY", "test-key");

      const value = getServerEnvVar("GOOGLE_MAPS_SERVER_API_KEY");
      expect(value).toBe("test-key");
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
      vi.stubEnv("GOOGLE_MAPS_SERVER_API_KEY", "test-key");

      const value = getServerEnvVarWithFallback(
        "GOOGLE_MAPS_SERVER_API_KEY",
        "fallback"
      );
      expect(value).toBe("test-key");
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
    it("should return Google Maps server API key", () => {
      vi.stubEnv("GOOGLE_MAPS_SERVER_API_KEY", "test-server-key");

      const key = getGoogleMapsServerKey();
      expect(key).toBe("test-server-key");
    });

    it("should throw when key is missing", () => {
      Reflect.deleteProperty(process.env, "GOOGLE_MAPS_SERVER_API_KEY");

      expect(() => getGoogleMapsServerKey()).toThrow(
        "GOOGLE_MAPS_SERVER_API_KEY is required"
      );
    });

    it("should throw when key is 'undefined' string", () => {
      vi.stubEnv("GOOGLE_MAPS_SERVER_API_KEY", "undefined");

      expect(() => getGoogleMapsServerKey()).toThrow(
        /GOOGLE_MAPS_SERVER_API_KEY.*required/
      );
    });
  });
});
