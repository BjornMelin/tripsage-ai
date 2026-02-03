/**
 * @fileoverview Image-related schemas for proxying and validation.
 */

import { z } from "zod";

// ===== CORE SCHEMAS =====

export const remoteImageProxyRequestSchema = z.strictObject({
  url: z.preprocess(
    (value) => (typeof value === "string" ? value.trim() : value),
    z.url().max(2048, { error: "Image URL is too long" })
  ),
});

export type RemoteImageProxyRequest = z.infer<typeof remoteImageProxyRequestSchema>;

// ===== TOOL INPUT SCHEMAS =====
