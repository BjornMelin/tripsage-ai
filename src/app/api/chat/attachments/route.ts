/**
 * @fileoverview Attachments v2: create signed upload URLs (Supabase Storage) + persist metadata.
 */

import "server-only";

import {
  type AttachmentSignedUpload,
  attachmentCreateSignedUploadRequestSchema,
  attachmentCreateSignedUploadResponseSchema,
  sanitizeFilename,
} from "@schemas/attachments";
import { revalidateTag } from "next/cache";
import { NextResponse } from "next/server";
import { z } from "zod";
import { withApiGuards } from "@/lib/api/factory";
import {
  errorResponse,
  parseJsonBody,
  requireUserId,
  validateSchema,
} from "@/lib/api/route-helpers";
import { bumpTag } from "@/lib/cache/tags";
import { tryEnqueueJob } from "@/lib/qstash/client";
import { secureUuid } from "@/lib/security/random";
import { createServerLogger } from "@/lib/telemetry/logger";

/** Storage bucket name for attachments. */
const STORAGE_BUCKET = "attachments";

const uploadRecordSchema = z.object({
  path: z.string(),
  signedUrl: z.string(),
  token: z.string(),
});

/**
 * Storage object path conventions:
 * - Chat-scoped: `{userId}/{chatId}/{attachmentId}/{fileName}`
 * - Trip-scoped: `{userId}/{tripId}/{attachmentId}/{fileName}`
 * - Trip + chat: `{userId}/{tripId}/{chatId}/{attachmentId}/{fileName}`
 */
function buildAttachmentStoragePath(options: {
  attachmentId: string;
  chatId?: string;
  fileName: string;
  tripId?: number;
  userId: string;
}): string {
  const { attachmentId, chatId, fileName, tripId, userId } = options;
  if (tripId !== undefined) {
    return chatId !== undefined
      ? `${userId}/${tripId}/${chatId}/${attachmentId}/${fileName}`
      : `${userId}/${tripId}/${attachmentId}/${fileName}`;
  }

  if (chatId !== undefined) {
    return `${userId}/${chatId}/${attachmentId}/${fileName}`;
  }

  throw new Error("Invariant violation: either chatId or tripId is required.");
}

/**
 * POST /api/chat/attachments
 *
 * Creates attachment metadata rows and returns signed upload URLs.
 *
 * Client uploads directly to Supabase Storage using:
 * `supabase.storage.from(bucket).uploadToSignedUrl(path, token, file, { contentType })`.
 */
export const POST = withApiGuards({
  auth: true,
  botId: true,
  rateLimit: "chat:attachments",
  telemetry: "chat.attachments.signed-upload",
})(async (req, { supabase, user }) => {
  const logger = createServerLogger("chat.attachments.signed-upload");

  const userResult = requireUserId(user);
  if (!userResult.ok) return userResult.error;
  const userId = userResult.data;

  const parsed = await parseJsonBody(req);
  if (!parsed.ok) return parsed.error;

  const validation = validateSchema(
    attachmentCreateSignedUploadRequestSchema,
    parsed.data
  );
  if (!validation.ok) return validation.error;
  const body = validation.data;

  const uploads: AttachmentSignedUpload[] = [];
  const insertedIds: string[] = [];

  const cleanupInserted = async (): Promise<void> => {
    if (insertedIds.length === 0) return;
    try {
      const { error: cleanupError } = await supabase
        .from("file_attachments")
        .delete()
        .in("id", insertedIds);
      if (cleanupError) {
        logger.warn("Failed to cleanup inserted attachment rows", {
          error: cleanupError.message,
          insertedCount: insertedIds.length,
          userId,
        });
      }
    } catch (error) {
      logger.warn("Failed to cleanup inserted attachment rows", {
        error: error instanceof Error ? error.message : String(error),
        insertedCount: insertedIds.length,
        userId,
      });
    }
  };

  try {
    for (const file of body.files) {
      const attachmentId = secureUuid();
      const sanitizedName = sanitizeFilename(file.originalName);
      const storagePath = buildAttachmentStoragePath({
        attachmentId,
        chatId: body.chatId,
        fileName: sanitizedName,
        tripId: body.tripId,
        userId,
      });

      // Insert metadata row first so Storage RLS can authorize the upload.
      const { error: insertError } = await supabase.from("file_attachments").insert({
        bucket_name: STORAGE_BUCKET,
        chat_id: body.chatId ?? null,
        chat_message_id: body.chatMessageId ?? null,
        file_path: storagePath,
        file_size: file.size,
        filename: attachmentId,
        id: attachmentId,
        mime_type: file.mimeType,
        original_filename: file.originalName,
        trip_id: body.tripId ?? null,
        upload_status: "uploading",
        user_id: userId,
      });

      if (insertError) {
        await cleanupInserted();
        return errorResponse({
          err: new Error(insertError.message),
          error: "db_error",
          reason: "Failed to create attachment record",
          status: 500,
        });
      }

      insertedIds.push(attachmentId);

      const { data: signedData, error: signedError } = await supabase.storage
        .from(STORAGE_BUCKET)
        .createSignedUploadUrl(storagePath, { upsert: false });

      if (signedError || !signedData) {
        logger.warn("Failed to create signed upload URL", {
          attachmentId,
          error: signedError?.message ?? "unknown_error",
          userId,
        });

        // Best-effort cleanup: remove metadata rows so the paths cannot authorize uploads.
        await cleanupInserted();

        return errorResponse({
          err: signedError ? new Error(signedError.message) : undefined,
          error: "internal",
          reason: "Failed to create signed upload URLs",
          status: 500,
        });
      }

      const uploadRecord = uploadRecordSchema.safeParse(signedData);
      if (!uploadRecord.success) {
        await cleanupInserted();
        return errorResponse({
          err: uploadRecord.error,
          error: "internal",
          reason: "Invalid signed upload response",
          status: 500,
        });
      }

      uploads.push({
        attachmentId,
        mimeType: file.mimeType,
        originalName: file.originalName,
        path: uploadRecord.data.path,
        signedUrl: uploadRecord.data.signedUrl,
        size: file.size,
        token: uploadRecord.data.token,
      });
    }
  } catch (error) {
    logger.error("Unexpected error creating signed upload URLs", {
      error: error instanceof Error ? error.message : String(error),
      userId,
    });

    // Best-effort cleanup of inserted metadata rows.
    await cleanupInserted();

    return errorResponse({
      err: error instanceof Error ? error : undefined,
      error: "internal",
      reason: "Failed to create signed upload URLs",
      status: 500,
    });
  }

  const responseValidation = attachmentCreateSignedUploadResponseSchema.safeParse({
    uploads,
  });

  if (!responseValidation.success) {
    logger.warn("Signed upload response failed schema validation", {
      error: responseValidation.error.message,
      userId,
    });

    await cleanupInserted();
    return errorResponse({
      err: responseValidation.error,
      error: "internal",
      reason: "Invalid response",
      status: 500,
    });
  }

  // Trigger ingestion via QStash (thin publish only; receiver lives elsewhere).
  // This is best-effort and should never block returning the signed URL to the user.
  const enqueueResult = await tryEnqueueJob(
    "attachments.ingest",
    {
      attachmentIds: uploads.map((u) => u.attachmentId),
      chatId: body.chatId ?? null,
      tripId: body.tripId ?? null,
      userId,
    },
    "/api/jobs/attachments-ingest",
    {
      deduplicationId: uploads.map((u) => u.attachmentId).join(":"),
    }
  );

  if (!enqueueResult.success) {
    logger.warn("Failed to enqueue attachment ingestion job", {
      error: enqueueResult.error?.message ?? "unavailable",
      userId,
    });
  }

  try {
    revalidateTag("attachments", { expire: 0 });
    await bumpTag("attachments");
  } catch {
    // Ignore cache invalidation errors in non-Next runtime test environments
  }

  return NextResponse.json(responseValidation.data);
});
