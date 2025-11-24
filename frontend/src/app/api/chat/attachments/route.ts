/**
 * @fileoverview Chat attachment upload endpoint.
 *
 * Handles multipart form data uploads, validates file sizes and types.
 */

"use cache: private";

import { revalidateTag } from "next/cache";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { createApiError } from "@/lib/api/error-response";
import { withApiGuards } from "@/lib/api/factory";
import { extractFiles, validateMultipart } from "@/lib/api/guards/multipart";
import { getServerEnvVarWithFallback } from "@/lib/env/server";
import { forwardAuthHeaders } from "@/lib/next/route-helpers";

/** Maximum file size allowed per file in bytes (10MB). */
const MAX_FILE_SIZE = 10 * 1024 * 1024;

/** Maximum number of files allowed per upload request. */
const MAX_FILES_PER_REQUEST = 5;

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
export const POST = withApiGuards({
  auth: true,
  rateLimit: "chat:attachments",
  telemetry: "chat.attachments.upload",
})(async (req: NextRequest) => {
  // Validate content type
  const contentType = req.headers.get("content-type");
  if (!contentType?.includes("multipart/form-data")) {
    return NextResponse.json(
      createApiError("INVALID_CONTENT_TYPE", "Invalid content type"),
      { status: 400 }
    );
  }

  // Parse form data
  const formData = await req.formData();

  // Validate files
  const validation = validateMultipart(formData, {
    maxFiles: MAX_FILES_PER_REQUEST,
    maxSize: MAX_FILE_SIZE,
  });

  if (!validation.valid) {
    const errorCode = validation.errorCode ?? "VALIDATION_ERROR";
    const errorMessage = validation.errorMessage ?? "Validation failed";
    return NextResponse.json(createApiError(errorCode, errorMessage), {
      status: 400,
    });
  }

  const files = extractFiles(formData);

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
  const headers: HeadersInit | undefined = forwardAuthHeaders(req);

  const response = await fetch(`${getBackendApiUrl()}${endpoint}`, {
    body: backendFormData,
    headers,
    method: "POST",
  });

  const data: unknown = await response.json();

  if (!response.ok) {
    const detail = (data as { detail?: string } | undefined)?.detail ?? "Upload failed";
    return NextResponse.json(createApiError("UPLOAD_ERROR", detail), {
      status: response.status,
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
