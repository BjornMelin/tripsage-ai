/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  __resetServerEnvCacheForTest,
  getServerEnv,
  getServerEnvVar,
  getServerEnvVarWithFallback,
} from "../server";

const exactBooleanEnvFlags = ["ENABLE_AI_DEMO"] as const;

function stubRequiredProductionEnv(): void {
  vi.stubEnv("NODE_ENV", "production");
  vi.stubEnv("APP_BASE_URL", "https://app.example.com");
  vi.stubEnv("HMAC_SECRET", "h".repeat(32));
  vi.stubEnv("SUPABASE_JWT_SECRET", "j".repeat(32));
  vi.stubEnv("TELEMETRY_HASH_SECRET", "t".repeat(32));
}

describe("env/server", () => {
  beforeEach(() => {
    // Set up required env vars for tests
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "test-publishable-key");
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

    it("should return proxy during build phase that fails on access", () => {
      vi.stubEnv("NEXT_PHASE", "phase-production-build");

      const env = getServerEnv();
      expect(() => env.NODE_ENV).toThrow(/build phase/i);
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

    it("should accept legacy anon Supabase key as a migration fallback", () => {
      Reflect.deleteProperty(process.env, "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY");
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");

      const env = getServerEnv();
      expect(env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY).toBe("test-anon-key");
    });

    it("should throw on invalid environment", () => {
      vi.stubEnv("NODE_ENV", "invalid");

      expect(() => getServerEnv()).toThrow("Environment validation failed");
    });

    it.each(exactBooleanEnvFlags)(
      "parses %s only from exact boolean strings",
      (flag) => {
        vi.stubEnv(flag, "true");
        expect(getServerEnv()[flag]).toBe(true);

        vi.stubEnv(flag, "false");
        __resetServerEnvCacheForTest();
        expect(getServerEnv()[flag]).toBe(false);
      }
    );

    it.each(exactBooleanEnvFlags)("rejects invalid %s values", (flag) => {
      vi.stubEnv(flag, "yes");

      expect(() => getServerEnv()).toThrow("Environment validation failed");
    });

    it.each(exactBooleanEnvFlags)("treats blank %s values as unset", (flag) => {
      vi.stubEnv(flag, "   ");

      expect(getServerEnv()[flag]).toBe(false);
    });

    it.each([" false ", "FALSE", "1", "*"])(
      "rejects non-canonical ENABLE_AI_DEMO=%j",
      (value) => {
        vi.stubEnv("ENABLE_AI_DEMO", value);

        expect(() => getServerEnv()).toThrow("Environment validation failed");
      }
    );

    it("requires a dedicated MFA backup-code pepper in production", () => {
      stubRequiredProductionEnv();
      Reflect.deleteProperty(process.env, "MFA_BACKUP_CODE_PEPPER");

      expect(() => getServerEnv()).toThrow("Environment validation failed");
    });

    it("rejects reusing the Supabase JWT secret as the production MFA pepper", () => {
      const sharedSecret = "s".repeat(32);
      stubRequiredProductionEnv();
      vi.stubEnv("MFA_BACKUP_CODE_PEPPER", sharedSecret);
      vi.stubEnv("SUPABASE_JWT_SECRET", sharedSecret);

      expect(() => getServerEnv()).toThrow(
        "MFA_BACKUP_CODE_PEPPER must be distinct from SUPABASE_JWT_SECRET"
      );
    });

    it("accepts distinct production MFA pepper and Supabase JWT secrets", () => {
      stubRequiredProductionEnv();
      vi.stubEnv("MFA_BACKUP_CODE_PEPPER", "m".repeat(32));

      const env = getServerEnv();

      expect(env.MFA_BACKUP_CODE_PEPPER).toBe("m".repeat(32));
      expect(env.SUPABASE_JWT_SECRET).toBe("j".repeat(32));
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
