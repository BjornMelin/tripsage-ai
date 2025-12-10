/**
 * @fileoverview Attachment schemas for Supabase Storage.
 *
 * Defines Zod v4 schemas for attachment uploads, listings, and responses.
 */

import { z } from "zod";

// ===== CONSTANTS =====

/**
 * Allowed MIME types for attachment uploads.
 *
 * Note: SVG intentionally excluded due to XSS risk (can contain JavaScript).
 */
export const ATTACHMENT_ALLOWED_MIME_TYPES = [
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "text/csv",
] as const;

/** Maximum file size in bytes (10MB). */
export const ATTACHMENT_MAX_FILE_SIZE = 10 * 1024 * 1024;

/** Maximum number of files per upload request. */
export const ATTACHMENT_MAX_FILES = 5;

/** Maximum total payload size in bytes (50MB). */
export const ATTACHMENT_MAX_TOTAL_SIZE = 50 * 1024 * 1024;

// ===== UPLOAD SCHEMAS =====

/** Schema for validating upload options (trip/message context). */
export const attachmentUploadOptionsSchema = z.strictObject({
  chatMessageId: z.coerce.number().int().nonnegative().optional(),
  tripId: z.coerce.number().int().nonnegative().optional(),
});

export type AttachmentUploadOptions = z.infer<typeof attachmentUploadOptionsSchema>;

// ===== LIST QUERY SCHEMAS =====

/** Schema for attachment listing query parameters. */
export const attachmentListQuerySchema = z.strictObject({
  chatMessageId: z.coerce.number().int().nonnegative().optional(),
  limit: z.coerce.number().int().min(1).max(100).default(20),
  offset: z.coerce.number().int().min(0).default(0),
  tripId: z.coerce.number().int().nonnegative().optional(),
});

export type AttachmentListQuery = z.infer<typeof attachmentListQuerySchema>;

// ===== RESPONSE SCHEMAS =====

/** Schema for a single uploaded file response. */
export const uploadedFileSchema = z.strictObject({
  id: z.uuid(),
  name: z.string(),
  size: z.number().int().nonnegative(),
  status: z.enum(["uploading", "completed", "failed"]),
  type: z.string(),
  url: z.url().nullable(),
});

export type UploadedFile = z.infer<typeof uploadedFileSchema>;

/** Schema for the upload response payload. */
export const uploadResponseSchema = z.strictObject({
  files: z.array(uploadedFileSchema),
  urls: z.array(z.url()),
});

export type UploadResponse = z.infer<typeof uploadResponseSchema>;

/** Schema for an attachment file in listings. */
export const attachmentFileSchema = z.strictObject({
  chatMessageId: z.number().int().nonnegative().nullable(),
  createdAt: z.string().datetime(),
  id: z.uuid(),
  mimeType: z.string(),
  name: z.string(),
  originalName: z.string(),
  size: z.number().int().nonnegative(),
  tripId: z.number().int().nonnegative().nullable(),
  updatedAt: z.string().datetime(),
  uploadStatus: z.enum(["uploading", "completed", "failed"]),
  url: z.url(),
});

export type AttachmentFile = z.infer<typeof attachmentFileSchema>;

/** Schema for pagination metadata. */
export const paginationSchema = z.strictObject({
  hasMore: z.boolean(),
  limit: z.number().int().positive(),
  nextOffset: z.number().int().nonnegative().nullable(),
  offset: z.number().int().nonnegative(),
  total: z.number().int().nonnegative(),
});

export type Pagination = z.infer<typeof paginationSchema>;

/** Schema for the attachment list response. */
export const attachmentListResponseSchema = z.strictObject({
  items: z.array(attachmentFileSchema),
  pagination: paginationSchema,
});

export type AttachmentListResponse = z.infer<typeof attachmentListResponseSchema>;

// ===== HELPER FUNCTIONS =====

/**
 * Check if a MIME type is allowed for uploads.
 *
 * @param mimeType - MIME type to check.
 * @returns True if the MIME type is allowed.
 */
export function isAllowedMimeType(mimeType: string): boolean {
  return (ATTACHMENT_ALLOWED_MIME_TYPES as readonly string[]).includes(mimeType);
}

/**
 * Sanitize a filename for safe storage.
 *
 * Removes path components, limits length, and replaces special characters.
 *
 * @param filename - Original filename.
 * @returns Sanitized filename.
 */
export function sanitizeFilename(filename: string): string {
  // Remove path components
  const basename = filename.split(/[/\\]/).pop() ?? filename;

  // Replace special characters with underscores
  const sanitized = basename
    // biome-ignore lint/suspicious/noControlCharactersInRegex: intentional - filter out control chars for security
    .replace(/[<>:"/\\|?*\x00-\x1f]/g, "_")
    .replace(/\s+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_|_$/g, "");

  const safe = sanitized.length > 0 ? sanitized : "file";

  // Limit length (preserve extension)
  const maxLength = 100;
  if (safe.length <= maxLength) {
    return safe;
  }

  const lastDot = safe.lastIndexOf(".");
  if (lastDot === -1 || lastDot < safe.length - 10) {
    return safe.slice(0, maxLength);
  }

  const extension = safe.slice(lastDot);
  const name = safe.slice(0, lastDot);
  const maxNameLength = maxLength - extension.length;
  return name.slice(0, maxNameLength) + extension;
}
