/**
 * Types for Deals functionality
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
  id: z.string(),
  type: DealTypeSchema,
  title: z.string().min(3).max(100),
  description: z.string().max(500),
  provider: z.string(),
  url: z.string().url(),
  price: z.number().positive(),
  originalPrice: z.number().positive().optional(),
  discountPercentage: z.number().min(0).max(100).optional(),
  currency: z.string().length(3),
  destination: z.string(),
  origin: z.string().optional(),
  startDate: z.string().datetime().optional(),
  endDate: z.string().datetime().optional(),
  expiryDate: z.string().datetime(), // When the deal expires
  imageUrl: z.string().url().optional(),
  tags: z.array(z.string()).optional(),
  featured: z.boolean().default(false),
  verified: z.boolean().default(false),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});

export type Deal = z.infer<typeof DealSchema>;

// Deal alert schema
export const DealAlertSchema = z.object({
  id: z.string(),
  userId: z.string(),
  dealType: DealTypeSchema.optional(),
  origin: z.string().optional(),
  destination: z.string().optional(),
  minDiscount: z.number().min(0).max(100).optional(),
  maxPrice: z.number().positive().optional(),
  dateRange: z
    .object({
      start: z.string().datetime().optional(),
      end: z.string().datetime().optional(),
    })
    .optional(),
  isActive: z.boolean().default(true),
  notificationType: z.enum(["email", "push", "both"]).default("both"),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});

export type DealAlert = z.infer<typeof DealAlertSchema>;

// Deal state schema
export const DealStateSchema = z.object({
  deals: z.record(z.string(), DealSchema),
  featuredDeals: z.array(z.string()), // IDs of featured deals
  alerts: z.array(DealAlertSchema),
  savedDeals: z.array(z.string()), // IDs of saved deals
  recentlyViewedDeals: z.array(z.string()), // IDs of recently viewed deals
  filters: z
    .object({
      types: z.array(DealTypeSchema).optional(),
      origins: z.array(z.string()).optional(),
      destinations: z.array(z.string()).optional(),
      providers: z.array(z.string()).optional(),
      minDiscount: z.number().min(0).max(100).optional(),
      maxPrice: z.number().positive().optional(),
      dateRange: z
        .object({
          start: z.string().datetime().optional(),
          end: z.string().datetime().optional(),
        })
        .optional(),
    })
    .optional(),
  lastUpdated: z.string().datetime().nullable(),
  isInitialized: z.boolean().default(false),
});

export type DealState = z.infer<typeof DealStateSchema>;

// Deal notification schema
export const DealNotificationSchema = z.object({
  id: z.string(),
  dealId: z.string(),
  userId: z.string(),
  title: z.string(),
  message: z.string(),
  isRead: z.boolean().default(false),
  createdAt: z.string().datetime(),
});

export type DealNotification = z.infer<typeof DealNotificationSchema>;

// API Request/Response schemas
export const SearchDealsRequestSchema = z.object({
  types: z.array(DealTypeSchema).optional(),
  origin: z.string().optional(),
  destination: z.string().optional(),
  providers: z.array(z.string()).optional(),
  minDiscount: z.number().min(0).max(100).optional(),
  maxPrice: z.number().positive().optional(),
  dateRange: z
    .object({
      start: z.string().datetime().optional(),
      end: z.string().datetime().optional(),
    })
    .optional(),
  featured: z.boolean().optional(),
  verified: z.boolean().optional(),
  limit: z.number().positive().optional(),
  offset: z.number().nonnegative().optional(),
  sort: z.enum(["price", "discount", "expiry", "created"]).optional(),
  sortDirection: z.enum(["asc", "desc"]).optional(),
});

export type SearchDealsRequest = z.infer<typeof SearchDealsRequestSchema>;

export const CreateDealAlertRequestSchema = z.object({
  dealType: DealTypeSchema.optional(),
  origin: z.string().optional(),
  destination: z.string().optional(),
  minDiscount: z.number().min(0).max(100).optional(),
  maxPrice: z.number().positive().optional(),
  dateRange: z
    .object({
      start: z.string().datetime().optional(),
      end: z.string().datetime().optional(),
    })
    .optional(),
  notificationType: z.enum(["email", "push", "both"]).default("both"),
});

export type CreateDealAlertRequest = z.infer<typeof CreateDealAlertRequestSchema>;

// Stats
export const DealStatsSchema = z.object({
  totalCount: z.number().nonnegative(),
  byType: z.record(DealTypeSchema, z.number().nonnegative()),
  byDestination: z.record(z.string(), z.number().nonnegative()),
  avgDiscount: z.number().nonnegative(),
  avgSavings: z.number().nonnegative(),
});

export type DealStats = z.infer<typeof DealStatsSchema>;
