import { beforeEach, describe, expect, it, vi } from "vitest";
import { parseClientEnv, parseEnv } from "../schema";

describe("env/schema", () => {
  beforeEach(() => {
    vi.resetModules();
    // Clear all env vars
    const keys = Object.keys(process.env);
    for (const key of keys) {
      Reflect.deleteProperty(process.env, key);
    }
    // Set up minimal required env vars
    vi.stubEnv("NODE_ENV", "test");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://test.supabase.co");
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "test-anon-key");
  });

  describe("parseEnv", () => {
    it("should parse and validate server environment successfully", () => {
      const env = parseEnv();
      expect(env).toBeDefined();
      expect(env.NODE_ENV).toBe("test");
      expect(env.NEXT_PUBLIC_SUPABASE_URL).toBe("https://test.supabase.co");
      expect(env.NEXT_PUBLIC_SUPABASE_ANON_KEY).toBe("test-anon-key");
    });

    it("should throw on invalid NODE_ENV", () => {
      vi.stubEnv("NODE_ENV", "invalid");
      expect(() => parseEnv()).toThrow("Environment validation failed");
    });

    it("should validate Stripe secret key format in production", () => {
      vi.stubEnv("NODE_ENV", "production");
      vi.stubEnv("SUPABASE_JWT_SECRET", "test-jwt-secret");
      vi.stubEnv("STRIPE_SECRET_KEY", "sk_test_invalid");

      expect(() => parseEnv()).toThrow(/sk_live_/);
    });

    it("should accept sk_test_ Stripe key in development", () => {
      vi.stubEnv("NODE_ENV", "development");
      vi.stubEnv("STRIPE_SECRET_KEY", "sk_test_1234567890");

      const env = parseEnv();
      expect(env.STRIPE_SECRET_KEY).toBe("sk_test_1234567890");
    });

    it("should accept sk_live_ Stripe key in production", () => {
      vi.stubEnv("NODE_ENV", "production");
      vi.stubEnv("SUPABASE_JWT_SECRET", "test-jwt-secret");
      vi.stubEnv("STRIPE_SECRET_KEY", "sk_live_1234567890");

      const env = parseEnv();
      expect(env.STRIPE_SECRET_KEY).toBe("sk_live_1234567890");
    });

    it("should validate Anthropic API key format", () => {
      vi.stubEnv("ANTHROPIC_API_KEY", "invalid-key");
      expect(() => parseEnv()).toThrow(/sk-ant-/);
    });

    it("should accept valid Anthropic API key", () => {
      vi.stubEnv("ANTHROPIC_API_KEY", "sk-ant-1234567890");

      const env = parseEnv();
      expect(env.ANTHROPIC_API_KEY).toBe("sk-ant-1234567890");
    });

    it("should validate OpenAI API key format", () => {
      vi.stubEnv("OPENAI_API_KEY", "invalid-key");
      expect(() => parseEnv()).toThrow(/sk-/);
    });

    it("should accept valid OpenAI API key", () => {
      vi.stubEnv("OPENAI_API_KEY", "sk-1234567890");

      const env = parseEnv();
      expect(env.OPENAI_API_KEY).toBe("sk-1234567890");
    });

    it("should validate Resend API key format", () => {
      vi.stubEnv("RESEND_API_KEY", "invalid-key");
      expect(() => parseEnv()).toThrow(/re_/);
    });

    it("should accept valid Resend API key", () => {
      vi.stubEnv("RESEND_API_KEY", "re_1234567890");

      const env = parseEnv();
      expect(env.RESEND_API_KEY).toBe("re_1234567890");
    });

    it("should apply default for RESEND_FROM_NAME", () => {
      const env = parseEnv();
      expect(env.RESEND_FROM_NAME).toBe("TripSage");
    });

    it("should apply default for AI_GATEWAY_URL", () => {
      const env = parseEnv();
      expect(env.AI_GATEWAY_URL).toBe("https://ai-gateway.vercel.sh/v1");
    });

    it("should apply default for FIRECRAWL_BASE_URL", () => {
      const env = parseEnv();
      expect(env.FIRECRAWL_BASE_URL).toBe("https://api.firecrawl.dev/v2");
    });

    it("should validate required production variables", () => {
      vi.stubEnv("NODE_ENV", "production");
      // Missing SUPABASE_JWT_SECRET

      expect(() => parseEnv()).toThrow("Missing required environment variables");
    });

    it("should validate Upstash Redis URL when token is present in production", () => {
      vi.stubEnv("NODE_ENV", "production");
      vi.stubEnv("SUPABASE_JWT_SECRET", "test-jwt-secret");
      vi.stubEnv("UPSTASH_REDIS_REST_TOKEN", "test-token");
      // Missing UPSTASH_REDIS_REST_URL

      expect(() => parseEnv()).toThrow(/Missing required environment variables/);
    });

    it("should accept Upstash config when both URL and token are present", () => {
      vi.stubEnv("UPSTASH_REDIS_REST_URL", "https://test.upstash.io");
      vi.stubEnv("UPSTASH_REDIS_REST_TOKEN", "test-token");

      const env = parseEnv();
      expect(env.UPSTASH_REDIS_REST_URL).toBe("https://test.upstash.io");
      expect(env.UPSTASH_REDIS_REST_TOKEN).toBe("test-token");
    });

    it("should apply default PORT of 3000", () => {
      const env = parseEnv();
      expect(env.PORT).toBe(3000);
    });

    it("should coerce PORT to number", () => {
      vi.stubEnv("PORT", "8080");

      const env = parseEnv();
      expect(env.PORT).toBe(8080);
    });

    it("should reject negative PORT", () => {
      vi.stubEnv("PORT", "-1");

      expect(() => parseEnv()).toThrow();
    });

    it("should validate email format for RESEND_FROM_EMAIL", () => {
      vi.stubEnv("RESEND_FROM_EMAIL", "invalid-email");

      expect(() => parseEnv()).toThrow();
    });

    it("should accept valid email for RESEND_FROM_EMAIL", () => {
      vi.stubEnv("RESEND_FROM_EMAIL", "noreply@tripsage.com");

      const env = parseEnv();
      expect(env.RESEND_FROM_EMAIL).toBe("noreply@tripsage.com");
    });

    it("should validate URL format for NEXT_PUBLIC_SUPABASE_URL", () => {
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "not-a-url");

      expect(() => parseEnv()).toThrow(/Invalid Supabase URL/);
    });

    it("should apply defaults for development flags", () => {
      const env = parseEnv();
      expect(env.ANALYZE).toBe(false);
      expect(env.DEBUG).toBe(false);
    });

    it("should coerce boolean strings for ANALYZE and DEBUG", () => {
      vi.stubEnv("ANALYZE", "true");
      vi.stubEnv("DEBUG", "1");

      const env = parseEnv();
      expect(env.ANALYZE).toBe(true);
      expect(env.DEBUG).toBe(true);
    });
  });

  describe("parseClientEnv", () => {
    it("should parse and validate client environment successfully", () => {
      const env = parseClientEnv();
      expect(env).toBeDefined();
      expect(env.NEXT_PUBLIC_SUPABASE_URL).toBe("https://test.supabase.co");
      expect(env.NEXT_PUBLIC_SUPABASE_ANON_KEY).toBe("test-anon-key");
      expect(env.NEXT_PUBLIC_APP_NAME).toBe("TripSage");
    });

    it("should only include NEXT_PUBLIC_ variables", () => {
      vi.stubEnv("SECRET_KEY", "secret");
      vi.stubEnv("NEXT_PUBLIC_TEST", "public");

      const env = parseClientEnv();
      expect(env).not.toHaveProperty("SECRET_KEY");
    });

    it("should throw on missing required variables in production", () => {
      vi.stubEnv("NODE_ENV", "production");
      // Clear required vars
      Reflect.deleteProperty(process.env, "NEXT_PUBLIC_SUPABASE_URL");
      Reflect.deleteProperty(process.env, "NEXT_PUBLIC_SUPABASE_ANON_KEY");

      expect(() => parseClientEnv()).toThrow("Client environment validation failed");
    });

    it("should return defaults in development when validation fails", () => {
      vi.stubEnv("NODE_ENV", "development");
      // Clear required vars
      Reflect.deleteProperty(process.env, "NEXT_PUBLIC_SUPABASE_URL");
      Reflect.deleteProperty(process.env, "NEXT_PUBLIC_SUPABASE_ANON_KEY");

      const env = parseClientEnv();
      expect(env.NEXT_PUBLIC_APP_NAME).toBe("TripSage");
      expect(env.NEXT_PUBLIC_SUPABASE_ANON_KEY).toBe("");
      expect(env.NEXT_PUBLIC_SUPABASE_URL).toBe("");
    });

    it("should apply default for NEXT_PUBLIC_APP_NAME", () => {
      const env = parseClientEnv();
      expect(env.NEXT_PUBLIC_APP_NAME).toBe("TripSage");
    });

    it("should validate URL format for NEXT_PUBLIC_SUPABASE_URL", () => {
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "not-a-url");

      expect(() => parseClientEnv()).toThrow();
    });

    it("should require minimum length for NEXT_PUBLIC_SUPABASE_ANON_KEY", () => {
      vi.stubEnv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "");

      expect(() => parseClientEnv()).toThrow();
    });

    it("should accept optional NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY", () => {
      vi.stubEnv("NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY", "test-browser-key");

      const env = parseClientEnv();
      expect(env.NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_API_KEY).toBe("test-browser-key");
    });

    it("should accept optional NEXT_PUBLIC_SITE_URL with URL validation", () => {
      vi.stubEnv("NEXT_PUBLIC_SITE_URL", "https://tripsage.com");

      const env = parseClientEnv();
      expect(env.NEXT_PUBLIC_SITE_URL).toBe("https://tripsage.com");
    });

    it("should reject invalid URL for NEXT_PUBLIC_SITE_URL", () => {
      vi.stubEnv("NEXT_PUBLIC_SITE_URL", "not-a-url");

      expect(() => parseClientEnv()).toThrow();
    });
  });

  describe("performance", () => {
    it("should parse environment in less than 10ms", () => {
      const start = performance.now();
      parseEnv();
      const end = performance.now();
      expect(end - start).toBeLessThan(10);
    });

    it("should parse client environment in less than 5ms", () => {
      const start = performance.now();
      parseClientEnv();
      const end = performance.now();
      expect(end - start).toBeLessThan(5);
    });
  });

  describe("error messages", () => {
    it("should provide detailed error messages on validation failure", () => {
      vi.stubEnv("STRIPE_SECRET_KEY", "invalid");

      try {
        parseEnv();
        expect.fail("Should have thrown");
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
        expect((error as Error).message).toContain("Environment validation failed");
        expect((error as Error).message).toContain("STRIPE_SECRET_KEY");
      }
    });

    it("should include documentation link in error message", () => {
      vi.stubEnv("NODE_ENV", "invalid");

      try {
        parseEnv();
        expect.fail("Should have thrown");
      } catch (error) {
        expect(error).toBeInstanceOf(Error);
        expect((error as Error).message).toContain(
          "https://docs.tripsage.com/env-setup"
        );
      }
    });
  });
});
