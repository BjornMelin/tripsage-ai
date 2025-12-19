/**
 * @fileoverview Webhook payload parsing and HMAC verification with bounded, single-pass body reads.
 */

import "server-only";
import { createHash } from "node:crypto";
import type { WebhookPayload } from "@schemas/webhooks";
import { webhookPayloadSchema } from "@schemas/webhooks";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { PayloadTooLargeError, readRequestBodyBytesWithLimit } from "@/lib/http/body";
import { computeHmacSha256Hex, timingSafeEqualHex } from "@/lib/security/webhook";
import { emitOperationalAlertOncePerWindow } from "@/lib/telemetry/degraded-mode";
import { sanitizePathnameForTelemetry } from "@/lib/telemetry/route-key";
import { addEventToActiveSpan } from "@/lib/telemetry/span";

const OLD_RECORD_KEY = "old_record" as const;
const OCCURRED_AT_KEY = "occurred_at" as const;

/** Raw webhook payload structure from external source. */
type RawWebhookPayload = {
  record: Record<string, unknown> | null;
  schema?: string;
  table: string;
  type: "INSERT" | "UPDATE" | "DELETE";
} & {
  [OLD_RECORD_KEY]?: Record<string, unknown> | null;
  [OCCURRED_AT_KEY]?: string;
};

// Re-export type from schemas
export type { WebhookPayload };

/**
 * Normalizes raw webhook payload to internal structure.
 *
 * @param raw - The raw webhook payload from external source.
 * @return Normalized webhook payload (validated via Zod schema).
 */
function normalizeWebhookPayload(raw: RawWebhookPayload): WebhookPayload {
  const normalized = {
    occurredAt: raw[OCCURRED_AT_KEY],
    oldRecord: raw[OLD_RECORD_KEY] ?? null,
    record: raw.record ?? null,
    schema: raw.schema,
    table: raw.table,
    type: raw.type,
  };
  // Validate using Zod schema
  return webhookPayloadSchema.parse(normalized);
}

function recordVerificationFailure(req: Request, reason: string): void {
  addEventToActiveSpan("webhook_verification_failed", { reason });

  // Safely parse URL to avoid exceptions on malformed request URLs
  let pathname = "/unknown";
  try {
    pathname = new URL(req.url).pathname;
  } catch {
    // Fall back to unknown if URL parsing fails
  }

  emitOperationalAlertOncePerWindow({
    attributes: {
      reason,
      route: sanitizePathnameForTelemetry(pathname),
    },
    event: "webhook.verification_failed",
    severity: "warning",
    windowMs: 60_000,
  });
}

export type ParseAndVerifyFailureReason =
  | "body_read_error"
  | "invalid_json"
  | "invalid_payload_shape"
  | "invalid_signature"
  | "missing_secret_env"
  | "missing_signature"
  | "payload_too_large";

export type ParseAndVerifyResult =
  | { ok: true; payload: WebhookPayload }
  | { ok: false; reason: ParseAndVerifyFailureReason };

/**
 * Parses and verifies a webhook request with HMAC signature.
 *
 * Uses a bounded single-pass body read:
 * 1. Read body bytes once (enforcing a max size)
 * 2. Verify HMAC on raw bytes
 * 3. Parse JSON from the same bytes
 *
 * @param req - The incoming webhook request.
 * @param options - Optional body size limit configuration.
 * @return Object with verification status and optional parsed payload.
 */
export async function parseAndVerify(
  req: Request,
  options: { maxBytes?: number } = {}
): Promise<ParseAndVerifyResult> {
  const { maxBytes = 65536 } = options;
  const secret = getServerEnvVarWithFallback("HMAC_SECRET", "");
  if (!secret) {
    recordVerificationFailure(req, "missing_secret_env");
    return { ok: false, reason: "missing_secret_env" };
  }

  // Get signature from header
  const sig = req.headers.get("x-signature-hmac");
  if (!sig) {
    recordVerificationFailure(req, "missing_signature");
    return { ok: false, reason: "missing_signature" };
  }

  let rawBytes: Uint8Array;
  try {
    rawBytes = await readRequestBodyBytesWithLimit(req, maxBytes);
  } catch (error) {
    if (error instanceof PayloadTooLargeError) {
      recordVerificationFailure(req, "payload_too_large");
      return { ok: false, reason: "payload_too_large" };
    }
    recordVerificationFailure(req, "body_read_error");
    return { ok: false, reason: "body_read_error" };
  }

  // Verify HMAC on raw bytes
  const expected = computeHmacSha256Hex(rawBytes, secret);
  if (!timingSafeEqualHex(expected, sig)) {
    recordVerificationFailure(req, "invalid_signature");
    return { ok: false, reason: "invalid_signature" };
  }

  const rawBody = Buffer.from(rawBytes).toString("utf8");

  // Parse JSON from the already-read body
  let raw: RawWebhookPayload;
  try {
    raw = JSON.parse(rawBody) as RawWebhookPayload;
  } catch {
    recordVerificationFailure(req, "invalid_json");
    return { ok: false, reason: "invalid_json" };
  }

  // Normalize and validate payload
  let payload: WebhookPayload;
  try {
    payload = normalizeWebhookPayload(raw);
  } catch {
    recordVerificationFailure(req, "invalid_payload_shape");
    return { ok: false, reason: "invalid_payload_shape" };
  }

  return { ok: true, payload };
}

/**
 * Builds a unique event key for webhook deduplication.
 *
 * @param payload - The webhook payload.
 * @return Unique event identifier string.
 */
export function buildEventKey(payload: WebhookPayload): string {
  const base = `${payload.table}:${payload.type}:${payload.occurredAt ?? ""}`;
  const id = (payload.record as { id?: string })?.id;
  if (id) return `${base}:${id}`;
  const rec = JSON.stringify(payload.record ?? payload.oldRecord ?? {});
  const h = createHash("sha256").update(rec).digest("hex").slice(0, 16);
  return `${base}:${h}`;
}
