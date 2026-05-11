#!/usr/bin/env node

/**
 * @fileoverview Feature-aware production environment contract checker.
 */

const PROVIDER_KEYS = [
  "AI_GATEWAY_API_KEY",
  "OPENAI_API_KEY",
  "OPENROUTER_API_KEY",
  "ANTHROPIC_API_KEY",
  "XAI_API_KEY",
];
const ORIGIN_KEYS = [
  "APP_BASE_URL",
  "NEXT_PUBLIC_SITE_URL",
  "NEXT_PUBLIC_BASE_URL",
  "NEXT_PUBLIC_APP_URL",
];
const URL_KEYS = ["NEXT_PUBLIC_SUPABASE_URL", "UPSTASH_REDIS_REST_URL"];

function readArg(name, fallback) {
  const index = process.argv.indexOf(name);
  if (index === -1) return fallback;
  const value = process.argv[index + 1];
  if (!value || value.startsWith("--")) return fallback;
  return value;
}

function envValue(name) {
  return process.env[name]?.trim() ?? "";
}

function hasEnv(name) {
  return Boolean(envValue(name));
}

function hasAny(names) {
  return names.some((name) => hasEnv(name));
}

function hasValidUrl(name, { requireHttps }) {
  const value = envValue(name);
  if (!value) return false;

  try {
    const url = new URL(value);
    if (requireHttps) return url.protocol === "https:";
    return url.protocol === "https:" || url.protocol === "http:";
  } catch {
    return false;
  }
}

function invalidUrlNames(names, options) {
  return names.filter((name) => hasEnv(name) && !hasValidUrl(name, options));
}

function makeCheck(name, passed, details = {}) {
  return {
    details,
    name,
    status: passed ? "passed" : "failed",
  };
}

function missing(names) {
  return names.filter((name) => !hasEnv(name));
}

const environment = readArg("--environment", "production");
const isProduction = environment === "production";
const requireHttps = isProduction;
const checks = [];
const invalidOrigins = invalidUrlNames(ORIGIN_KEYS, { requireHttps });

checks.push(
  makeCheck(
    "canonical_origin",
    ORIGIN_KEYS.some((name) => hasValidUrl(name, { requireHttps })) &&
      invalidOrigins.length === 0,
    {
      accepted: ORIGIN_KEYS,
      invalid: invalidOrigins,
      protocol: isProduction ? "https" : "http-or-https",
    }
  )
);

const requiredProduction = [
  "NEXT_PUBLIC_SUPABASE_URL",
  "SUPABASE_SERVICE_ROLE_KEY",
  "SUPABASE_JWT_SECRET",
  "TELEMETRY_HASH_SECRET",
  "HMAC_SECRET",
];

if (isProduction) {
  const absent = missing(requiredProduction);
  checks.push(
    makeCheck("required_production_env", absent.length === 0, {
      missing: absent,
      required: requiredProduction,
    })
  );
}

checks.push(
  makeCheck(
    "qstash_origin_contract",
    !isProduction || hasValidUrl("NEXT_PUBLIC_SITE_URL", { requireHttps: true }),
    {
      reason:
        "QStash enqueue code resolves callback origins from NEXT_PUBLIC_SITE_URL.",
      required: ["NEXT_PUBLIC_SITE_URL"],
      requiredWhen: "production",
    }
  )
);

const invalidUrls = invalidUrlNames(URL_KEYS, { requireHttps });
checks.push(
  makeCheck("service_url_values", invalidUrls.length === 0, {
    invalid: invalidUrls,
    protocol: isProduction ? "https" : "http-or-https",
    variables: URL_KEYS,
  })
);

checks.push(
  makeCheck(
    "supabase_public_key",
    hasAny(["NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "NEXT_PUBLIC_SUPABASE_ANON_KEY"]),
    {
      accepted: [
        "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
        "NEXT_PUBLIC_SUPABASE_ANON_KEY",
      ],
    }
  )
);

const upstashRequired = [
  "UPSTASH_REDIS_REST_URL",
  "UPSTASH_REDIS_REST_TOKEN",
  "QSTASH_TOKEN",
  "QSTASH_CURRENT_SIGNING_KEY",
  "QSTASH_NEXT_SIGNING_KEY",
];
const upstashMissing = missing(upstashRequired);
checks.push(
  makeCheck("upstash_qstash_contract", !isProduction || upstashMissing.length === 0, {
    missing: upstashMissing,
    requiredWhen: "production",
  })
);

const aiDemoEnabled = process.env.ENABLE_AI_DEMO === "true";
checks.push(
  makeCheck("ai_provider_contract", !aiDemoEnabled || hasAny(PROVIDER_KEYS), {
    enabledBy: "ENABLE_AI_DEMO=true",
    providers: PROVIDER_KEYS,
  })
);

const failed = checks.filter((check) => check.status === "failed");
const summary = {
  checks,
  environment,
  status: failed.length === 0 ? "passed" : "failed",
};

console.log(JSON.stringify(summary, null, 2));

if (failed.length > 0) {
  console.error(
    `Production environment validation failed: ${failed
      .map((check) => check.name)
      .join(", ")}`
  );
  process.exit(1);
}
