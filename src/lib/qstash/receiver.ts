/**
 * @fileoverview QStash Receiver utilities for signature verification.
 *
 * Centralizes creation and verification logic to keep job route handlers
 * consistent and reduce security-critical duplication.
 */

import "server-only";

import { Receiver } from "@upstash/qstash";
import type { NextResponse } from "next/server";
import { errorResponse } from "@/lib/api/route-helpers";
import { getServerEnvVar, getServerEnvVarWithFallback } from "@/lib/env/server";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";
import { createServerLogger } from "@/lib/telemetry/logger";
import { QSTASH_SIGNATURE_HEADER } from "./config";

const DEFAULT_CLOCK_TOLERANCE_SECONDS = 30;
const logger = createServerLogger("qstash.receiver");

export type QstashVerifyFailureReason = "invalid_signature" | "missing_signature";

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
    emitOperationalAlert("qstash.next_signing_key_missing", {
      attributes: {
        "config.current_key_set": true,
        "config.next_key_set": false,
        "docs.url": "https://upstash.com/docs/qstash/howto/signature-validation",
      },
      severity: "warning",
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
  receiver: Receiver
): Promise<VerifyQstashRequestResult> {
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

  const body = await req.text();

  let valid = false;
  try {
    valid = await receiver.verify({
      body,
      clockTolerance: DEFAULT_CLOCK_TOLERANCE_SECONDS,
      signature,
      url: req.url,
    });
  } catch (err) {
    logger.error("QStash signature verification failed", {
      error: err instanceof Error ? err.message : String(err),
      signature,
      url: req.url,
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
