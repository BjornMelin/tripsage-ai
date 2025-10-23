"use cache: private";
import { revalidateTag } from "next/cache";
import type { NextRequest } from "next/server";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB per file
const MAX_FILES_PER_REQUEST = 5;
const BACKEND_API_URL = process.env.BACKEND_API_URL || "http://localhost:8001";

export async function POST(req: NextRequest) {
  try {
    // Validate content type
    const contentType = req.headers.get("content-type");
    if (!contentType?.includes("multipart/form-data")) {
      return Response.json(
        { error: "Invalid content type", code: "INVALID_CONTENT_TYPE" },
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
      return Response.json(
        { error: "No files uploaded", code: "NO_FILES" },
        { status: 400 }
      );
    }

    if (files.length > MAX_FILES_PER_REQUEST) {
      return Response.json(
        {
          error: `Maximum ${MAX_FILES_PER_REQUEST} files allowed per request`,
          code: "TOO_MANY_FILES",
        },
        { status: 400 }
      );
    }

    // Check file sizes
    const oversizedFile = files.find((file) => file.size > MAX_FILE_SIZE);
    if (oversizedFile) {
      return Response.json(
        {
          error: `File "${oversizedFile.name}" exceeds maximum size of ${MAX_FILE_SIZE / 1024 / 1024}MB`,
          code: "FILE_TOO_LARGE",
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
    const headers: HeadersInit = {};
    const authHeader = req.headers.get("authorization");
    if (authHeader) {
      headers.Authorization = authHeader;
    }

    const response = await fetch(`${BACKEND_API_URL}${endpoint}`, {
      method: "POST",
      headers,
      body: backendFormData,
    });

    const data = await response.json();

    if (!response.ok) {
      return Response.json(
        { error: data.detail || "Upload failed", code: "UPLOAD_ERROR" },
        { status: response.status }
      );
    }

    // Transform response
    if (files.length === 1) {
      const payload = {
        files: [
          {
            id: data.file_id,
            name: data.filename,
            size: data.file_size,
            type: data.mime_type,
            url: `/api/attachments/${data.file_id}/download`,
            status: data.processing_status,
          },
        ],
        urls: [`/api/attachments/${data.file_id}/download`],
      };
      try {
        revalidateTag("attachments", "max");
      } catch {
        // Ignore cache revalidation errors in non-Next runtime test environments
      }
      return Response.json(payload);
    }

    // Batch response
    interface UploadedFile {
      file_id: string;
      filename: string;
      file_size: number;
      mime_type: string;
      processing_status: string;
    }
    const transformedFiles = data.successful_uploads.map((file: UploadedFile) => ({
      id: file.file_id,
      name: file.filename,
      size: file.file_size,
      type: file.mime_type,
      url: `/api/attachments/${file.file_id}/download`,
      status: file.processing_status,
    }));

    const resultPayload = {
      files: transformedFiles,
      urls: transformedFiles.map((f: any) => f.url),
    };
    const result = Response.json(resultPayload);
    try {
      revalidateTag("attachments", "max");
    } catch {
      // Ignore cache revalidation errors in non-Next runtime test environments
    }
    return result;
  } catch (error) {
    console.error("File upload error:", error);
    return Response.json(
      { error: "Internal server error", code: "INTERNAL_ERROR" },
      { status: 500 }
    );
  }
}
