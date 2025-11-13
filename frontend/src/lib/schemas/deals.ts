/**
 * @fileoverview Zod v4 schemas for travel deals, alerts, filters, and store state.
 */

import { z } from "zod";

/** Zod schema for deal category types. */
export const DEAL_TYPE_SCHEMA = z.enum([
  "flight",
  "accommodation",
  "package",
  "activity",
  "transportation",
  "error_fare",
  "flash_sale",
  "promotion",
]);
/** TypeScript type for deal types. */
export type DealType = z.infer<typeof DEAL_TYPE_SCHEMA>;

/**
 * Zod schema for deal entities.
 * Represents travel deals with pricing, dates, and metadata.
 */
export const DEAL_SCHEMA = z.object({
  createdAt: z.string().datetime(),
  currency: z.string().length(3),
  description: z.string().max(500),
  destination: z.string(),
  discountPercentage: z.number().min(0).max(100).optional(),
  endDate: z.string().datetime().optional(),
  expiryDate: z.string().datetime(),
  featured: z.boolean().default(false),
  id: z.string(),
  imageUrl: z.string().url().optional(),
  origin: z.string().optional(),
  originalPrice: z.number().positive().optional(),
  price: z.number().positive(),
  provider: z.string(),
  startDate: z.string().datetime().optional(),
  tags: z.array(z.string()).optional(),
  title: z.string().min(3).max(100),
  type: DEAL_TYPE_SCHEMA,
  updatedAt: z.string().datetime(),
  url: z.string().url(),
  verified: z.boolean().default(false),
});
/** TypeScript type for deal entities. */
export type Deal = z.infer<typeof DEAL_SCHEMA>;

/** Zod schema for deal alert subscriptions. */
export const DEAL_ALERT_SCHEMA = z.object({
  createdAt: z.string().datetime(),
  dealType: DEAL_TYPE_SCHEMA.optional(),
  destination: z.string().optional(),
  id: z.string(),
  isActive: z.boolean().default(true),
  maxPrice: z.number().positive().optional(),
  minDiscount: z.number().min(0).max(100).optional(),
  notificationType: z.enum(["email", "both"]).default("email"),
  origin: z.string().optional(),
  updatedAt: z.string().datetime(),
  userId: z.string().optional(),
});
/** TypeScript type for deal alerts. */
export type DealAlert = z.infer<typeof DEAL_ALERT_SCHEMA>;

/** Zod schema for deal filter criteria. */
export const DEAL_FILTERS_SCHEMA = z.object({
  dateRange: z
    .object({ end: z.string().optional(), start: z.string().optional() })
    .optional(),
  destinations: z.array(z.string()).optional(),
  maxPrice: z.number().positive().optional(),
  minDiscount: z.number().min(0).max(100).optional(),
  origins: z.array(z.string()).optional(),
  providers: z.array(z.string()).optional(),
  types: z.array(DEAL_TYPE_SCHEMA).optional(),
});
/** TypeScript type for deal filters. */
export type DealFilters = z.infer<typeof DEAL_FILTERS_SCHEMA>;

/** Zod schema for deal store state. */
export const DEAL_STATE_SCHEMA = z.object({
  alerts: z.array(DEAL_ALERT_SCHEMA).default([]),
  deals: z.record(z.string(), DEAL_SCHEMA).default({}),
  featuredDeals: z.array(z.string()).default([]),
  filters: DEAL_FILTERS_SCHEMA.optional(),
  isInitialized: z.boolean().default(false),
  lastUpdated: z.string().nullable().default(null),
  recentlyViewedDeals: z.array(z.string()).default([]),
  savedDeals: z.array(z.string()).default([]),
});
/** TypeScript type for deal store state. */
export type DealState = z.infer<typeof DEAL_STATE_SCHEMA>;

/** TypeScript type for computed deal statistics. */
export type DealStats = {
  avgDiscount: number;
  avgSavings: number;
  byDestination: Record<string, number>;
  byType: Record<DealType, number>;
  totalCount: number;
};
