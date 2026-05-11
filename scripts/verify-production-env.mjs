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
const SUPABASE_PUBLIC_KEYS = [
  "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
  "NEXT_PUBLIC_SUPABASE_ANON_KEY",
];

const valueValidators = new Map([
  ["AMADEUS_CLIENT_ID", [minLength(10)]],
  ["AMADEUS_CLIENT_SECRET", [minLength(16)]],
  ["AMADEUS_ENV", [oneOf(["production", "test"])]],
  ["HMAC_SECRET", [minLength(32)]],
  ["NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY", [startsWithOneOf(["pk_live_", "pk_test_"])]],
  ["QSTASH_CURRENT_SIGNING_KEY", [minLength(32)]],
  ["QSTASH_NEXT_SIGNING_KEY", [minLength(32)]],
  ["QSTASH_TOKEN", [minLength(20)]],
  ["RESEND_API_KEY", [startsWithOneOf(["re_"])]],
  ["RESEND_FROM_EMAIL", [validEmail()]],
  ["STRIPE_SECRET_KEY", [startsWithOneOf(["sk_live_", "sk_test_"])]],
  ["STRIPE_WEBHOOK_SECRET", [startsWithOneOf(["whsec_"])]],
  ["SUPABASE_JWT_SECRET", [minLength(32)]],
  ["SUPABASE_SERVICE_ROLE_KEY", [minLength(30)]],
  ["TELEMETRY_AI_DEMO_KEY", [minLength(32)]],
  ["TELEMETRY_HASH_SECRET", [minLength(32)]],
  ["UPSTASH_REDIS_REST_TOKEN", [minLength(20)]],
]);

function minLength(length) {
  return (value) =>
    value.length >= length ? null : `must be at least ${length} characters`;
}

function oneOf(values) {
  return (value) =>
    values.includes(value) ? null : `must be one of ${values.join(", ")}`;
}

function startsWithOneOf(prefixes) {
  return (value) =>
    prefixes.some((prefix) => value.startsWith(prefix))
      ? null
      : `must start with ${prefixes.join(" or ")}`;
}

function validEmail() {
  return (value) =>
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) ? null : "must be an email";
}

function isPlaceholderValue(value) {
  const lower = value.toLowerCase();
  return (
    lower.startsWith("your-") ||
    lower.startsWith("your_") ||
    lower.startsWith("changeme") ||
    lower.startsWith("replace-") ||
    lower.startsWith("replace_") ||
    lower.includes("placeholder") ||
    lower.includes("example") ||
    lower.includes("...") ||
    lower === "null" ||
    lower === "undefined" ||
    /^0+$/.test(lower)
  );
}

function readArg(name, fallback) {
  const index = process.argv.indexOf(name);
  if (index === -1) return fallback;
  const value = process.argv[index + 1];
  if (!value || value.startsWith("--")) return fallback;
  return value;
}

function envValue(name) {
  const value = process.env[name]?.trim() ?? "";
  if (!value || value.toLowerCase() === "undefined") return "";
  return value;
}

function hasEnv(name) {
  return Boolean(envValue(name));
}

function hasAny(names) {
  return names.some((name) => hasEnv(name));
}

function hasAll(names) {
  return names.every((name) => hasEnv(name));
}

function hasValidUrl(name, { requireHttps }) {
  const value = envValue(name);
  if (!value) return false;

  try {
    const url = new URL(value);
    const hasValidProtocol = requireHttps
      ? url.protocol === "https:"
      : url.protocol === "https:" || url.protocol === "http:";

    return (
      hasValidProtocol &&
      url.pathname === "/" &&
      url.search === "" &&
      url.hash === "" &&
      url.username === "" &&
      url.password === ""
    );
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

function invalidValues(names) {
  return names.flatMap((name) => {
    const value = envValue(name);
    if (!value) return [];
    if (isPlaceholderValue(value)) {
      return [{ name, reason: "placeholder value is not allowed" }];
    }

    const validators = valueValidators.get(name) ?? [];
    if (validators.length === 0) return [];

    const reason = validators.map((validator) => validator(value)).find(Boolean);
    return reason ? [{ name, reason }] : [];
  });
}

function hasValidAny(names) {
  return names.some((name) => hasEnv(name) && invalidValues([name]).length === 0);
}

function addRequiredGroupCheck(name, names, options = {}) {
  const enabled = options.enabled ?? isProduction;
  const absent = enabled ? missing(names) : [];
  const invalid = enabled ? invalidValues(names) : [];
  checks.push(
    makeCheck(name, !enabled || (absent.length === 0 && invalid.length === 0), {
      enabled,
      enabledBy: options.enabledBy,
      invalid,
      missing: absent,
      required: names,
      requiredWhen: options.requiredWhen ?? "production",
    })
  );
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

addRequiredGroupCheck(
  "supabase_core_contract",
  ["NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_JWT_SECRET"],
  { requiredWhen: "production" }
);

checks.push(
  makeCheck("supabase_public_key", !isProduction || hasValidAny(SUPABASE_PUBLIC_KEYS), {
    accepted: SUPABASE_PUBLIC_KEYS,
    invalid: invalidValues(SUPABASE_PUBLIC_KEYS),
    preferred: "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
    requiredWhen: "production",
  })
);

addRequiredGroupCheck("telemetry_core_contract", ["TELEMETRY_HASH_SECRET"], {
  requiredWhen: "production",
});

addRequiredGroupCheck("webhook_hmac_contract", ["HMAC_SECRET"], {
  requiredWhen: "production",
});

checks.push(
  makeCheck(
    "qstash_origin_contract",
    !isProduction || ORIGIN_KEYS.some((name) => hasValidUrl(name, { requireHttps })),
    {
      accepted: ORIGIN_KEYS,
      preferred: "APP_BASE_URL",
      reason:
        "QStash enqueue code resolves callback origins through the server-origin contract.",
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

const upstashRedisRequired = ["UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"];
addRequiredGroupCheck("upstash_redis_contract", upstashRedisRequired, {
  requiredWhen: "production",
});

const qstashRequired = [
  "QSTASH_TOKEN",
  "QSTASH_CURRENT_SIGNING_KEY",
  "QSTASH_NEXT_SIGNING_KEY",
];
addRequiredGroupCheck("qstash_delivery_contract", qstashRequired, {
  requiredWhen: "production",
});

const stripeRequired = [
  "NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY",
  "STRIPE_SECRET_KEY",
  "STRIPE_WEBHOOK_SECRET",
];
addRequiredGroupCheck("stripe_feature_contract", stripeRequired, {
  enabled: hasAny(stripeRequired),
  enabledBy: "any Stripe key is configured",
  requiredWhen: "feature enabled",
});

const resendRequired = ["RESEND_API_KEY", "RESEND_FROM_EMAIL", "RESEND_FROM_NAME"];
addRequiredGroupCheck("resend_feature_contract", resendRequired, {
  enabled: hasAny(resendRequired),
  enabledBy: "any Resend email variable is configured",
  requiredWhen: "feature enabled",
});

const amadeusRequired = ["AMADEUS_CLIENT_ID", "AMADEUS_CLIENT_SECRET", "AMADEUS_ENV"];
addRequiredGroupCheck("amadeus_feature_contract", amadeusRequired, {
  enabled: hasAny(amadeusRequired),
  enabledBy: "any Amadeus variable is configured",
  requiredWhen: "feature enabled",
});

const legacyUpstashRequired = [
  "UPSTASH_REDIS_REST_URL",
  "UPSTASH_REDIS_REST_TOKEN",
  "QSTASH_TOKEN",
  "QSTASH_CURRENT_SIGNING_KEY",
  "QSTASH_NEXT_SIGNING_KEY",
];
checks.push(
  makeCheck("upstash_qstash_contract", !isProduction || hasAll(legacyUpstashRequired), {
    deprecatedBy: ["upstash_redis_contract", "qstash_delivery_contract"],
    missing: isProduction ? missing(legacyUpstashRequired) : [],
    requiredWhen: "production",
  })
);

const aiDemoEnabled = process.env.ENABLE_AI_DEMO === "true";
addRequiredGroupCheck("ai_demo_telemetry_contract", ["TELEMETRY_AI_DEMO_KEY"], {
  enabled: aiDemoEnabled,
  enabledBy: "ENABLE_AI_DEMO=true",
  requiredWhen: "feature enabled",
});

checks.push(
  makeCheck("ai_provider_contract", !aiDemoEnabled || hasValidAny(PROVIDER_KEYS), {
    enabledBy: "ENABLE_AI_DEMO=true",
    invalid: invalidValues(PROVIDER_KEYS),
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
    `${environment} environment validation failed: ${failed
      .map((check) => check.name)
      .join(", ")}`
  );
  process.exit(1);
}
