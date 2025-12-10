/**
 * @fileoverview File attachment webhook handler for upload status changes.
 *
 * Uses the shared webhook handler abstraction to reduce boilerplate.
 */

import "server-only";

import { createAdminSupabase } from "@/lib/supabase/admin";
import type { Database } from "@/lib/supabase/database.types";
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
    const attachmentId = record?.id;
    const uploadStatus = record?.upload_status;

    // Verify file attachment exists on INSERT with uploading status
    if (payload.type === "INSERT" && attachmentId && uploadStatus === "uploading") {
      const supabase = createAdminSupabase();
      const { error } = await supabase
        .from("file_attachments")
        .select("id")
        .eq("id", attachmentId)
        .limit(1)
        .single();

      if (error) {
        span.recordException(error);
        throw error; // Will be caught by handler and return 500
      }

      span.setAttribute("file.verified", true);
    }

    return {};
  },
  idempotencyTTL: 300,
  name: "files",
  tableFilter: "file_attachments",
});
