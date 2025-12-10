/**
 * @fileoverview Durable job handler for sending collaborator notifications via QStash.
 */

import "server-only";

import { notifyJobSchema } from "@schemas/webhooks";
import { Receiver } from "@upstash/qstash";
import { NextResponse } from "next/server";
import {
  errorResponse,
  unauthorizedResponse,
  validateSchema,
} from "@/lib/api/route-helpers";
import { getServerEnvVar, getServerEnvVarWithFallback } from "@/lib/env/server";
import { tryReserveKey } from "@/lib/idempotency/redis";
import { sendCollaboratorNotifications } from "@/lib/notifications/collaborators";
import { pushToDLQ } from "@/lib/qstash/dlq";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/**
 * Creates a QStash receiver for webhook signature verification.
 *
 * Logs a warning if QSTASH_NEXT_SIGNING_KEY is not set, as this
 * could cause issues during key rotation.
 *
 * @return QStash receiver instance.
 */
function getQstashReceiver(): Receiver {
  const current = getServerEnvVar("QSTASH_CURRENT_SIGNING_KEY") as string;
  const next = getServerEnvVarWithFallback("QSTASH_NEXT_SIGNING_KEY", "");

  if (!next) {
    // Log warning about fallback to help operators during key rotation
    console.warn(
      "[QStash Worker] QSTASH_NEXT_SIGNING_KEY not configured. " +
        "Using current key for both. This is normal for regular operation " +
        "but may cause request failures during key rotation if not addressed. " +
        "See: https://upstash.com/docs/qstash/howto/signature-validation"
    );
  }

  return new Receiver({
    currentSigningKey: current,
    nextSigningKey: next || current,
  });
}

/** Max retries configured for QStash (per ADR-0048) */
const MAX_RETRIES = 5;

/**
 * Extract retry attempt information from QStash headers.
 *
 * @param req - Incoming request
 * @return Object with current attempt and max retries
 */
function getRetryInfo(req: Request): { attempt: number; maxRetries: number } {
  const retried = Number(req.headers.get("Upstash-Retried")) || 0;
  const maxRetries = Number(req.headers.get("Upstash-Max-Retries")) || MAX_RETRIES;
  return { attempt: retried + 1, maxRetries };
}

/**
 * Processes queued collaborator notification jobs with signature verification.
 *
 * @param req - The incoming job request.
 * @return Response indicating success or error.
 */
export async function POST(req: Request) {
  return await withTelemetrySpan(
    "jobs.notify-collaborators",
    { attributes: { route: "/api/jobs/notify-collaborators" } },
    async (span) => {
      const { attempt, maxRetries } = getRetryInfo(req);
      span.setAttribute("qstash.attempt", attempt);
      span.setAttribute("qstash.max_retries", maxRetries);

      // Store parsed job data for DLQ on failure
      let jobPayload: unknown = null;

      try {
        let receiver: Receiver;
        try {
          receiver = getQstashReceiver();
        } catch (error) {
          span.recordException(error as Error);
          return errorResponse({
            err: error,
            error: "configuration_error",
            reason: "QStash signing keys are misconfigured",
            status: 500,
          });
        }

        const sig = req.headers.get("Upstash-Signature");
        const body = await req.clone().text();
        const url = req.url;
        const valid = sig
          ? await receiver.verify({ body, signature: sig, url })
          : false;
        if (!valid) {
          try {
            const forwardedFor = req.headers.get("x-forwarded-for");
            const ip =
              forwardedFor?.split(",")[0]?.trim() ??
              req.headers.get("cf-connecting-ip") ??
              undefined;
            span.addEvent("unauthorized_attempt", {
              hasSignature: Boolean(sig),
              ip,
              reason: "invalid_signature",
              url,
            });
          } catch (spanError) {
            span.recordException(spanError as Error);
          }
          return unauthorizedResponse();
        }

        const json = (await req.json()) as unknown;
        jobPayload = json; // Store for DLQ
        const validation = validateSchema(notifyJobSchema, json);
        if ("error" in validation) {
          return validation.error;
        }
        const { eventKey, payload } = validation.data;
        span.setAttribute("event.key", eventKey);
        span.setAttribute("table", payload.table);
        span.setAttribute("op", payload.type);

        // De-duplicate at worker level as well to avoid double-send on retries
        const unique = await tryReserveKey(`notify:${eventKey}`, 300);
        if (!unique) {
          span.setAttribute("event.duplicate", true);
          return NextResponse.json({ duplicate: true, ok: true });
        }

        const result = await sendCollaboratorNotifications(payload, eventKey);
        return NextResponse.json({ ok: true, ...result });
      } catch (error) {
        span.recordException(error as Error);

        // Check if this is the final retry attempt
        const isFinalAttempt = attempt >= maxRetries;
        span.setAttribute("qstash.final_attempt", isFinalAttempt);

        if (isFinalAttempt) {
          // Push to DLQ on final failure per ADR-0048
          const dlqEntryId = await pushToDLQ(
            "notify-collaborators",
            jobPayload,
            error,
            attempt
          );
          span.setAttribute("qstash.dlq", true);
          span.setAttribute("qstash.dlq_entry_id", dlqEntryId ?? "unavailable");
        }

        return errorResponse({
          err: error,
          error: "internal",
          reason: "Collaborator notification job failed",
          status: 500,
        });
      }
    }
  );
}
