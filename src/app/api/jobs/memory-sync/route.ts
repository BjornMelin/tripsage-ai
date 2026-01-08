/**
 * @fileoverview QStash job route that validates and persists memory sync payloads.
 */

import "server-only";

import { memorySyncJobSchema } from "@schemas/webhooks";
import { releaseKey, tryReserveKey } from "@/lib/idempotency/redis";
import { runQstashJob } from "@/lib/qstash/job-route";
import { createAdminSupabase } from "@/lib/supabase/admin";
import { hashTelemetryIdentifier } from "@/lib/telemetry/identifiers";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { handleMemorySyncJob } from "./_handler";

/**
 * Processes queued memory sync jobs with signature verification and deduplication.
 *
 * @param req - The incoming job request.
 * @return Response indicating success or error.
 */
export async function POST(req: Request) {
  return await withTelemetrySpan(
    "jobs.memory-sync",
    { attributes: { route: "/api/jobs/memory-sync" } },
    async (span) =>
      await runQstashJob({
        handle: async (payload) => {
          // De-duplicate at worker level to avoid double-processing on retries
          const businessKey = `memory-sync:${payload.idempotencyKey}`;
          const unique = await tryReserveKey(businessKey, {
            degradedMode: "fail_closed",
            ttlSeconds: 300, // short TTL to avoid amplification across republishes
          });
          if (!unique) {
            span.setAttribute("job.duplicate", true);
            return { duplicate: true, ok: true };
          }

          try {
            const supabase = createAdminSupabase();
            const result = await handleMemorySyncJob({ supabase }, payload.payload);

            return { ok: true, ...result };
          } catch (error) {
            // Best-effort release so QStash retries can re-attempt on transient failures.
            await releaseKey(businessKey, { degradedMode: "fail_open" }).catch(
              () => undefined
            );
            span.setAttribute("job.idempotency_released", true);
            throw error;
          }
        },
        internalErrorReason: "Memory sync job failed",
        onPayloadValidated: (payload, _meta, span) => {
          span.setAttribute("idempotency.key", payload.idempotencyKey);
          span.setAttribute("sync.type", payload.payload.syncType);
          const sessionIdHash = hashTelemetryIdentifier(payload.payload.sessionId);
          if (sessionIdHash) {
            span.setAttribute("session.id_hash", sessionIdHash);
          }
          const userIdHash = hashTelemetryIdentifier(payload.payload.userId);
          if (userIdHash) {
            span.setAttribute("user.id_hash", userIdHash);
          }
        },
        onVerifyFailure: (result, request, span) => {
          const pathname = new URL(request.url).pathname;
          span.addEvent?.("unauthorized_attempt", {
            hasSignature: result.reason !== "missing_signature",
            path: pathname,
            reason: result.reason,
          });
        },
        req,
        schema: memorySyncJobSchema,
        span,
      })
  );
}
