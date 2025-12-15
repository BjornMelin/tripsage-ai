/**
 * @fileoverview Durable job handler for sending collaborator notifications via QStash.
 */

import "server-only";

import { notifyJobSchema } from "@schemas/webhooks";
import { NextResponse } from "next/server";
import { errorResponse, validateSchema } from "@/lib/api/route-helpers";
import { tryReserveKey } from "@/lib/idempotency/redis";
import { sendCollaboratorNotifications } from "@/lib/notifications/collaborators";
import { pushToDLQ } from "@/lib/qstash/dlq";
import { getQstashReceiver, verifyQstashRequest } from "@/lib/qstash/receiver";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/** Max retries configured for QStash (per ADR-0048) */
const MAX_RETRIES = 5;

/**
 * Extract retry attempt information from QStash headers.
 *
 * @param req - Incoming request
 * @return Object with current attempt and max retries
 */
function getRetryInfo(req: Request): { attempt: number; maxRetries: number } {
  const retriedHeader = req.headers.get("Upstash-Retried");
  let retried = parseInt(retriedHeader ?? "", 10);
  if (Number.isNaN(retried) || retried < 0) retried = 0;

  const maxRetriesHeader = req.headers.get("Upstash-Max-Retries");
  let maxRetries = parseInt(maxRetriesHeader ?? "", 10);
  if (Number.isNaN(maxRetries) || maxRetries < 0) maxRetries = MAX_RETRIES;

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

      // Store raw job payload for DLQ on failure
      let jobPayload: unknown = null;

      try {
        let receiver: ReturnType<typeof getQstashReceiver>;
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

        const verified = await verifyQstashRequest(req, receiver);
        if (!verified.ok) {
          try {
            const forwardedFor = req.headers.get("x-forwarded-for");
            const ip =
              forwardedFor?.split(",")[0]?.trim() ??
              req.headers.get("cf-connecting-ip") ??
              undefined;
            span.addEvent("unauthorized_attempt", {
              hasSignature: verified.reason !== "missing_signature",
              ip,
              reason: verified.reason,
              url: req.url,
            });
          } catch (spanError) {
            span.recordException(spanError as Error);
          }
          return verified.response;
        }

        jobPayload = verified.body;

        const json = JSON.parse(verified.body) as unknown;
        jobPayload = json; // Store parsed form for DLQ/validation
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
