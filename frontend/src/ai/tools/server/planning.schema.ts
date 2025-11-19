/**
 * @fileoverview Canonical Zod schema for travel plans.
 * Defines the persisted shape and exported TypeScript type.
 */

import { z } from "zod";

export const isoDate = z.string().regex(/^\d{4}-\d{2}-\d{2}$/u, "must be YYYY-MM-DD");

export const isoDateTime = z.iso.datetime();

export const planComponentsSchema = z.object({
  accommodations: z.array(z.record(z.string(), z.unknown())).default([]),
  activities: z.array(z.record(z.string(), z.unknown())).default([]),
  flights: z.array(z.record(z.string(), z.unknown())).default([]),
  notes: z.array(z.record(z.string(), z.unknown())).default([]),
  transportation: z.array(z.record(z.string(), z.unknown())).default([]),
});

export const planSchema = z.object({
  budget: z.number().min(0).nullable(),
  components: planComponentsSchema,
  createdAt: isoDateTime,
  destinations: z.array(z.string().min(1)).min(1),
  endDate: isoDate,
  finalizedAt: isoDateTime.optional(),
  planId: z.uuid(),
  preferences: z.record(z.string(), z.unknown()).default({}),
  startDate: isoDate,
  status: z.enum(["draft", "finalized"]).default("draft"),
  title: z.string().min(1),
  travelers: z.number().int().min(1).max(50),
  updatedAt: isoDateTime,
  userId: z.string().min(1),
});

export type Plan = z.infer<typeof planSchema>;
