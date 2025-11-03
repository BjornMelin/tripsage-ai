/**
 * @fileoverview Types and schemas for travel deals.
 */
import { z } from "zod";

// Deal type enum
export const DealTypeSchema = z.enum([
  "flight",
  "accommodation",
  "package",
  "activity",
  "transportation",
  "error_fare",
  "flash_sale",
  "promotion",
]);

export type DealType = z.infer<typeof DealTypeSchema>;

// Deal schema
export const DealSchema = z.object({
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
  type: DealTypeSchema,
  updatedAt: z.string().datetime(),
  url: z.string().url(),
  verified: z.boolean().default(false),
});

export type Deal = z.infer<typeof DealSchema>;

// Deal alert schema
export const DealAlertSchema = z.object({
  createdAt: z.string().datetime(),
  dateRange: z
    .object({
      end: z.string().datetime().optional(),
      start: z.string().datetime().optional(),
    })
    .optional(),
  dealType: DealTypeSchema.optional(),
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

export type DealAlert = z.infer<typeof DealAlertSchema>;

// Deal state schema
export const DealStateSchema = z.object({
  alerts: z.array(DealAlertSchema),
  deals: z.record(z.string(), DealSchema),
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
      types: z.array(DealTypeSchema).optional(),
    })
    .optional(),
  isInitialized: z.boolean().default(false),
  lastUpdated: z.string().datetime().nullable(),
  recentlyViewedDeals: z.array(z.string()), // IDs of recently viewed deals
  savedDeals: z.array(z.string()), // IDs of saved deals
});

export type DealState = z.infer<typeof DealStateSchema>;

// Deal notification schema
export const DealNotificationSchema = z.object({
  createdAt: z.string().datetime(),
  dealId: z.string(),
  id: z.string(),
  isRead: z.boolean().default(false),
  message: z.string(),
  title: z.string(),
  userId: z.string(),
});

export type DealNotification = z.infer<typeof DealNotificationSchema>;

// API Request/Response schemas
export const SearchDealsRequestSchema = z.object({
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
  types: z.array(DealTypeSchema).optional(),
  verified: z.boolean().optional(),
});

export type SearchDealsRequest = z.infer<typeof SearchDealsRequestSchema>;

export const CreateDealAlertRequestSchema = z.object({
  dateRange: z
    .object({
      end: z.string().datetime().optional(),
      start: z.string().datetime().optional(),
    })
    .optional(),
  dealType: DealTypeSchema.optional(),
  destination: z.string().optional(),
  maxPrice: z.number().positive().optional(),
  minDiscount: z.number().min(0).max(100).optional(),
  notificationType: z.enum(["email", "push", "both"]).default("both"),
  origin: z.string().optional(),
});

export type CreateDealAlertRequest = z.infer<typeof CreateDealAlertRequestSchema>;

// Stats
export const DealStatsSchema = z.object({
  avgDiscount: z.number().nonnegative(),
  avgSavings: z.number().nonnegative(),
  byDestination: z.record(z.string(), z.number().nonnegative()),
  byType: z.record(DealTypeSchema, z.number().nonnegative()),
  totalCount: z.number().nonnegative(),
});

export type DealStats = z.infer<typeof DealStatsSchema>;
