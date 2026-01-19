/**
 * @fileoverview Server-only env helpers for feature flags and optional integrations.
 */

import "server-only";

function normalizeOptionalEnvVar(value: string | undefined): string | undefined {
  if (value === undefined) return undefined;
  const trimmed = value.trim();
  if (!trimmed || trimmed.toLowerCase() === "undefined") return undefined;
  return trimmed;
}

/**
 * Standard boolean flag parsing for server env vars.
 *
 * Accepted true values: `"1"` or `"true"`.
 * Accepted false values: `"0"` or `"false"`.
 *
 * Anything else falls back to the provided default.
 */
function parseEnvFlag(value: string | undefined, defaultValue: boolean): boolean {
  const normalized = normalizeOptionalEnvVar(value);
  if (!normalized) return defaultValue;
  const lower = normalized.toLowerCase();
  if (lower === "1" || lower === "true") return true;
  if (lower === "0" || lower === "false") return false;
  return defaultValue;
}

export function getBotIdEnableCsv(): string {
  return normalizeOptionalEnvVar(process.env.BOTID_ENABLE) ?? "production,preview,test";
}

export function getIdempotencyFailOpenDefault(): boolean {
  return parseEnvFlag(process.env.IDEMPOTENCY_FAIL_OPEN, true);
}

export function isTelemetrySilent(): boolean {
  return parseEnvFlag(process.env.TELEMETRY_SILENT, false);
}

export function isVercelRuntime(): boolean {
  return parseEnvFlag(process.env.VERCEL, false);
}

export function isTrustProxyEnabled(): boolean {
  return parseEnvFlag(process.env.TRUST_PROXY, false);
}
