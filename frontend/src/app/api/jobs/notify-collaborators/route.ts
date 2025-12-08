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
import { withTelemetrySpan } from "@/lib/telemetry/span";

/**
 * Creates a QStash receiver for webhook signature verification.
 *
 * @return QStash receiver instance or null if not configured.
 */
function getQstashReceiver(): Receiver {
  const current = getServerEnvVar("QSTASH_CURRENT_SIGNING_KEY") as string;
  const next = getServerEnvVarWithFallback(
    "QSTASH_NEXT_SIGNING_KEY",
    current
  ) as string;
  return new Receiver({ currentSigningKey: current, nextSigningKey: next });
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
