/**
 * @fileoverview Chat attachment upload endpoint using Supabase Storage.
 */

import "server-only";

import {
  ATTACHMENT_ALLOWED_MIME_TYPES,
  ATTACHMENT_MAX_FILE_SIZE,
  ATTACHMENT_MAX_FILES,
  ATTACHMENT_MAX_TOTAL_SIZE,
  attachmentUploadOptionsSchema,
  isAllowedMimeType,
  sanitizeFilename,
} from "@schemas/attachments";
import { fileTypeFromBuffer } from "file-type";
import { revalidateTag } from "next/cache";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { errorResponse, requireUserId } from "@/lib/api/route-helpers";
import { bumpTag } from "@/lib/cache/tags";
import { PayloadTooLargeError, parseFormDataWithLimit } from "@/lib/http/body";
import { secureUuid } from "@/lib/security/random";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { recordErrorOnActiveSpan } from "@/lib/telemetry/span";

const logger = createServerLogger("chat.attachments.upload");

/** Storage bucket name for chat attachments. */
const STORAGE_BUCKET = "attachments";

/**
 * Validates files from form data for upload.
 *
 * @param formData - FormData object containing files.
 * @returns Validation result with files or error response.
 */
function validateUploadFiles(
  formData: FormData
): { data: File[] } | { error: NextResponse } {
  const files = Array.from(formData.values()).filter(
    (value): value is File => value instanceof File && value.size > 0
  );

  if (files.length === 0) {
    return {
      error: errorResponse({
        error: "invalid_request",
        reason: "No files uploaded",
        status: 400,
      }),
    };
  }

  if (files.length > ATTACHMENT_MAX_FILES) {
    return {
      error: errorResponse({
        error: "invalid_request",
        reason: `Maximum ${ATTACHMENT_MAX_FILES} files allowed per request`,
        status: 400,
      }),
    };
  }

  const oversizedFile = files.find((file) => file.size > ATTACHMENT_MAX_FILE_SIZE);
  if (oversizedFile) {
    return {
      error: errorResponse({
        error: "invalid_request",
        reason: `File "${oversizedFile.name}" exceeds maximum size of ${Math.floor(ATTACHMENT_MAX_FILE_SIZE / 1024 / 1024)}MB`,
        status: 400,
      }),
    };
  }

  const invalidTypeFile = files.find((file) => !isAllowedMimeType(file.type));
  if (invalidTypeFile) {
    return {
      error: errorResponse({
        error: "invalid_request",
        reason: `File "${invalidTypeFile.name}" has invalid type. Allowed types: ${ATTACHMENT_ALLOWED_MIME_TYPES.join(", ")}`,
        status: 400,
      }),
    };
  }

  return { data: files };
}

/**
 * Verifies file MIME type using magic bytes.
 *
 * Compares detected MIME type from file contents against declared type.
 * Prevents malware disguised as allowed file types.
 *
 * @param buffer - File contents as Uint8Array.
 * @param declaredType - MIME type declared by client.
 * @returns Validation result with detected type or error.
 */
async function verifyMimeType(
  buffer: Uint8Array,
  declaredType: string
): Promise<
  | { valid: true; detectedType: string }
  | { detectedType?: string; reason: string; valid: false }
> {
  const detected = await fileTypeFromBuffer(buffer);

  // For files without detectable magic bytes (e.g., text/csv, text/plain),
  // trust the declared type if it's in allowed list
  if (!detected) {
    if (isAllowedMimeType(declaredType)) {
      return { detectedType: declaredType, valid: true };
    }
    return { reason: "Unable to verify file type", valid: false };
  }

  // Make detected MIME the source of truth - must be in allowed list
  if (!isAllowedMimeType(detected.mime)) {
    return {
      reason: `Detected MIME type ${detected.mime} is not allowed`,
      valid: false,
    };
  }

  // Require exact match - no category-based relaxation (prevents malware disguised as images)
  if (detected.mime !== declaredType) {
    return {
      reason: `MIME type mismatch: declared ${declaredType}, detected ${detected.mime}`,
      valid: false,
    };
  }

  return { detectedType: detected.mime, valid: true };
}

/** Result of a single file upload operation. */
interface UploadResult {
  file: File;
  id: string;
  insertedMetadata: boolean;
  path: string;
  uploaded: boolean;
  detectedType?: string;
  errorKind?: "metadata" | "validation" | "storage";
  error: Error | null;
  signedUrl: string | null;
}

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
 * Uploads a single file to Supabase Storage.
 *
 * @param file - File to upload.
 * @param userId - User ID for path prefix.
 * @param supabase - Supabase client.
 * @returns Upload result with path or error.
 */
async function uploadToSupabaseStorage(options: {
  chatId?: string;
  chatMessageId?: number;
  file: File;
  supabase: TypedServerSupabase;
  tripId?: number;
  userId: string;
}): Promise<UploadResult> {
  const { chatId, chatMessageId, file, supabase, tripId, userId } = options;

  if (chatId === undefined && tripId === undefined) {
    return {
      detectedType: undefined,
      error: new Error("Either chatId or tripId is required."),
      errorKind: "validation",
      file,
      id: "",
      insertedMetadata: false,
      path: "",
      signedUrl: null,
      uploaded: false,
    };
  }

  const attachmentId = secureUuid();
  const sanitizedName = sanitizeFilename(file.name);
  const storagePath = buildAttachmentStoragePath({
    attachmentId,
    chatId,
    fileName: sanitizedName,
    tripId,
    userId,
  });

  // Convert File to Buffer for magic byte verification
  const arrayBuffer = await file.arrayBuffer();
  const buffer = new Uint8Array(arrayBuffer);

  // Verify MIME type using magic bytes
  const mimeVerification = await verifyMimeType(buffer, file.type);
  if (!mimeVerification.valid) {
    return {
      detectedType: mimeVerification.detectedType,
      error: new Error(mimeVerification.reason),
      errorKind: "validation",
      file,
      id: attachmentId,
      insertedMetadata: false,
      path: "",
      signedUrl: null,
      uploaded: false,
    };
  }

  const contentType = mimeVerification.detectedType ?? file.type;

  // Create metadata record first so Storage RLS can validate the upload.
  const { error: insertError } = await supabase.from("file_attachments").insert({
    bucket_name: STORAGE_BUCKET,
    chat_id: chatId ?? null,
    chat_message_id: chatMessageId ?? null,
    file_path: storagePath,
    file_size: file.size,
    filename: attachmentId,
    id: attachmentId,
    mime_type: contentType,
    original_filename: file.name,
    trip_id: tripId ?? null,
    upload_status: "uploading",
    user_id: userId,
  });

  if (insertError) {
    return {
      error: new Error(insertError.message),
      errorKind: "metadata",
      file,
      id: attachmentId,
      insertedMetadata: false,
      path: storagePath,
      signedUrl: null,
      uploaded: false,
    };
  }

  // Upload to Supabase Storage
  const { error } = await supabase.storage
    .from(STORAGE_BUCKET)
    .upload(storagePath, buffer, {
      contentType,
      upsert: false,
    });

  if (error) {
    try {
      await supabase
        .from("file_attachments")
        .update({ upload_status: "failed" })
        .eq("id", attachmentId);
    } catch (updateFailedError) {
      logger.warn("failed_to_mark_attachment_failed", {
        attachmentId,
        error:
          updateFailedError instanceof Error
            ? updateFailedError.message
            : String(updateFailedError),
      });
    }
    return {
      detectedType: mimeVerification.detectedType,
      error: new Error(error.message),
      errorKind: "storage",
      file,
      id: attachmentId,
      insertedMetadata: true,
      path: storagePath,
      signedUrl: null,
      uploaded: false,
    };
  }

  const { error: updateError } = await supabase
    .from("file_attachments")
    .update({ upload_status: "completed" })
    .eq("id", attachmentId);

  if (updateError) {
    return {
      detectedType: mimeVerification.detectedType,
      error: new Error(updateError.message),
      errorKind: "metadata",
      file,
      id: attachmentId,
      insertedMetadata: true,
      path: storagePath,
      signedUrl: null,
      uploaded: true,
    };
  }

  // Generate signed URL for the uploaded file (1 hour expiry)
  const { data: signedUrlData } = await supabase.storage
    .from(STORAGE_BUCKET)
    .createSignedUrl(storagePath, 3600, { download: true });

  const signedUrl = signedUrlData?.signedUrl ?? null;

  return {
    detectedType: mimeVerification.detectedType,
    error: null,
    file,
    id: attachmentId,
    insertedMetadata: true,
    path: storagePath,
    signedUrl,
    uploaded: true,
  };
}

/**
 * Deletes a file from Supabase Storage.
 *
 * @param path - File path within the bucket.
 * @param supabase - Supabase client.
 */
async function deleteFromStorage(
  path: string,
  supabase: TypedServerSupabase
): Promise<void> {
  const { error } = await supabase.storage.from(STORAGE_BUCKET).remove([path]);
  if (error) {
    throw new Error(`Failed to delete file: ${error.message}`);
  }
}

/** Shape of an uploaded file record in the response. */
interface UploadedFileRecord {
  id: string;
  name: string;
  size: number;
  status: "uploading" | "completed" | "failed";
  type: string;
  url: string | null;
}

export const POST = withApiGuards({
  auth: true,
  botId: true,
  rateLimit: "chat:attachments",
  telemetry: "chat.attachments.upload",
})(async (req: NextRequest, { supabase, user }) => {
  // Validate content type
  const contentType = req.headers.get("content-type");
  if (!contentType?.includes("multipart/form-data")) {
    return errorResponse({
      error: "invalid_request",
      reason: "Invalid content type",
      status: 400,
    });
  }

  // Extract and validate user ID
  const userResult = requireUserId(user);
  if (!userResult.ok) return userResult.error;
  const userId = userResult.data;

  // Parse form data with hard size limit before buffering full payload
  let formData: FormData;
  try {
    formData = await parseFormDataWithLimit(req, ATTACHMENT_MAX_TOTAL_SIZE);
  } catch (error) {
    if (error instanceof PayloadTooLargeError) {
      return errorResponse({
        error: "invalid_request",
        reason: `Request payload exceeds maximum total size of ${Math.floor(ATTACHMENT_MAX_TOTAL_SIZE / (1024 * 1024))}MB`,
        status: 413,
      });
    }
    return errorResponse({
      err: error instanceof Error ? error : undefined,
      error: "invalid_request",
      reason: "Invalid multipart form data",
      status: 400,
    });
  }

  // Validate and extract files
  const validation = validateUploadFiles(formData);
  if ("error" in validation) {
    return validation.error;
  }
  const files = validation.data;

  const optionsResult = attachmentUploadOptionsSchema.safeParse({
    chatId: formData.get("chatId") ?? undefined,
    chatMessageId: formData.get("chatMessageId") ?? undefined,
    tripId: formData.get("tripId") ?? undefined,
  });

  if (!optionsResult.success) {
    return errorResponse({
      err: optionsResult.error,
      error: "invalid_request",
      issues: optionsResult.error.issues,
      reason: "Invalid upload options",
      status: 400,
    });
  }

  const { chatId, chatMessageId, tripId } = optionsResult.data;

  // Upload files to Supabase Storage in parallel
  const uploadResults = await Promise.allSettled(
    files.map((file) =>
      uploadToSupabaseStorage({
        chatId,
        chatMessageId,
        file,
        supabase,
        tripId,
        userId,
      })
    )
  );

  // Process upload results
  const uploadedFiles: UploadedFileRecord[] = [];
  const urls: string[] = [];
  const uploadedPaths: string[] = []; // Track successful uploads for cleanup
  const insertedAttachmentIds: string[] = []; // Track inserted metadata for rollback
  let firstUploadError: Error | null = null;
  let firstUploadStatus: number | null = null;

  for (const result of uploadResults) {
    if (result.status === "rejected") {
      // Upload promise itself rejected (unexpected error)
      const error =
        result.reason instanceof Error
          ? result.reason
          : new Error(String(result.reason));
      recordErrorOnActiveSpan(error);
      logger.error("Unexpected upload error", { error: error.message, userId });
      if (!firstUploadError) firstUploadError = error;
      continue; // Don't return yet - need to cleanup uploaded files
    }

    const {
      detectedType,
      file,
      id,
      insertedMetadata,
      path,
      uploaded,
      error: uploadError,
      errorKind,
      signedUrl,
    } = result.value;

    const isMetadataStatusUpdateFailure =
      errorKind === "metadata" && insertedMetadata && uploaded && uploadError;

    if (insertedMetadata && !isMetadataStatusUpdateFailure) {
      insertedAttachmentIds.push(id);
    }
    if (uploaded && !uploadError && !isMetadataStatusUpdateFailure) {
      uploadedPaths.push(path);
    }

    if (uploadError) {
      // Upload returned an error (validation or storage error)
      recordErrorOnActiveSpan(uploadError);
      logger.error("Failed to upload file to Supabase Storage", {
        error: uploadError.message,
        fileName: file.name,
        userId,
      });

      // Metadata insert failures are treated as per-file failures (no storage object to clean up).
      if (errorKind === "metadata" && !insertedMetadata) {
        uploadedFiles.push({
          id,
          name: file.name,
          size: file.size,
          status: "failed",
          type: detectedType ?? file.type,
          url: null,
        });
        continue;
      }

      if (!firstUploadError) {
        firstUploadError = uploadError;
        firstUploadStatus = errorKind === "validation" ? 400 : 500;
      }
      continue; // Don't return yet - need to cleanup uploaded files
    }

    uploadedFiles.push({
      id,
      name: file.name,
      size: file.size,
      status: "completed",
      type: detectedType ?? file.type,
      url: signedUrl,
    });

    if (signedUrl) {
      urls.push(signedUrl);
    }
  }

  // If any upload failed, cleanup all successfully uploaded files
  if (firstUploadError) {
    logger.warn("Cleaning up uploaded files due to upload failure", {
      count: uploadedPaths.length,
      userId,
    });

    const uniqueUploadedPaths = Array.from(new Set(uploadedPaths));
    const uniqueAttachmentIds = Array.from(new Set(insertedAttachmentIds));

    // Delete storage objects before removing their metadata: the Storage RLS DELETE policy
    // authorizes deletes by verifying a matching metadata row, so removing metadata first
    // would block storage deletion.
    const cleanupResults = await Promise.allSettled(
      uniqueUploadedPaths.map((path) => deleteFromStorage(path, supabase))
    );

    // Log cleanup failures but don't block the error response
    for (const [index, result] of cleanupResults.entries()) {
      if (result.status === "rejected") {
        logger.error("Failed to cleanup uploaded file", {
          error:
            result.reason instanceof Error
              ? result.reason.message
              : String(result.reason),
          path: uniqueUploadedPaths[index],
          userId,
        });
      }
    }

    if (uniqueAttachmentIds.length > 0) {
      const metadataCleanupResults = await Promise.allSettled(
        uniqueAttachmentIds.map((id) =>
          supabase.from("file_attachments").delete().eq("id", id)
        )
      );

      for (const [index, result] of metadataCleanupResults.entries()) {
        if (result.status === "fulfilled" && result.value?.error) {
          logger.error("Failed to cleanup attachment metadata", {
            error: result.value.error.message,
            fileId: uniqueAttachmentIds[index],
            userId,
          });
        }
        if (result.status === "rejected") {
          logger.error("Failed to cleanup attachment metadata", {
            error:
              result.reason instanceof Error
                ? result.reason.message
                : String(result.reason),
            fileId: uniqueAttachmentIds[index],
            userId,
          });
        }
      }
    }

    return errorResponse({
      err: firstUploadError,
      error: firstUploadStatus === 400 ? "invalid_request" : "internal",
      reason: "File upload failed",
      status: firstUploadStatus ?? 500,
    });
  }

  // Invalidate attachment caches
  try {
    revalidateTag("attachments", { expire: 0 });
    await bumpTag("attachments");
  } catch {
    // Ignore cache revalidation errors in non-Next runtime test environments
  }

  return NextResponse.json({
    files: uploadedFiles,
    urls,
  });
});
