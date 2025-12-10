/**
 * @fileoverview Webhook payload parsing, verification, and event key generation.
 *
 * Implements single-pass body read to avoid redundant request cloning
 * and potential stream exhaustion issues.
 */

import "server-only";
import { createHash } from "node:crypto";
import type { WebhookPayload } from "@schemas/webhooks";
import { webhookPayloadSchema } from "@schemas/webhooks";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { computeHmacSha256Hex, timingSafeEqualHex } from "@/lib/security/webhook";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";
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

function recordVerificationFailure(reason: string): void {
  addEventToActiveSpan("webhook_verification_failed", { reason });
  emitOperationalAlert("webhook.verification_failed", {
    attributes: { reason },
  });
}

/**
 * Parses and verifies a webhook request with HMAC signature.
 *
 * Uses single-pass body read to avoid redundant request cloning:
 * 1. Read body as raw text once
 * 2. Verify HMAC on raw text
 * 3. Parse JSON from the same text
 *
 * @param req - The incoming webhook request.
 * @return Object with verification status and optional parsed payload.
 */
export async function parseAndVerify(
  req: Request
): Promise<{ ok: boolean; payload?: WebhookPayload }> {
  const secret = getServerEnvVarWithFallback("HMAC_SECRET", "");
  if (!secret) {
    recordVerificationFailure("missing_secret_env");
    return { ok: false };
  }

  // Get signature from header
  const sig = req.headers.get("x-signature-hmac");
  if (!sig) {
    recordVerificationFailure("missing_signature");
    return { ok: false };
  }

  // Single-pass body read: read as text once, verify, then parse
  let rawBody: string;
  try {
    rawBody = await req.text();
  } catch {
    recordVerificationFailure("body_read_error");
    return { ok: false };
  }

  // Verify HMAC on raw text
  const expected = computeHmacSha256Hex(rawBody, secret);
  if (!timingSafeEqualHex(expected, sig)) {
    recordVerificationFailure("invalid_signature");
    return { ok: false };
  }

  // Parse JSON from the already-read text
  let raw: RawWebhookPayload;
  try {
    raw = JSON.parse(rawBody) as RawWebhookPayload;
  } catch {
    recordVerificationFailure("invalid_json");
    return { ok: false };
  }

  // Normalize and validate payload
  let payload: WebhookPayload;
  try {
    payload = normalizeWebhookPayload(raw);
  } catch {
    recordVerificationFailure("invalid_payload_shape");
    return { ok: false };
  }

  if (!payload?.type || !payload?.table) {
    recordVerificationFailure("invalid_payload_shape");
    return { ok: false };
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
