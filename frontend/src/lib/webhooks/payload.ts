/**
 * @fileoverview Webhook payload parsing, verification, and event key generation.
 */

import "server-only";
import { createHash } from "node:crypto";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { verifyRequestHmac } from "@/lib/security/webhook";

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

/** Normalized webhook payload structure for internal use. */
export type WebhookPayload = {
  type: "INSERT" | "UPDATE" | "DELETE";
  table: string;
  schema?: string;
  record: Record<string, unknown> | null;
  oldRecord: Record<string, unknown> | null;
  occurredAt?: string;
};

/**
 * Normalizes raw webhook payload to internal structure.
 *
 * @param raw - The raw webhook payload from external source.
 * @return Normalized webhook payload.
 */
function normalizeWebhookPayload(raw: RawWebhookPayload): WebhookPayload {
  return {
    occurredAt: raw[OCCURRED_AT_KEY],
    oldRecord: raw[OLD_RECORD_KEY] ?? null,
    record: raw.record ?? null,
    schema: raw.schema,
    table: raw.table,
    type: raw.type,
  };
}

/**
 * Parses and verifies a webhook request with HMAC signature.
 *
 * @param req - The incoming webhook request.
 * @return Object with verification status and optional parsed payload.
 */
export async function parseAndVerify(
  req: Request
): Promise<{ ok: boolean; payload?: WebhookPayload }> {
  const secret = getServerEnvVarWithFallback("HMAC_SECRET", "");
  if (!secret || !(await verifyRequestHmac(req, secret))) {
    return { ok: false };
  }
  let raw: RawWebhookPayload;
  try {
    raw = (await req.json()) as RawWebhookPayload;
  } catch {
    return { ok: false };
  }
  const payload = normalizeWebhookPayload(raw);
  if (!payload?.type || !payload?.table) return { ok: false };
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
