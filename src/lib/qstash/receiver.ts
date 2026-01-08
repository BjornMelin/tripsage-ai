/**
 * @fileoverview QStash Receiver utilities for signature verification.
 */

import "server-only";

import { createHash } from "node:crypto";
import { Receiver } from "@upstash/qstash";
import type { NextResponse } from "next/server";
import type { $ZodIssue } from "zod/v4/core";
import { errorResponse } from "@/lib/api/route-helpers";
import { getServerEnvVar, getServerEnvVarWithFallback } from "@/lib/env/server";
import { PayloadTooLargeError, readRequestBodyBytesWithLimit } from "@/lib/http/body";
import { getRedis } from "@/lib/redis";
import { emitOperationalAlertOncePerWindow } from "@/lib/telemetry/degraded-mode";
import { createServerLogger } from "@/lib/telemetry/logger";
import {
  QSTASH_MESSAGE_ID_HEADER,
  QSTASH_NONRETRYABLE_ERROR_HEADER,
  QSTASH_RETRIED_HEADER,
  QSTASH_SIGNATURE_HEADER,
} from "./config";

const DEFAULT_CLOCK_TOLERANCE_SECONDS = 30;
const DEFAULT_MAX_BODY_BYTES = 64 * 1024;
const DEFAULT_MESSAGE_ID_TTL_SECONDS = 60 * 60 * 24; // 24h
// Keep this shorter than the QStash retry backoff window (initial retries are
// seconds to minutes apart) so a crashed worker doesn't push messages to the
// DLQ purely due to a stale in-flight lock.
const DEFAULT_MESSAGE_LOCK_TTL_SECONDS = 60 * 4; // 4m
const DEFAULT_KEY_ROTATION_ALERT_WINDOW_MS = 6 * 60 * 60 * 1000; // 6h
const logger = createServerLogger("qstash.receiver");

export type QstashVerifyFailureReason =
  | "body_read_error"
  | "invalid_signature"
  | "missing_signature"
  | "payload_too_large";

export type VerifyQstashRequestResult =
  | {
      ok: true;
      body: string;
    }
  | {
      ok: false;
      reason: QstashVerifyFailureReason;
      response: NextResponse;
    };

export interface QstashRequestMeta {
  /** Message identifier (stable across retries for the same message). */
  messageId: string;
  /** Number of retries already performed (0 for first attempt). */
  retried: number;
}

/**
 * Parse QStash metadata headers.
 *
 * Per Upstash docs, `Upstash-Message-Id` is stable across retries and should be
 * used for idempotency, and `Upstash-Retried` indicates how many retries have already
 * happened.
 */
export function getQstashRequestMeta(req: Request): QstashRequestMeta | null {
  const messageId = req.headers.get(QSTASH_MESSAGE_ID_HEADER);
  if (!messageId) return null;

  const retriedRaw = req.headers.get(QSTASH_RETRIED_HEADER);
  let retried = Number.parseInt(retriedRaw ?? "", 10);
  if (!Number.isFinite(retried) || retried < 0) retried = 0;

  return { messageId, retried };
}

/**
 * Build a response that tells QStash to stop retrying and forward the message to the DLQ.
 *
 * QStash requires HTTP 489 + `Upstash-NonRetryable-Error: true`.
 */
export function qstashNonRetryableErrorResponse({
  err,
  error,
  extras,
  issues,
  reason,
}: {
  error: string;
  reason: string;
  err?: unknown;
  issues?: $ZodIssue[];
  extras?: Record<string, unknown>;
}): NextResponse {
  return errorResponse({
    err,
    error,
    extras,
    headers: {
      [QSTASH_NONRETRYABLE_ERROR_HEADER]: "true",
    },
    issues,
    reason,
    status: 489,
  });
}

/**
 * The callbacks `commitProcessed` and `release` perform Redis writes and may reject.
 * Callers should await and handle errors from these functions.
 */
export type QstashIdempotencyResult =
  | {
      ok: true;
      meta: QstashRequestMeta;
      outcome: "process";
      commitProcessed: () => Promise<void>;
      release: () => Promise<void>;
    }
  | { ok: true; meta: QstashRequestMeta; outcome: "duplicate" }
  | { ok: false; response: NextResponse };

/**
 * Enforce idempotency for a QStash-delivered request via `Upstash-Message-Id`.
 *
 * The marker is stored in Upstash Redis with a TTL and `NX` to ensure the same message
 * (including retries) is only processed once.
 */
export async function enforceQstashMessageIdempotency(
  req: Request,
  options: { lockTtlSeconds?: number; processedTtlSeconds?: number } = {}
): Promise<QstashIdempotencyResult> {
  const meta = getQstashRequestMeta(req);
  if (!meta) {
    return {
      ok: false,
      response: qstashNonRetryableErrorResponse({
        error: "invalid_request",
        reason: "Missing Upstash message id",
      }),
    };
  }

  const redis = getRedis();
  if (!redis) {
    return {
      ok: false,
      response: errorResponse({
        error: "service_unavailable",
        reason: "Idempotency service unavailable",
        status: 503,
      }),
    };
  }

  const key = `qstash:message:${meta.messageId}`;
  const lockTtlSeconds = options.lockTtlSeconds ?? DEFAULT_MESSAGE_LOCK_TTL_SECONDS;
  const processedTtlSeconds =
    options.processedTtlSeconds ?? DEFAULT_MESSAGE_ID_TTL_SECONDS;

  let acquired: string | null;
  try {
    acquired = await redis.set(key, "processing", {
      ex: lockTtlSeconds,
      nx: true,
    });
  } catch (error) {
    logger.error("qstash_idempotency_set_failed", {
      error,
      key,
      lockTtlSeconds,
      messageId: meta.messageId,
      retried: meta.retried,
    });
    return {
      ok: false,
      response: errorResponse({
        err: error,
        error: "service_unavailable",
        reason: "Idempotency check failed",
        status: 503,
      }),
    };
  }
  if (acquired === "OK") {
    return {
      commitProcessed: async () => {
        await redis.set(key, "done", { ex: processedTtlSeconds });
      },
      meta,
      ok: true,
      outcome: "process",
      release: async () => {
        await redis.del(key);
      },
    };
  }

  let state: string | null;
  try {
    state = await redis.get<string>(key);
  } catch (error) {
    logger.error("qstash_idempotency_get_failed", {
      error,
      key,
      messageId: meta.messageId,
      retried: meta.retried,
    });
    return {
      ok: false,
      response: errorResponse({
        err: error,
        error: "service_unavailable",
        reason: "Idempotency check failed",
        status: 503,
      }),
    };
  }
  if (state === "done") {
    return { meta, ok: true, outcome: "duplicate" };
  }

  // Another worker is currently processing this message; return non-2xx to trigger retry.
  return {
    ok: false,
    response: errorResponse({
      error: "in_progress",
      reason:
        "Message is currently being processed by another worker (or lock is stale)",
      status: 409,
    }),
  };
}

/**
 * Create a QStash Receiver for signature verification.
 *
 * Uses `QSTASH_CURRENT_SIGNING_KEY` and `QSTASH_NEXT_SIGNING_KEY` (fallback to current).
 * Emits an operational alert when the next signing key is missing/empty, which can
 * cause issues during key rotation.
 */
export function getQstashReceiver(): Receiver {
  const current = getServerEnvVar("QSTASH_CURRENT_SIGNING_KEY");
  if (!current) {
    throw new Error("QSTASH_CURRENT_SIGNING_KEY is not configured");
  }

  const next = getServerEnvVarWithFallback("QSTASH_NEXT_SIGNING_KEY", "");
  if (!next) {
    emitOperationalAlertOncePerWindow({
      attributes: {
        "alert.category": "config_drift",
        "config.current_key_set": true,
        "config.next_key_set": false,
        "docs.rotation_url": "https://upstash.com/docs/qstash/howto/roll-signing-keys",
        "docs.url": "https://upstash.com/docs/qstash/howto/signature",
      },
      event: "qstash.next_signing_key_missing",
      severity: "warning",
      windowMs: DEFAULT_KEY_ROTATION_ALERT_WINDOW_MS,
    });
  }

  return new Receiver({
    currentSigningKey: current,
    nextSigningKey: next || current,
  });
}

/**
 * Verify that a request originated from QStash, and return the raw body string.
 *
 * Reads the request body exactly once. Callers should parse JSON from `body`.
 */
export async function verifyQstashRequest(
  req: Request,
  receiver: Receiver,
  options: { maxBytes?: number } = {}
): Promise<VerifyQstashRequestResult> {
  const { maxBytes = DEFAULT_MAX_BODY_BYTES } = options;
  const signature = req.headers.get(QSTASH_SIGNATURE_HEADER);
  if (!signature) {
    return {
      ok: false,
      reason: "missing_signature",
      response: errorResponse({
        error: "unauthorized",
        reason: "Missing Upstash signature",
        status: 401,
      }),
    };
  }

  let body: string;
  try {
    const bytes = await readRequestBodyBytesWithLimit(req, maxBytes);
    body = new TextDecoder().decode(bytes);
  } catch (error) {
    if (error instanceof PayloadTooLargeError) {
      return {
        ok: false,
        reason: "payload_too_large",
        response: qstashNonRetryableErrorResponse({
          error: "payload_too_large",
          reason: "Request body exceeds limit",
        }),
      };
    }
    return {
      ok: false,
      reason: "body_read_error",
      response: qstashNonRetryableErrorResponse({
        err: error,
        error: "bad_request",
        reason: "Failed to read request body",
      }),
    };
  }

  let valid = false;
  try {
    valid = await receiver.verify({
      body,
      clockTolerance: DEFAULT_CLOCK_TOLERANCE_SECONDS,
      signature,
      url: req.url,
    });
  } catch (err) {
    const signatureHash = createHash("sha256")
      .update(signature)
      .digest("hex")
      .slice(0, 8);
    const pathname = new URL(req.url).pathname;
    logger.error("QStash signature verification failed", {
      error: err instanceof Error ? err.message : String(err),
      path: pathname,
      signatureHash,
    });
    valid = false;
  }

  if (!valid) {
    return {
      ok: false,
      reason: "invalid_signature",
      response: errorResponse({
        error: "unauthorized",
        reason: "Invalid Upstash signature",
        status: 401,
      }),
    };
  }

  return { body, ok: true };
}
