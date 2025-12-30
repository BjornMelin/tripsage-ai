/**
 * @fileoverview Server-only env helpers for small flags and optional integrations.
 *
 * Keep this module intentionally lightweight and focused. It exists to:
 * - centralize direct `process.env` reads to `src/lib/env/**` (repo exception)
 * - provide minimal validation/normalization for feature flags and optional keys
 */

import "server-only";

import { z } from "zod";

function normalizeOptionalEnvVar(value: string | undefined): string | undefined {
  if (value === undefined) return undefined;
  const trimmed = value.trim();
  if (!trimmed || trimmed.toLowerCase() === "undefined") return undefined;
  return trimmed;
}

const mem0ApiKeySchema = z.string().min(20, {
  error: "MEM0_API_KEY must be at least 20 characters when configured",
});

export function getMem0ApiKey(): string | undefined {
  const raw = normalizeOptionalEnvVar(process.env.MEM0_API_KEY);
  if (!raw) return undefined;
  return mem0ApiKeySchema.parse(raw);
}

export function getBotIdEnableCsv(): string {
  return normalizeOptionalEnvVar(process.env.BOTID_ENABLE) ?? "production,preview";
}

export function getIdempotencyFailOpenDefault(): boolean {
  return normalizeOptionalEnvVar(process.env.IDEMPOTENCY_FAIL_OPEN) !== "false";
}

export function isTelemetrySilent(): boolean {
  return normalizeOptionalEnvVar(process.env.TELEMETRY_SILENT) === "1";
}

export function isVercelRuntime(): boolean {
  return normalizeOptionalEnvVar(process.env.VERCEL) === "1";
}

export function isTrustProxyEnabled(): boolean {
  return normalizeOptionalEnvVar(process.env.TRUST_PROXY) === "true";
}
