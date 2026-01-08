/**
 * @fileoverview QStash job route for RAG document indexing.
 */

import "server-only";

import { ragIndexJobSchema } from "@schemas/webhooks";
import { runQstashJob } from "@/lib/qstash/job-route";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { handleRagIndexJob } from "./_handler";

const MAX_RAG_JOB_BODY_BYTES = 512 * 1024;

class NonRetryableRagIndexError extends Error {
  public readonly errorCode: string;

  constructor(errorCode: string, message: string) {
    super(message);
    this.errorCode = errorCode;
    this.name = "NonRetryableRagIndexError";
  }
}

function isNonRetryableRagIndexFailure(reason: string): boolean {
  return reason.startsWith("rag_limit:");
}

export async function POST(req: Request): Promise<Response> {
  return await withTelemetrySpan(
    "jobs.rag-index",
    { attributes: { route: "/api/jobs/rag-index" } },
    async (span) =>
      await runQstashJob({
        handle: async (payload) => {
          const supabase = createAdminSupabase();
          const result = await handleRagIndexJob({ supabase }, payload);

          if (!result.success) {
            const uniqueErrors = Array.from(
              new Set(result.failed.map((doc) => doc.error))
            );
            if (
              uniqueErrors.length > 0 &&
              uniqueErrors.every(isNonRetryableRagIndexFailure)
            ) {
              throw new NonRetryableRagIndexError(
                "rag_index_limit",
                `Non-retryable RAG indexing failures: ${uniqueErrors
                  .slice(0, 5)
                  .join(", ")}`
              );
            }

            // Treat partial failures as retryable by default; the job runner should be
            // conservative to avoid silently dropping documents.
            throw new Error(`rag_index_failed:${result.failed.length}`);
          }

          return result;
        },
        internalErrorReason: "RAG index job failed",
        lockTtlSeconds: 60 * 4,
        mapNonRetryableError: (error) =>
          error instanceof NonRetryableRagIndexError
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
        schema: ragIndexJobSchema,
        span,
        verifyMaxBytes: MAX_RAG_JOB_BODY_BYTES,
      })
  );
}
