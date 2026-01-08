/**
 * @fileoverview Durable job handler for sending collaborator notifications via QStash.
 */

import "server-only";

import { notifyJobSchema } from "@schemas/webhooks";
import { sendCollaboratorNotifications } from "@/lib/notifications/collaborators";
import { runQstashJob } from "@/lib/qstash/job-route";
import { getTrustedRateLimitIdentifierFromHeaders } from "@/lib/ratelimit/identifier";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { handleNotifyCollaboratorsJob } from "./_handler";

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
    async (span) =>
      await runQstashJob({
        handle: async (payload) =>
          await handleNotifyCollaboratorsJob(
            { sendNotifications: sendCollaboratorNotifications },
            payload
          ),
        internalErrorReason: "Collaborator notification job failed",
        onPayloadValidated: (payload, _meta, span) => {
          span.setAttribute("event.key", payload.eventKey);
          span.setAttribute("table", payload.payload.table);
          span.setAttribute("op", payload.payload.type);
        },
        onVerifyFailure: (result, request, span) => {
          try {
            const ipHash = getTrustedRateLimitIdentifierFromHeaders(request.headers);
            const pathname = new URL(request.url).pathname;
            span.addEvent?.("unauthorized_attempt", {
              hasSignature: result.reason !== "missing_signature",
              ipHash: ipHash === "unknown" ? undefined : ipHash,
              path: pathname,
              reason: result.reason,
            });
          } catch (spanError) {
            span.recordException(spanError as Error);
          }
        },
        req,
        schema: notifyJobSchema,
        span,
      })
  );
}
