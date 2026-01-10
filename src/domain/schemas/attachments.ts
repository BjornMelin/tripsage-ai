/**
 * @fileoverview Attachment schemas for Supabase Storage.
 */

import { z } from "zod";
import {
  OFFSET_PAGINATION_QUERY_SCHEMA,
  OFFSET_PAGINATION_RESPONSE_SCHEMA,
} from "./shared/pagination";

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

function withAttachmentContextRules<T extends z.ZodTypeAny>(schema: T) {
  return schema
    .refine(
      (data) => {
        if (!data || typeof data !== "object") return false;
        const record = data as Record<string, unknown>;
        return record.chatId !== undefined || record.tripId !== undefined;
      },
      {
        error: "Either chatId or tripId is required.",
        path: ["chatId"],
      }
    )
    .refine(
      (data) => {
        if (!data || typeof data !== "object") return false;
        const record = data as Record<string, unknown>;
        return record.chatMessageId === undefined || record.chatId !== undefined;
      },
      {
        error: "chatId is required when chatMessageId is provided.",
        path: ["chatId"],
      }
    );
}

/** Schema for validating upload options (trip/message context). */
export const attachmentUploadOptionsSchema = withAttachmentContextRules(
  z.strictObject({
    chatId: z.uuid().optional(),
    chatMessageId: z.coerce.number().int().nonnegative().optional(),
    tripId: z.coerce.number().int().nonnegative().optional(),
  })
);

export type AttachmentUploadOptions = z.infer<typeof attachmentUploadOptionsSchema>;

/** Schema for a single file to be uploaded via signed upload URL. */
export const attachmentSignedUploadFileSchema = z.strictObject({
  mimeType: z
    .string()
    .trim()
    .min(1)
    .refine((value) => isAllowedMimeType(value), {
      error: `Invalid mime type. Allowed: ${ATTACHMENT_ALLOWED_MIME_TYPES.join(", ")}`,
    }),
  originalName: z.string().trim().min(1).max(260),
  size: z
    .number()
    .int()
    .positive()
    .max(ATTACHMENT_MAX_FILE_SIZE, {
      error: `File exceeds maximum size of ${Math.floor(ATTACHMENT_MAX_FILE_SIZE / 1024 / 1024)}MB`,
    }),
});

export type AttachmentSignedUploadFile = z.infer<
  typeof attachmentSignedUploadFileSchema
>;

/** Request schema for creating signed upload URLs + metadata records. */
export const attachmentCreateSignedUploadRequestSchema = withAttachmentContextRules(
  z.strictObject({
    chatId: z.uuid().optional(),
    chatMessageId: z.coerce.number().int().nonnegative().optional(),
    files: z.array(attachmentSignedUploadFileSchema).min(1).max(ATTACHMENT_MAX_FILES),
    tripId: z.coerce.number().int().nonnegative().optional(),
  })
);

export type AttachmentCreateSignedUploadRequest = z.infer<
  typeof attachmentCreateSignedUploadRequestSchema
>;

// ===== LIST QUERY SCHEMAS =====

/** Schema for attachment listing query parameters. */
export const attachmentListQuerySchema = OFFSET_PAGINATION_QUERY_SCHEMA.extend({
  chatId: z.uuid().optional(),
  chatMessageId: z.coerce.number().int().nonnegative().optional(),
  tripId: z.coerce.number().int().nonnegative().optional(),
});

export type AttachmentListQuery = z.infer<typeof attachmentListQuerySchema>;

// ===== RESPONSE SCHEMAS =====

/** Schema for a single signed upload entry. */
export const attachmentSignedUploadSchema = z.strictObject({
  attachmentId: z.uuid(),
  mimeType: z.string(),
  originalName: z.string(),
  path: z.string(),
  signedUrl: z.url(),
  size: z.number().int().nonnegative(),
  token: z.string(),
});

export type AttachmentSignedUpload = z.infer<typeof attachmentSignedUploadSchema>;

/** Schema for the signed upload response payload. */
export const attachmentCreateSignedUploadResponseSchema = z.strictObject({
  uploads: z.array(attachmentSignedUploadSchema),
});

export type AttachmentCreateSignedUploadResponse = z.infer<
  typeof attachmentCreateSignedUploadResponseSchema
>;

/** Schema for attachment upload status values. */
export const attachmentUploadStatusSchema = z.enum([
  "uploading",
  "completed",
  "failed",
]);

export type AttachmentUploadStatus = z.infer<typeof attachmentUploadStatusSchema>;

/** Schema for an attachment file in listings. */
export const attachmentFileSchema = z.strictObject({
  chatId: z.uuid().nullable(),
  chatMessageId: z.number().int().nonnegative().nullable(),
  createdAt: z.string().datetime(),
  id: z.uuid(),
  mimeType: z.string(),
  name: z.string(),
  originalName: z.string(),
  size: z.number().int().nonnegative(),
  tripId: z.number().int().nonnegative().nullable(),
  updatedAt: z.string().datetime(),
  uploadStatus: attachmentUploadStatusSchema,
  url: z.url(),
});

export type AttachmentFile = z.infer<typeof attachmentFileSchema>;

/** Schema for pagination metadata. */
export const paginationSchema = OFFSET_PAGINATION_RESPONSE_SCHEMA;

export type Pagination = z.infer<typeof paginationSchema>;

/** Schema for the attachment list response. */
export const attachmentListResponseSchema = z.strictObject({
  items: z.array(attachmentFileSchema),
  pagination: paginationSchema,
});

export type AttachmentListResponse = z.infer<typeof attachmentListResponseSchema>;

// ===== TOOL INPUT SCHEMAS =====

/** Tool input schema for listing attachments in a chat session. */
export const attachmentsListToolInputSchema = z.strictObject({
  chatId: z.uuid(),
  limit: z.number().int().min(1).max(20).default(10),
});

export type AttachmentsListToolInput = z.infer<typeof attachmentsListToolInputSchema>;

/** Tool output schema for attachmentsList. */
export const attachmentsListToolOutputSchema = z.strictObject({
  items: z.array(
    z.strictObject({
      id: z.uuid(),
      mimeType: z.string(),
      originalName: z.string(),
      size: z.number().int().nonnegative(),
      uploadStatus: attachmentUploadStatusSchema,
      url: z.url(),
    })
  ),
});

export type AttachmentsListToolOutput = z.infer<typeof attachmentsListToolOutputSchema>;

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
