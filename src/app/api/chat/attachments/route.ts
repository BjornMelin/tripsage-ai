/**
 * @fileoverview Chat attachment upload endpoint.
 *
 * Handles multipart form data uploads, validates file sizes and types.
 */

import "server-only";

import { FILE_COUNT_LIMITS, FILE_SIZE_LIMITS } from "@schemas/api";
import { revalidateTag } from "next/cache";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { validateMultipart } from "@/lib/api/guards/multipart";
import { errorResponse } from "@/lib/api/route-helpers";
import { getServerEnvVarWithFallback } from "@/lib/env/server";

/**
 * Returns backend API URL from environment or default.
 *
 * @returns Backend API URL string.
 */
function getBackendApiUrl(): string {
  return (
    getServerEnvVarWithFallback("BACKEND_API_URL", "http://localhost:8001") ??
    "http://localhost:8001"
  );
}

/** Single file upload response from backend API. */
interface SingleUploadResponse {
  file_id: string;
  filename: string;
  file_size: number;
  mime_type: string;
  processing_status: string;
}

/** Batch upload file response structure. */
interface BatchUploadFileResponse {
  fileId: string;
  filename: string;
  fileSize: number;
  mimeType: string;
  processingStatus: string;
}

/** Batch upload response from backend API. */
interface BatchUploadResponse {
  successful_uploads: BatchUploadFileResponse[];
}

/**
 * Handles multipart form data file uploads with validation.
 *
 * @param req - Next.js request containing multipart form data.
 * @returns JSON response with uploaded file metadata or error.
 */
const MAX_TOTAL_UPLOAD_BYTES = FILE_COUNT_LIMITS.STANDARD * FILE_SIZE_LIMITS.STANDARD;

export const POST = withApiGuards({
  auth: true,
  rateLimit: "chat:attachments",
  telemetry: "chat.attachments.upload",
})(async (req: NextRequest, { supabase }) => {
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
    if (Number.isFinite(contentLength) && contentLength > MAX_TOTAL_UPLOAD_BYTES) {
      return errorResponse({
        error: "invalid_request",
        reason: `Request payload exceeds maximum total size of ${Math.floor(
          MAX_TOTAL_UPLOAD_BYTES / (1024 * 1024)
        )}MB`,
        status: 413,
      });
    }
  }

  // Parse form data
  const formData = await req.formData();

  // Validate and extract files
  const validation = validateMultipart(formData, {
    maxFiles: FILE_COUNT_LIMITS.STANDARD,
    maxSize: FILE_SIZE_LIMITS.STANDARD,
  });

  if ("error" in validation) {
    return validation.error;
  }

  const files = validation.data;

  // Prepare backend request
  const backendFormData = new FormData();
  if (files.length === 1) {
    backendFormData.append("file", files[0]);
  } else {
    for (const file of files) {
      backendFormData.append("files", file);
    }
  }

  // Call backend API
  const endpoint =
    files.length === 1 ? "/api/attachments/upload" : "/api/attachments/upload/batch";

  const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
  if (sessionError || !sessionData?.session?.access_token) {
    return errorResponse({
      error: "unauthenticated",
      reason: "Missing authenticated session",
      status: 401,
    });
  }

  const response = await fetch(`${getBackendApiUrl()}${endpoint}`, {
    body: backendFormData,
    headers: {
      Authorization: `Bearer ${sessionData.session.access_token}`,
    },
    method: "POST",
  });

  const data: unknown = await response.json();

  if (!response.ok) {
    const detail = (data as { detail?: string } | undefined)?.detail ?? "Upload failed";
    return errorResponse({
      err: new Error(`File upload failed: ${detail}`),
      error: "internal",
      reason: "File upload failed",
      status: response.status >= 400 && response.status < 500 ? response.status : 502,
    });
  }

  // Transform response
  if (files.length === 1) {
    const singleUpload = data as SingleUploadResponse;
    const payload = {
      files: [
        {
          id: singleUpload.file_id,
          name: singleUpload.filename,
          size: singleUpload.file_size,
          status: singleUpload.processing_status,
          type: singleUpload.mime_type,
          url: `/api/attachments/${singleUpload.file_id}/download`,
        },
      ],
      urls: [`/api/attachments/${singleUpload.file_id}/download`],
    };
    try {
      revalidateTag("attachments", "max");
    } catch {
      // Ignore cache revalidation errors in non-Next runtime test environments
    }
    return NextResponse.json(payload);
  }

  // Batch response
  const batchResponse = data as BatchUploadResponse;
  const transformedFiles = batchResponse.successful_uploads.map(
    (
      file
    ): {
      id: string;
      name: string;
      size: number;
      status: string;
      type: string;
      url: string;
    } => ({
      id: file.fileId,
      name: file.filename,
      size: file.fileSize,
      status: file.processingStatus,
      type: file.mimeType,
      url: `/api/attachments/${file.fileId}/download`,
    })
  );

  const resultPayload = {
    files: transformedFiles,
    urls: transformedFiles.map((f) => f.url),
  };
  const result = NextResponse.json(resultPayload);
  try {
    revalidateTag("attachments", "max");
  } catch {
    // Ignore cache revalidation errors in non-Next runtime test environments
  }
  return result;
});
