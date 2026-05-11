/** @vitest-environment node */

import { spawnSync } from "node:child_process";
import path from "node:path";
import { describe, expect, it } from "vitest";

type EnvCheck = {
  details: Record<string, unknown>;
  name: string;
  status: "failed" | "passed";
};

type EnvSummary = {
  checks: EnvCheck[];
  environment: string;
  status: "failed" | "passed";
};

const scriptPath = path.join(process.cwd(), "scripts/verify-production-env.mjs");
const longSecret = "a".repeat(32);
const legacyAnonJwt =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiJ9.signature";
const validRedisUrl = "https://upstash-valid.test";

const productionEnv = {
  APP_BASE_URL: "https://app.example.com",
  HMAC_SECRET: longSecret,
  NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "sb_publishable_test",
  NEXT_PUBLIC_SUPABASE_URL: "https://test.supabase.co",
  NODE_ENV: "production",
  QSTASH_CURRENT_SIGNING_KEY: longSecret,
  QSTASH_NEXT_SIGNING_KEY: longSecret,
  QSTASH_TOKEN: longSecret,
  SUPABASE_JWT_SECRET: longSecret,
  SUPABASE_SERVICE_ROLE_KEY: longSecret,
  TELEMETRY_HASH_SECRET: longSecret,
  UPSTASH_REDIS_REST_TOKEN: longSecret,
  UPSTASH_REDIS_REST_URL: validRedisUrl,
} satisfies NodeJS.ProcessEnv;

function runVerifier(overrides: Partial<NodeJS.ProcessEnv> = {}) {
  const env: NodeJS.ProcessEnv = { ...productionEnv, ...overrides };
  for (const [key, value] of Object.entries(env)) {
    if (value === undefined) {
      Reflect.deleteProperty(env, key);
    }
  }

  const result = spawnSync(
    process.execPath,
    [scriptPath, "--environment", "production"],
    {
      encoding: "utf8",
      env,
    }
  );

  return {
    ...result,
    summary: JSON.parse(result.stdout) as EnvSummary,
  };
}

function check(summary: EnvSummary, name: string): EnvCheck {
  const found = summary.checks.find((item) => item.name === name);
  if (!found) {
    throw new Error(`Missing env check: ${name}`);
  }
  return found;
}

describe("verify-production-env", () => {
  it("passes minimal production env while disabled optional feature groups stay disabled", () => {
    const result = runVerifier();

    expect(result.status).toBe(0);
    expect(result.summary.status).toBe("passed");
    expect(check(result.summary, "qstash_origin_contract").status).toBe("passed");
    expect(check(result.summary, "stripe_feature_contract").details.enabled).toBe(
      false
    );
    expect(check(result.summary, "resend_feature_contract").details.enabled).toBe(
      false
    );
    expect(check(result.summary, "amadeus_feature_contract").details.enabled).toBe(
      false
    );
  });

  it("fails partial optional feature groups when any Stripe variable enables payments", () => {
    const result = runVerifier({ STRIPE_SECRET_KEY: "sk_test" });

    expect(result.status).toBe(1);
    expect(result.summary.status).toBe("failed");
    expect(check(result.summary, "stripe_feature_contract")).toMatchObject({
      status: "failed",
    });
  });

  it("fails QStash when no server-origin variable is configured", () => {
    const result = runVerifier({
      APP_BASE_URL: undefined,
      NEXT_PUBLIC_APP_URL: undefined,
      NEXT_PUBLIC_BASE_URL: undefined,
      NEXT_PUBLIC_SITE_URL: undefined,
    });

    expect(result.status).toBe(1);
    expect(result.summary.status).toBe("failed");
    expect(check(result.summary, "qstash_origin_contract")).toMatchObject({
      status: "failed",
    });
  });

  it("fails values that runtime env schema would reject", () => {
    const result = runVerifier({
      HMAC_SECRET: "short",
      QSTASH_CURRENT_SIGNING_KEY: "short",
      QSTASH_NEXT_SIGNING_KEY: "short",
      QSTASH_TOKEN: "short",
      SUPABASE_JWT_SECRET: "short",
      SUPABASE_SERVICE_ROLE_KEY: "short",
      TELEMETRY_HASH_SECRET: "short",
    });

    expect(result.status).toBe(1);
    expect(check(result.summary, "supabase_core_contract").details.invalid).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ name: "SUPABASE_SERVICE_ROLE_KEY" }),
        expect.objectContaining({ name: "SUPABASE_JWT_SECRET" }),
      ])
    );
    expect(check(result.summary, "webhook_hmac_contract").details.invalid).toEqual(
      expect.arrayContaining([expect.objectContaining({ name: "HMAC_SECRET" })])
    );
    expect(check(result.summary, "telemetry_core_contract").details.invalid).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ name: "TELEMETRY_HASH_SECRET" }),
      ])
    );
    expect(check(result.summary, "qstash_delivery_contract").details.invalid).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ name: "QSTASH_TOKEN" }),
        expect.objectContaining({ name: "QSTASH_CURRENT_SIGNING_KEY" }),
        expect.objectContaining({ name: "QSTASH_NEXT_SIGNING_KEY" }),
      ])
    );
  });

  it("treats literal undefined public keys as absent", () => {
    const result = runVerifier({
      NEXT_PUBLIC_SUPABASE_ANON_KEY: undefined,
      NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "undefined",
    });

    expect(result.status).toBe(1);
    expect(check(result.summary, "supabase_public_key")).toMatchObject({
      status: "failed",
    });
  });

  it("rejects placeholder public and feature-enabling keys", () => {
    const result = runVerifier({
      AI_GATEWAY_API_KEY: "placeholder",
      ENABLE_AI_DEMO: "true",
      NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "sb_publishable_...",
      TELEMETRY_AI_DEMO_KEY: "telemetry_ai_demo_key_0123456789abc",
      UPSTASH_REDIS_REST_TOKEN: "placeholder",
    });

    expect(result.status).toBe(1);
    expect(check(result.summary, "supabase_public_key").details.invalid).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ name: "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY" }),
      ])
    );
    expect(check(result.summary, "upstash_redis_contract").details.invalid).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ name: "UPSTASH_REDIS_REST_TOKEN" }),
      ])
    );
    expect(check(result.summary, "ai_provider_contract").details.invalid).toEqual(
      expect.arrayContaining([expect.objectContaining({ name: "AI_GATEWAY_API_KEY" })])
    );
  });

  it("fails malformed publishable key even when a legacy fallback is configured", () => {
    const result = runVerifier({
      NEXT_PUBLIC_SUPABASE_ANON_KEY: legacyAnonJwt,
      NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "not-a-publishable-key",
    });

    expect(result.status).toBe(1);
    expect(check(result.summary, "supabase_public_key")).toMatchObject({
      details: {
        active: "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
        invalid: [
          expect.objectContaining({
            name: "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
          }),
        ],
      },
      status: "failed",
    });
  });

  it("accepts a legacy anon JWT only when publishable key is absent", () => {
    const result = runVerifier({
      NEXT_PUBLIC_SUPABASE_ANON_KEY: legacyAnonJwt,
      NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: undefined,
    });

    expect(result.status).toBe(0);
    expect(check(result.summary, "supabase_public_key")).toMatchObject({
      details: {
        active: "NEXT_PUBLIC_SUPABASE_ANON_KEY",
      },
      status: "passed",
    });
  });

  it("requires telemetry auth and one provider when the AI demo is enabled", () => {
    const result = runVerifier({ ENABLE_AI_DEMO: "true" });

    expect(result.status).toBe(1);
    expect(check(result.summary, "ai_demo_telemetry_contract")).toMatchObject({
      status: "failed",
    });
    expect(check(result.summary, "ai_provider_contract")).toMatchObject({
      status: "failed",
    });
  });
});
