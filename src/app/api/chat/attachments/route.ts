/**
 * @fileoverview Chat attachment upload endpoint using Supabase Storage.
 *
 * Handles multipart form data uploads directly to Supabase Storage bucket,
 * with metadata stored in Supabase file_attachments table. See ADR-0058 and SPEC-0036.
 */

import "server-only";

import {
  ATTACHMENT_ALLOWED_MIME_TYPES,
  ATTACHMENT_MAX_FILE_SIZE,
  ATTACHMENT_MAX_FILES,
  ATTACHMENT_MAX_TOTAL_SIZE,
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
  path: string;
  detectedType?: string;
  errorKind?: "validation" | "storage";
  error: Error | null;
}

/**
 * Uploads a single file to Supabase Storage.
 *
 * @param file - File to upload.
 * @param userId - User ID for path prefix.
 * @param supabase - Supabase client.
 * @returns Upload result with path or error.
 */
async function uploadToSupabaseStorage(
  file: File,
  userId: string,
  supabase: TypedServerSupabase
): Promise<UploadResult> {
  const uuid = secureUuid();
  const sanitizedName = sanitizeFilename(file.name);
  // Path format per SPEC-0036: chat/{userId}/filename
  const storagePath = `chat/${userId}/${uuid}-${sanitizedName}`;

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
      path: "",
    };
  }

  const contentType = mimeVerification.detectedType ?? file.type;

  // Upload to Supabase Storage
  const { error } = await supabase.storage
    .from(STORAGE_BUCKET)
    .upload(storagePath, buffer, {
      contentType,
      upsert: false,
    });

  if (error) {
    return {
      detectedType: mimeVerification.detectedType,
      error: new Error(error.message),
      errorKind: "storage",
      file,
      path: storagePath,
    };
  }

  return {
    detectedType: mimeVerification.detectedType,
    error: null,
    file,
    path: storagePath,
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

  // Enforce total size limit before buffering
  const contentLengthHeader = req.headers.get("content-length");
  if (contentLengthHeader) {
    const contentLength = Number.parseInt(contentLengthHeader, 10);
    if (Number.isFinite(contentLength) && contentLength > ATTACHMENT_MAX_TOTAL_SIZE) {
      return errorResponse({
        error: "invalid_request",
        reason: `Request payload exceeds maximum total size of ${Math.floor(ATTACHMENT_MAX_TOTAL_SIZE / (1024 * 1024))}MB`,
        status: 413,
      });
    }
  }

  // Extract and validate user ID
  const userResult = requireUserId(user);
  if ("error" in userResult) {
    return userResult.error;
  }
  const { userId } = userResult;

  // Parse form data
  const formData = await req.formData();

  // Validate and extract files
  const validation = validateUploadFiles(formData);
  if ("error" in validation) {
    return validation.error;
  }
  const files = validation.data;

  // Upload files to Supabase Storage in parallel
  const uploadResults = await Promise.allSettled(
    files.map((file) => uploadToSupabaseStorage(file, userId, supabase))
  );

  // Process upload results and store metadata
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

    const { detectedType, file, path, error: uploadError, errorKind } = result.value;

    if (uploadError) {
      // Upload returned an error (validation or storage error)
      recordErrorOnActiveSpan(uploadError);
      logger.error("Failed to upload file to Supabase Storage", {
        error: uploadError.message,
        fileName: file.name,
        userId,
      });
      if (!firstUploadError) {
        firstUploadError = uploadError;
        firstUploadStatus = errorKind === "validation" ? 400 : 500;
      }
      continue; // Don't return yet - need to cleanup uploaded files
    }

    // Track this successful upload for potential cleanup
    uploadedPaths.push(path);

    // Generate file ID for metadata
    const fileId = secureUuid();

    // Insert metadata into Supabase
    // Note: filename = storage key (UUID), original_filename = user-facing name
    const { error: insertError } = await supabase.from("file_attachments").insert({
      bucket_name: STORAGE_BUCKET,
      file_path: path,
      file_size: file.size,
      filename: fileId, // Storage key (UUID)
      id: fileId,
      mime_type: detectedType ?? file.type,
      original_filename: file.name, // User-facing name
      upload_status: "completed",
      user_id: userId,
    });

    if (insertError) {
      logger.error("Failed to insert attachment metadata", {
        error: insertError.message,
        fileId,
        userId,
      });
      // Clean up uploaded file on metadata failure
      try {
        await deleteFromStorage(path, supabase);
      } catch (cleanupError) {
        logger.warn("Failed to clean up storage after metadata insert failure", {
          cleanupError:
            cleanupError instanceof Error ? cleanupError.message : String(cleanupError),
          fileId,
          path,
          userId,
        });
      }
      // Mark this file as failed but continue with others
      uploadedFiles.push({
        id: fileId,
        name: file.name,
        size: file.size,
        status: "failed",
        type: detectedType ?? file.type,
        url: null,
      });
      continue;
    }

    // Generate signed URL for the uploaded file (1 hour expiry)
    const { data: signedUrlData } = await supabase.storage
      .from(STORAGE_BUCKET)
      .createSignedUrl(path, 3600, { download: true });

    const signedUrl = signedUrlData?.signedUrl ?? null;

    uploadedFiles.push({
      id: fileId,
      name: file.name,
      size: file.size,
      status: "completed",
      type: detectedType ?? file.type,
      url: signedUrl,
    });

    insertedAttachmentIds.push(fileId);

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

    if (insertedAttachmentIds.length > 0) {
      const metadataCleanupResults = await Promise.allSettled(
        insertedAttachmentIds.map((id) =>
          supabase.from("file_attachments").delete().eq("id", id)
        )
      );

      for (const [index, result] of metadataCleanupResults.entries()) {
        if (result.status === "fulfilled" && result.value?.error) {
          logger.error("Failed to cleanup attachment metadata", {
            error: result.value.error.message,
            fileId: insertedAttachmentIds[index],
            userId,
          });
        }
        if (result.status === "rejected") {
          logger.error("Failed to cleanup attachment metadata", {
            error:
              result.reason instanceof Error
                ? result.reason.message
                : String(result.reason),
            fileId: insertedAttachmentIds[index],
            userId,
          });
        }
      }
    }

    // Delete all successfully uploaded files
    const cleanupResults = await Promise.allSettled(
      uploadedPaths.map((path) => deleteFromStorage(path, supabase))
    );

    // Log cleanup failures but don't block the error response
    for (const [index, result] of cleanupResults.entries()) {
      if (result.status === "rejected") {
        logger.error("Failed to cleanup uploaded file", {
          error:
            result.reason instanceof Error
              ? result.reason.message
              : String(result.reason),
          path: uploadedPaths[index],
          userId,
        });
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
