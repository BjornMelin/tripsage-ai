/**
 * @fileoverview Helpers for UI attachments mapping and validation.
 */

import type { UIMessage } from "ai";

/**
 * Type representing the result of attachment validation.
 */
export type Validation = { valid: true } | { valid: false; reason: string };

/**
 * Validates that any file parts are image/* and contain a media type.
 *
 * @param messages - Array of UI messages to validate for attachments.
 * @returns Validation result indicating success or failure with reason.
 */
export function validateImageAttachments(messages: UIMessage[]): Validation {
  for (const m of messages) {
    const parts = (m as any).parts as Array<any> | undefined;
    if (!Array.isArray(parts)) continue;
    for (const p of parts) {
      if (p?.type === "file") {
        const mediaType: string | undefined = p.media_type || p.mediaType;
        if (!mediaType) return { valid: false, reason: "missing_media_type" };
        if (!mediaType.startsWith("image/"))
          return { valid: false, reason: "unsupported_media_type" };
      }
    }
  }
  return { valid: true } as const;
}

/**
 * Converts UI file parts to model file format for AI SDK compatibility.
 *
 * @param part - UI message part to convert.
 * @returns FilePart object for AI SDK or undefined if not convertible.
 */
export function convertUiFilePartToImage(part: any) {
  if (part?.type === "file") {
    const mediaType: string | undefined = part.media_type || part.mediaType;
    if (mediaType?.startsWith("image/")) {
      return {
        type: "image" as const,
        image: part.url,
        mimeType: mediaType,
      };
    }
  }
  return null;
}

/**
 * Extracts text content from UI messages for token budgeting purposes.
 *
 * @param messages - Array of UI messages to extract text from.
 * @returns Array of text strings found in the messages.
 */
export function extractTexts(messages: UIMessage[]): string[] {
  const texts: string[] = [];
  for (const m of messages) {
    const parts = (m as any).parts as Array<any> | undefined;
    if (!Array.isArray(parts)) continue;
    for (const p of parts) {
      if (p?.type === "text" && typeof p.text === "string") texts.push(p.text);
    }
  }
  return texts;
}
