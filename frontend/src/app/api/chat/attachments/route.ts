import type { NextRequest } from "next/server";
import { randomUUID } from "crypto";
import { z } from "zod";
import path from "path";
import { writeFile, mkdir } from "fs/promises";

// Configuration
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const MAX_FILES_PER_REQUEST = 5;
const ALLOWED_FILE_TYPES = [
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
  "application/pdf",
  "text/plain",
  "text/csv",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
];

const ALLOWED_EXTENSIONS = [
  ".jpg",
  ".jpeg",
  ".png",
  ".gif",
  ".webp",
  ".pdf",
  ".txt",
  ".csv",
  ".xls",
  ".xlsx",
];

// Mock in-memory storage for uploaded files
// In production, you would use proper file storage like S3, Supabase Storage, etc.
const UPLOADS_DIR = path.join(process.cwd(), "public", "uploads");

// Create a temporary in-memory cache for this example
const fileCache = new Map<
  string,
  { name: string; type: string; size: number }
>();

// File validation schema
const FileValidationSchema = z.object({
  name: z.string().min(1).max(255),
  type: z.string(),
  size: z
    .number()
    .max(
      MAX_FILE_SIZE,
      `File size must not exceed ${MAX_FILE_SIZE / 1024 / 1024}MB`
    ),
});

/**
 * Validate file type and extension
 */
function isValidFileType(file: File): boolean {
  const ext = path.extname(file.name).toLowerCase();
  return (
    ALLOWED_FILE_TYPES.includes(file.type) && ALLOWED_EXTENSIONS.includes(ext)
  );
}

/**
 * Sanitize filename for security
 */
function sanitizeFilename(filename: string): string {
  // Remove any path traversal attempts
  const basename = path.basename(filename);
  // Replace unsafe characters
  return basename.replace(/[^a-zA-Z0-9.-]/g, "_");
}

/**
 * POST handler for /api/chat/attachments
 * Handles secure file uploads with validation
 */
export async function POST(req: NextRequest) {
  try {
    // Check content type
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

    // Ensure the uploads directory exists
    try {
      await mkdir(UPLOADS_DIR, { recursive: true });
    } catch (error) {
      console.error("Error creating uploads directory:", error);
    }

    // Process form data with files
    const formData = await req.formData();
    const files: File[] = [];
    const errors: string[] = [];

    // Extract files from form data
    for (const entry of Array.from(formData.entries())) {
      const [key, value] = entry;

      if (value instanceof File && value.size > 0) {
        files.push(value);
      }
    }

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

    // Validate each file
    for (const file of files) {
      try {
        // Validate file properties
        FileValidationSchema.parse({
          name: file.name,
          type: file.type,
          size: file.size,
        });

        // Validate file type
        if (!isValidFileType(file)) {
          errors.push(
            `File "${file.name}" has unsupported type. Allowed: images, PDF, text, CSV, Excel`
          );
        }
      } catch (error) {
        if (error instanceof z.ZodError) {
          errors.push(`File "${file.name}": ${error.errors[0].message}`);
        } else {
          errors.push(`File "${file.name}": Validation failed`);
        }
      }
    }

    if (errors.length > 0) {
      return new Response(
        JSON.stringify({
          error: "File validation failed",
          code: "VALIDATION_ERROR",
          details: errors,
        }),
        {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }
      );
    }

    // Process and save valid files
    const savedFiles = await Promise.all(
      files.map(async (file) => {
        const fileId = randomUUID();
        const sanitizedName = sanitizeFilename(file.name);
        const fileExt = path.extname(sanitizedName);
        const uniqueFileName = `${fileId}${fileExt}`;
        const filePath = path.join(UPLOADS_DIR, uniqueFileName);

        // Save to a buffer before writing to file
        const buffer = Buffer.from(await file.arrayBuffer());
        await writeFile(filePath, buffer);

        // Store metadata in memory (in production, use a database)
        fileCache.set(fileId, {
          name: sanitizedName,
          type: file.type,
          size: file.size,
        });

        // Generate public URL
        const publicUrl = `/uploads/${uniqueFileName}`;

        return {
          url: publicUrl,
          id: fileId,
          name: sanitizedName,
          size: file.size,
          type: file.type,
        };
      })
    );

    // Return metadata of saved files
    return new Response(
      JSON.stringify({
        files: savedFiles,
        urls: savedFiles.map((f) => f.url), // Backward compatibility
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }
    );
  } catch (error) {
    console.error("Error processing file upload:", error);
    return new Response(
      JSON.stringify({
        error: "Failed to process file upload",
        code: "UPLOAD_ERROR",
      }),
      {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}
