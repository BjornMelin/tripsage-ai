/**
 * @fileoverview Activity tool model output schemas.
 */

import { z } from "zod";

// ===== MODEL OUTPUT SCHEMAS =====

/** Activity entry for model consumption. Fields match source activitySchema requirements. */
const activityEntryModelOutputSchema = z.strictObject({
  duration: z.number(),
  id: z.string(),
  location: z.string(),
  name: z.string(),
  price: z.number(),
  rating: z.number(),
  type: z.string(),
});

/** Activity search result metadata for model consumption. */
const activityMetadataModelOutputSchema = z.strictObject({
  primarySource: z.enum(["googleplaces", "ai_fallback", "mixed"]),
  total: z.number().int(),
});

/** Activity search result output schema for model consumption. */
export const activityModelOutputSchema = z.strictObject({
  activities: z.array(activityEntryModelOutputSchema),
  metadata: activityMetadataModelOutputSchema,
});

export type ActivityModelOutput = z.infer<typeof activityModelOutputSchema>;
