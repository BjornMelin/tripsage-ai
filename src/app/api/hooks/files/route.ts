/**
 * @fileoverview File attachment webhook handler for upload status changes.
 */

import "server-only";

import { tryEnqueueJob } from "@/lib/qstash/client";
import { QSTASH_JOB_LABELS } from "@/lib/qstash/config";
import { getAdminSupabase } from "@/lib/supabase/admin";
import type { Database } from "@/lib/supabase/database.types";
import { getSingle } from "@/lib/supabase/typed-helpers";
import { WebhookServiceUnavailableError } from "@/lib/webhooks/errors";
import { createWebhookHandler } from "@/lib/webhooks/handler";

type FileAttachmentRow = Database["public"]["Tables"]["file_attachments"]["Row"];

/**
 * Handles file attachment database change webhooks.
 *
 * Features (via handler abstraction):
 * - Rate limiting (100 req/min per IP)
 * - Body size validation (64KB max)
 * - HMAC signature verification
 * - Table filtering (file_attachments only)
 * - Idempotency via Redis
 */
export const POST = createWebhookHandler({
  enableIdempotency: true,

  async handle(payload, _eventKey, span) {
    const record = payload.record as Partial<FileAttachmentRow> | null;
    const oldRecord = payload.oldRecord as Partial<FileAttachmentRow> | null;
    const attachmentId = record?.id;
    const uploadStatus = record?.upload_status;

    // Verify file attachment exists on INSERT with uploading status
    if (payload.type === "INSERT" && attachmentId && uploadStatus === "uploading") {
      const supabase = getAdminSupabase();
      const { error } = await getSingle(
        supabase,
        "file_attachments",
        (qb) => qb.eq("id", attachmentId),
        { select: "id", validate: false }
      );

      if (error) {
        const normalized = error instanceof Error ? error : new Error(String(error));
        span.recordException(normalized);
        throw normalized; // Will be caught by handler and return 500
      }

      span.setAttribute("file.verified", true);
    }

    // Trigger ingestion when upload completes (UPDATE: uploading -> completed)
    const oldUploadStatus = oldRecord?.upload_status;
    if (
      payload.type === "UPDATE" &&
      attachmentId &&
      uploadStatus === "completed" &&
      oldUploadStatus !== "completed"
    ) {
      const enqueue = await tryEnqueueJob(
        "attachments-ingest",
        { attachmentId },
        "/api/jobs/attachments-ingest",
        {
          deduplicationId: `attachments-ingest:${attachmentId}`,
          delay: 0,
          label: QSTASH_JOB_LABELS.ATTACHMENTS_INGEST,
        }
      );

      if (enqueue.success) {
        span.setAttribute("qstash.message_id", enqueue.messageId);
        return { enqueued: true };
      }

      span.setAttribute("qstash.unavailable", true);
      throw new WebhookServiceUnavailableError("qstash_unavailable", {
        cause: enqueue.error ?? undefined,
      });
    }

    return {};
  },
  idempotencyTTL: 300,
  name: "files",
  tableFilter: "file_attachments",
});
