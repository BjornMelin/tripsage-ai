/**
 * @fileoverview API route for uploading chat attachments with rate limiting.
 * Handles multipart form data uploads, validates file sizes and types,
 * and provides rate limiting protection.
 */

"use cache: private";
import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import { revalidateTag } from "next/cache";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { buildRateLimitKey, forwardAuthHeaders } from "@/lib/next/route-helpers";

/** Maximum file size allowed per file in bytes (10MB). */
const MAX_FILE_SIZE = 10 * 1024 * 1024;

/** Maximum number of files allowed per upload request. */
const MAX_FILES_PER_REQUEST = 5;

/** Backend API URL for attachment operations. */
const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://localhost:8001";

const RATELIMIT_PREFIX = "ratelimit:attachments";

/**
 * Lazily construct a rate limiter when Upstash credentials are configured.
 *
 * @returns Configured Ratelimit instance or undefined when env vars are absent.
 */
function createRateLimiter(): Ratelimit | undefined {
  const upstashUrl = process.env.UPSTASH_REDIS_REST_URL;
  const upstashToken = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!upstashUrl || !upstashToken) {
    return undefined;
  }

  return new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(20, "1 m"),
    prefix: RATELIMIT_PREFIX,
    redis: Redis.fromEnv(),
  });
}

interface SingleUploadResponse {
  file_id: string;
  filename: string;
  file_size: number;
  mime_type: string;
  processing_status: string;
}

interface BatchUploadFileResponse {
  fileId: string;
  filename: string;
  fileSize: number;
  mimeType: string;
  processingStatus: string;
}

interface BatchUploadResponse {
  successful_uploads: BatchUploadFileResponse[];
}

/**
 * Handles attachment uploads with validation and rate limiting.
 *
 * @param req - The Next.js request object containing multipart form data.
 * @returns A JSON response with uploaded file information or an error response.
 * @throws Will return error responses for validation failures or server errors.
 */
export async function POST(req: NextRequest) {
  try {
    // Optional rate limit: enable only when Upstash env is configured
    const limiter = createRateLimiter();
    if (limiter) {
      const identifier = buildRateLimitKey(req);
      const { success, limit, remaining, reset } = await limiter.limit(identifier);
      if (!success) {
        return NextResponse.json(
          { code: "RATE_LIMIT", error: "Rate limit exceeded" },
          {
            headers: {
              "X-RateLimit-Limit": String(limit),
              "X-RateLimit-Remaining": String(remaining),
              "X-RateLimit-Reset": String(reset),
            },
            status: 429,
          }
        );
      }
    }
    // Validate content type
    const contentType = req.headers.get("content-type");
    if (!contentType?.includes("multipart/form-data")) {
      return NextResponse.json(
        { code: "INVALID_CONTENT_TYPE", error: "Invalid content type" },
        { status: 400 }
      );
    }

    // Parse form data
    const formData = await req.formData();
    const files = Array.from(formData.values()).filter(
      (value): value is File => value instanceof File && value.size > 0
    );

    // Validate files
    if (files.length === 0) {
      return NextResponse.json(
        { code: "NO_FILES", error: "No files uploaded" },
        { status: 400 }
      );
    }

    if (files.length > MAX_FILES_PER_REQUEST) {
      return NextResponse.json(
        {
          code: "TOO_MANY_FILES",
          error: `Maximum ${MAX_FILES_PER_REQUEST} files allowed per request`,
        },
        { status: 400 }
      );
    }

    // Check file sizes
    const oversizedFile = files.find((file) => file.size > MAX_FILE_SIZE);
    if (oversizedFile) {
      return NextResponse.json(
        {
          code: "FILE_TOO_LARGE",
          error: `File "${oversizedFile.name}" exceeds maximum size of ${MAX_FILE_SIZE / 1024 / 1024}MB`,
        },
        { status: 400 }
      );
    }

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

    const response = await fetch(`${BACKEND_API_URL}${endpoint}`, {
      body: backendFormData,
      headers,
      method: "POST",
    });

    const data: unknown = await response.json();

    if (!response.ok) {
      const detail =
        (data as { detail?: string } | undefined)?.detail ?? "Upload failed";
      return NextResponse.json(
        { code: "UPLOAD_ERROR", error: detail },
        { status: response.status }
      );
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
  } catch (error) {
    // DecisionFramework§2.1(L1): Log for debugging while returning sanitized response.
    console.error("File upload error:", error);
    return NextResponse.json(
      { code: "INTERNAL_ERROR", error: "Internal server error" },
      { status: 500 }
    );
  }
}
