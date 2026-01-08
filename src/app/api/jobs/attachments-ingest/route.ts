/**
 * @fileoverview QStash job route for attachment ingestion (download + text extraction).
 */

import "server-only";

import { attachmentsIngestJobSchema } from "@schemas/webhooks";
import { tryEnqueueJob } from "@/lib/qstash/client";
import { runQstashJob } from "@/lib/qstash/job-route";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { handleAttachmentsIngest, NonRetryableJobError } from "./_handler";

export async function POST(req: Request): Promise<Response> {
  return await withTelemetrySpan(
    "jobs.attachments-ingest",
    { attributes: { route: "/api/jobs/attachments-ingest" } },
    async (span) =>
      await runQstashJob({
        handle: async (payload) => {
          const supabase = createAdminSupabase();
          return await handleAttachmentsIngest({ supabase, tryEnqueueJob }, payload);
        },
        internalErrorReason: "Attachment ingestion job failed",
        lockTtlSeconds: 60 * 4,
        mapNonRetryableError: (error) =>
          error instanceof NonRetryableJobError
            ? { error: error.errorCode, reason: error.message }
            : null,
        onVerifyFailure: (result, request, span) => {
          const pathname = new URL(request.url).pathname;
          span.addEvent?.("unauthorized_attempt", {
            hasSignature: result.reason !== "missing_signature",
            path: pathname,
            reason: result.reason,
          });
        },
        req,
        schema: attachmentsIngestJobSchema,
        span,
      })
  );
}
