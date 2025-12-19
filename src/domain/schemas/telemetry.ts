/**
 * @fileoverview Schemas for telemetry-related API boundaries.
 */

import { z } from "zod";

// ===== API REQUEST SCHEMAS =====

export const TELEMETRY_AI_DEMO_MAX_DETAIL_LENGTH = 2000;

export const telemetryAiDemoRequestSchema = z.strictObject({
  detail: z
    .string()
    .max(TELEMETRY_AI_DEMO_MAX_DETAIL_LENGTH, { error: "detail exceeds limit" })
    .optional(),
  status: z.enum(["success", "error"]),
});

export type TelemetryAiDemoRequest = z.infer<typeof telemetryAiDemoRequestSchema>;
