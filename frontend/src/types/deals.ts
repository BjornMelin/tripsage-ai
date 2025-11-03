/**
 * @fileoverview Types and schemas for travel deals.
 */
import { z } from "zod";

// Deal type enum
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

export type DealType = z.infer<typeof DEAL_TYPE_SCHEMA>;

// Deal schema
export const DEAL_SCHEMA = z.object({
  createdAt: z.string().datetime(),
  currency: z.string().length(3),
  description: z.string().max(500),
  destination: z.string(),
  discountPercentage: z.number().min(0).max(100).optional(),
  endDate: z.string().datetime().optional(),
  expiryDate: z.string().datetime(), // When the deal expires
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

export type Deal = z.infer<typeof DEAL_SCHEMA>;

// Deal alert schema
export const DEAL_ALERT_SCHEMA = z.object({
  createdAt: z.string().datetime(),
  dateRange: z
    .object({
      end: z.string().datetime().optional(),
      start: z.string().datetime().optional(),
    })
    .optional(),
  dealType: DEAL_TYPE_SCHEMA.optional(),
  destination: z.string().optional(),
  id: z.string(),
  isActive: z.boolean().default(true),
  maxPrice: z.number().positive().optional(),
  minDiscount: z.number().min(0).max(100).optional(),
  notificationType: z.enum(["email", "push", "both"]).default("both"),
  origin: z.string().optional(),
  updatedAt: z.string().datetime(),
  userId: z.string(),
});

export type DealAlert = z.infer<typeof DEAL_ALERT_SCHEMA>;

// Deal state schema
export const DEAL_STATE_SCHEMA = z.object({
  alerts: z.array(DEAL_ALERT_SCHEMA),
  deals: z.record(z.string(), DEAL_SCHEMA),
  featuredDeals: z.array(z.string()), // IDs of featured deals
  filters: z
    .object({
      dateRange: z
        .object({
          end: z.string().datetime().optional(),
          start: z.string().datetime().optional(),
        })
        .optional(),
      destinations: z.array(z.string()).optional(),
      maxPrice: z.number().positive().optional(),
      minDiscount: z.number().min(0).max(100).optional(),
      origins: z.array(z.string()).optional(),
      providers: z.array(z.string()).optional(),
      types: z.array(DEAL_TYPE_SCHEMA).optional(),
    })
    .optional(),
  isInitialized: z.boolean().default(false),
  lastUpdated: z.string().datetime().nullable(),
  recentlyViewedDeals: z.array(z.string()), // IDs of recently viewed deals
  savedDeals: z.array(z.string()), // IDs of saved deals
});

export type DealState = z.infer<typeof DEAL_STATE_SCHEMA>;

// Deal notification schema
export const DEAL_NOTIFICATION_SCHEMA = z.object({
  createdAt: z.string().datetime(),
  dealId: z.string(),
  id: z.string(),
  isRead: z.boolean().default(false),
  message: z.string(),
  title: z.string(),
  userId: z.string(),
});

export type DealNotification = z.infer<typeof DEAL_NOTIFICATION_SCHEMA>;

// API Request/Response schemas
export const SEARCH_DEALS_REQUEST_SCHEMA = z.object({
  dateRange: z
    .object({
      end: z.string().datetime().optional(),
      start: z.string().datetime().optional(),
    })
    .optional(),
  destination: z.string().optional(),
  featured: z.boolean().optional(),
  limit: z.number().positive().optional(),
  maxPrice: z.number().positive().optional(),
  minDiscount: z.number().min(0).max(100).optional(),
  offset: z.number().nonnegative().optional(),
  origin: z.string().optional(),
  providers: z.array(z.string()).optional(),
  sort: z.enum(["price", "discount", "expiry", "created"]).optional(),
  sortDirection: z.enum(["asc", "desc"]).optional(),
  types: z.array(DEAL_TYPE_SCHEMA).optional(),
  verified: z.boolean().optional(),
});

export type SearchDealsRequest = z.infer<typeof SEARCH_DEALS_REQUEST_SCHEMA>;

export const CREATE_DEAL_ALERT_REQUEST_SCHEMA = z.object({
  dateRange: z
    .object({
      end: z.string().datetime().optional(),
      start: z.string().datetime().optional(),
    })
    .optional(),
  dealType: DEAL_TYPE_SCHEMA.optional(),
  destination: z.string().optional(),
  maxPrice: z.number().positive().optional(),
  minDiscount: z.number().min(0).max(100).optional(),
  notificationType: z.enum(["email", "push", "both"]).default("both"),
  origin: z.string().optional(),
});

export type CreateDealAlertRequest = z.infer<typeof CREATE_DEAL_ALERT_REQUEST_SCHEMA>;

// Stats
export const DEAL_STATS_SCHEMA = z.object({
  avgDiscount: z.number().nonnegative(),
  avgSavings: z.number().nonnegative(),
  byDestination: z.record(z.string(), z.number().nonnegative()),
  byType: z.record(DEAL_TYPE_SCHEMA, z.number().nonnegative()),
  totalCount: z.number().nonnegative(),
});

export type DealStats = z.infer<typeof DEAL_STATS_SCHEMA>;
