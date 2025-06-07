import type { NextRequest } from "next/server";

// Configuration - should match backend centralized config
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB per file
const MAX_FILES_PER_REQUEST = 5;

// Backend API configuration
const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://localhost:8000";
const API_TIMEOUT = 30000; // 30 seconds for file uploads

/**
 * POST handler for /api/chat/attachments
 * Proxies file uploads to the FastAPI backend with authentication
 */
export async function POST(req: NextRequest) {
  try {
    // Basic validation before forwarding to backend
    const contentType = req.headers.get("content-type");
    if (!contentType || !contentType.includes("multipart/form-data")) {
      return new Response(
        JSON.stringify({
          error: "Invalid content type",
          code: "INVALID_CONTENT_TYPE",
        }),
        {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Get form data to check file count and basic validation
    const formData = await req.formData();
    const files: File[] = [];

    // Extract files from form data
    for (const entry of Array.from(formData.entries())) {
      const [key, value] = entry;
      if (value instanceof File && value.size > 0) {
        files.push(value);
      }
    }

    // Basic frontend validation
    if (files.length === 0) {
      return new Response(
        JSON.stringify({
          error: "No files uploaded",
          code: "NO_FILES",
        }),
        {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    if (files.length > MAX_FILES_PER_REQUEST) {
      return new Response(
        JSON.stringify({
          error: `Maximum ${MAX_FILES_PER_REQUEST} files allowed per request`,
          code: "TOO_MANY_FILES",
        }),
        {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Quick size check before sending to backend
    for (const file of files) {
      if (file.size > MAX_FILE_SIZE) {
        return new Response(
          JSON.stringify({
            error: `File "${file.name}" exceeds maximum size of ${MAX_FILE_SIZE / 1024 / 1024}MB`,
            code: "FILE_TOO_LARGE",
          }),
          {
            status: 400,
            headers: { "Content-Type": "application/json" },
          }
        );
      }
    }

    // Determine upload endpoint based on file count
    const endpoint =
      files.length === 1 ? "/api/attachments/upload" : "/api/attachments/upload/batch";

    // Forward request to backend API
    const backendUrl = `${BACKEND_API_URL}${endpoint}`;

    // Get authentication token from request headers
    const authHeader = req.headers.get("authorization");

    // Create new FormData for backend request
    const backendFormData = new FormData();

    if (files.length === 1) {
      // Single file upload
      backendFormData.append("file", files[0]);
    } else {
      // Batch upload
      files.forEach((file, index) => {
        backendFormData.append("files", file);
      });
    }

    // Prepare headers for backend request
    const backendHeaders: HeadersInit = {};
    if (authHeader) {
      backendHeaders.Authorization = authHeader;
    }

    // Forward to backend with timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT);

    try {
      const backendResponse = await fetch(backendUrl, {
        method: "POST",
        headers: backendHeaders,
        body: backendFormData,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Get response data
      const responseData = await backendResponse.json();

      // Transform backend response to match frontend expectations
      if (backendResponse.ok) {
        if (files.length === 1) {
          // Single file response - match backend FileUploadResponse model
          const fileData = responseData;
          return new Response(
            JSON.stringify({
              files: [
                {
                  id: fileData.file_id,
                  name: fileData.filename,
                  size: fileData.file_size,
                  type: fileData.mime_type,
                  url: `/api/attachments/${fileData.file_id}/download`, // Backend download endpoint
                  status: fileData.processing_status, // Use processing_status instead of upload_status
                },
              ],
              urls: [`/api/attachments/${fileData.file_id}/download`], // Backward compatibility
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json" },
            }
          );
        }
        // Batch upload response
        const batchData = responseData;
        const transformedFiles = batchData.successful_uploads.map((file: any) => ({
          id: file.file_id,
          name: file.filename,
          size: file.file_size,
          type: file.mime_type,
          url: `/api/attachments/${file.file_id}/download`,
          status: file.processing_status, // Use processing_status instead of upload_status
        }));

        return new Response(
          JSON.stringify({
            files: transformedFiles,
            urls: transformedFiles.map((f: any) => f.url),
            batch_summary: {
              total: batchData.total_files,
              successful: batchData.successful_count,
              failed: batchData.failed_count,
              errors: batchData.failed_uploads,
            },
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }
        );
      }
      // Forward backend error response
      return new Response(
        JSON.stringify({
          error: responseData.detail || "Backend upload failed",
          code: "BACKEND_ERROR",
          backend_response: responseData,
        }),
        {
          status: backendResponse.status,
          headers: { "Content-Type": "application/json" },
        }
      );
    } catch (fetchError) {
      clearTimeout(timeoutId);

      if (fetchError instanceof Error && fetchError.name === "AbortError") {
        return new Response(
          JSON.stringify({
            error: "Upload timeout",
            code: "TIMEOUT_ERROR",
          }),
          {
            status: 408,
            headers: { "Content-Type": "application/json" },
          }
        );
      }

      throw fetchError;
    }
  } catch (error) {
    console.error("Error proxying file upload to backend:", error);
    return new Response(
      JSON.stringify({
        error: "Failed to process file upload",
        code: "PROXY_ERROR",
        details: error instanceof Error ? error.message : "Unknown error",
      }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}

/**
 * GET handler for retrieving file metadata
 * Proxies requests to backend API
 */
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const fileId = searchParams.get("id");

    if (!fileId) {
      return new Response(
        JSON.stringify({
          error: "File ID is required",
          code: "MISSING_FILE_ID",
        }),
        {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Forward to backend
    const backendUrl = `${BACKEND_API_URL}/api/attachments/${fileId}`;
    const authHeader = req.headers.get("authorization");

    const backendHeaders: HeadersInit = {};
    if (authHeader) {
      backendHeaders.Authorization = authHeader;
    }

    const backendResponse = await fetch(backendUrl, {
      method: "GET",
      headers: backendHeaders,
    });

    const responseData = await backendResponse.json();

    if (backendResponse.ok) {
      return new Response(JSON.stringify(responseData), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(
      JSON.stringify({
        error: responseData.detail || "Failed to retrieve file metadata",
        code: "BACKEND_ERROR",
      }),
      {
        status: backendResponse.status,
        headers: { "Content-Type": "application/json" },
      }
    );
  } catch (error) {
    console.error("Error retrieving file metadata:", error);
    return new Response(
      JSON.stringify({
        error: "Failed to retrieve file metadata",
        code: "PROXY_ERROR",
      }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}
