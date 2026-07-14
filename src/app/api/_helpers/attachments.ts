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
    const parts = m.parts;
    if (!Array.isArray(parts)) continue;
    for (const p of parts) {
      if (p?.type === "file") {
        const mediaType: string | undefined = p.mediaType;
        if (!mediaType) return { reason: "missing_media_type", valid: false };
        const normalizedMediaType = mediaType.trim().toLowerCase();
        if (!normalizedMediaType) return { reason: "missing_media_type", valid: false };
        if (!normalizedMediaType.startsWith("image/"))
          return { reason: "unsupported_media_type", valid: false };
      }
    }
  }
  return { valid: true } as const;
}
