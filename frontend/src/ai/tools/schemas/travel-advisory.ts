/**
 * @fileoverview Centralized Zod schemas for travel advisory tools.
 *
 * Contains input validation schemas for getTravelAdvisory tool.
 */

import { z } from "zod";

/** Schema for travel advisory tool input. */
export const travelAdvisoryInputSchema = z.strictObject({
  destination: z
    .string()
    .min(1, "Destination must be a non-empty string")
    .describe("The destination city, country, or region to get travel advisory for"),
});
