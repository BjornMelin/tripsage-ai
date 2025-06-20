/**
 * Comprehensive Zod schemas for Zustand store state validation
 * Runtime validation for all store state mutations and data
 */

import { z } from "zod";

// Common validation patterns
const timestampSchema = z.string().datetime();
const uuidSchema = z.string().uuid();
const emailSchema = z.string().email();
const positiveNumberSchema = z.number().positive();
const nonNegativeNumberSchema = z.number().nonnegative();

// Base store state patterns
const loadingStateSchema = z.object({
  isLoading: z.boolean(),
  error: z.string().nullable(),
  lastUpdated: timestampSchema.optional(),
});

const paginationStateSchema = z.object({
  page: z.number().int().positive(),
  pageSize: z.number().int().positive().max(100),
  total: nonNegativeNumberSchema,
  hasNext: z.boolean(),
  hasPrevious: z.boolean(),
});

// Auth store schema
export const authStoreStateSchema = z.object({
  user: z
    .object({
      id: uuidSchema,
      email: emailSchema,
      firstName: z.string(),
      lastName: z.string(),
      role: z.enum(["user", "admin", "moderator"]),
      avatar: z.string().url().optional(),
      emailVerified: z.boolean(),
      twoFactorEnabled: z.boolean(),
    })
    .nullable(),
  session: z
    .object({
      accessToken: z.string(),
      refreshToken: z.string(),
      expiresAt: timestampSchema,
    })
    .nullable(),
  isAuthenticated: z.boolean(),
  isLoading: z.boolean(),
  error: z.string().nullable(),
  lastAuthCheck: timestampSchema.optional(),
});

export const authStoreActionsSchema = z.object({
  signIn: z.function(),
  signOut: z.function(),
  signUp: z.function(),
  refreshToken: z.function(),
  updateUser: z.function(),
  clearError: z.function(),
  checkAuth: z.function(),
});

// User store schema
export const userStoreStateSchema = z.object({
  profile: z
    .object({
      id: uuidSchema,
      email: emailSchema,
      firstName: z.string(),
      lastName: z.string(),
      displayName: z.string().optional(),
      bio: z.string().optional(),
      avatar: z.string().url().optional(),
      timezone: z.string().optional(),
      language: z.string().optional(),
      currency: z.string().length(3).optional(),
      preferences: z.record(z.unknown()).optional(),
    })
    .nullable(),
  ...loadingStateSchema.shape,
});

export const userStoreActionsSchema = z.object({
  fetchProfile: z.function(),
  updateProfile: z.function(),
  updatePreferences: z.function(),
  uploadAvatar: z.function(),
  deleteAccount: z.function(),
  reset: z.function(),
});

// Search store schema
export const searchStoreStateSchema = z.object({
  currentSearchType: z
    .enum(["flight", "accommodation", "activity", "destination"])
    .nullable(),
  currentParams: z.record(z.unknown()).nullable(),
  results: z.object({
    flights: z.array(z.unknown()).optional(),
    accommodations: z.array(z.unknown()).optional(),
    activities: z.array(z.unknown()).optional(),
    destinations: z.array(z.unknown()).optional(),
  }),
  filters: z.record(z.unknown()),
  sorting: z
    .object({
      field: z.string(),
      direction: z.enum(["asc", "desc"]),
    })
    .optional(),
  pagination: paginationStateSchema.optional(),
  recentSearches: z.array(
    z.object({
      id: z.string(),
      type: z.enum(["flight", "accommodation", "activity", "destination"]),
      params: z.record(z.unknown()),
      timestamp: timestampSchema,
    })
  ),
  savedSearches: z.array(
    z.object({
      id: z.string(),
      name: z.string(),
      type: z.enum(["flight", "accommodation", "activity", "destination"]),
      params: z.record(z.unknown()),
      createdAt: timestampSchema,
      lastUsed: timestampSchema.optional(),
    })
  ),
  ...loadingStateSchema.shape,
});

export const searchStoreActionsSchema = z.object({
  setSearchType: z.function(),
  updateParams: z.function(),
  executeSearch: z.function(),
  clearResults: z.function(),
  setFilters: z.function(),
  setSorting: z.function(),
  loadMore: z.function(),
  saveSearch: z.function(),
  loadSavedSearch: z.function(),
  deleteSavedSearch: z.function(),
  addToRecentSearches: z.function(),
  clearRecentSearches: z.function(),
  reset: z.function(),
});

// Trip store schema
export const tripStoreStateSchema = z.object({
  trips: z.array(
    z.object({
      id: uuidSchema,
      title: z.string(),
      description: z.string().optional(),
      destination: z.string(),
      startDate: z.string().date(),
      endDate: z.string().date(),
      status: z.enum(["planning", "booked", "active", "completed", "cancelled"]),
      budget: z
        .object({
          total: positiveNumberSchema,
          spent: nonNegativeNumberSchema,
          currency: z.string().length(3),
        })
        .optional(),
      travelers: z.array(
        z.object({
          id: uuidSchema.optional(),
          name: z.string(),
          email: emailSchema.optional(),
          role: z.enum(["owner", "collaborator", "viewer"]),
        })
      ),
      itinerary: z.array(z.unknown()),
      createdAt: timestampSchema,
      updatedAt: timestampSchema,
    })
  ),
  currentTrip: z
    .object({
      id: uuidSchema,
      title: z.string(),
      destination: z.string(),
      startDate: z.string().date(),
      endDate: z.string().date(),
      status: z.enum(["planning", "booked", "active", "completed", "cancelled"]),
      budget: z
        .object({
          total: positiveNumberSchema,
          spent: nonNegativeNumberSchema,
          currency: z.string().length(3),
        })
        .optional(),
      travelers: z.array(z.unknown()),
      itinerary: z.array(z.unknown()),
    })
    .nullable(),
  filters: z.object({
    status: z
      .array(z.enum(["planning", "booked", "active", "completed", "cancelled"]))
      .optional(),
    dateRange: z
      .object({
        start: z.string().date(),
        end: z.string().date(),
      })
      .optional(),
    search: z.string().optional(),
  }),
  sorting: z.object({
    field: z.enum(["createdAt", "startDate", "title", "status"]),
    direction: z.enum(["asc", "desc"]),
  }),
  ...loadingStateSchema.shape,
  pagination: paginationStateSchema,
});

export const tripStoreActionsSchema = z.object({
  fetchTrips: z.function(),
  createTrip: z.function(),
  updateTrip: z.function(),
  deleteTrip: z.function(),
  duplicateTrip: z.function(),
  setCurrentTrip: z.function(),
  clearCurrentTrip: z.function(),
  updateFilters: z.function(),
  clearFilters: z.function(),
  setSorting: z.function(),
  loadMore: z.function(),
  refresh: z.function(),
  reset: z.function(),
});

// Chat store schema
export const chatStoreStateSchema = z.object({
  conversations: z.array(
    z.object({
      id: uuidSchema,
      title: z.string(),
      messages: z.array(
        z.object({
          id: uuidSchema,
          role: z.enum(["user", "assistant", "system"]),
          content: z.string(),
          timestamp: timestampSchema,
          metadata: z.record(z.unknown()).optional(),
        })
      ),
      status: z.enum(["active", "archived", "deleted"]),
      createdAt: timestampSchema,
      updatedAt: timestampSchema,
    })
  ),
  currentConversation: z
    .object({
      id: uuidSchema,
      title: z.string(),
      messages: z.array(z.unknown()),
      status: z.enum(["active", "archived", "deleted"]),
    })
    .nullable(),
  isTyping: z.boolean(),
  typingUsers: z.array(z.string()),
  connectionStatus: z.enum(["connected", "connecting", "disconnected", "error"]),
  ...loadingStateSchema.shape,
});

export const chatStoreActionsSchema = z.object({
  fetchConversations: z.function(),
  createConversation: z.function(),
  setCurrentConversation: z.function(),
  sendMessage: z.function(),
  editMessage: z.function(),
  deleteMessage: z.function(),
  archiveConversation: z.function(),
  deleteConversation: z.function(),
  setTyping: z.function(),
  addTypingUser: z.function(),
  removeTypingUser: z.function(),
  setConnectionStatus: z.function(),
  reset: z.function(),
});

// UI store schema
export const uiStoreStateSchema = z.object({
  theme: z.enum(["light", "dark", "system"]),
  sidebar: z.object({
    isOpen: z.boolean(),
    isCollapsed: z.boolean(),
    width: z.number().positive(),
  }),
  modals: z.record(
    z.object({
      isOpen: z.boolean(),
      data: z.unknown().optional(),
    })
  ),
  notifications: z.array(
    z.object({
      id: z.string(),
      type: z.enum(["success", "error", "warning", "info"]),
      title: z.string(),
      message: z.string(),
      duration: z.number().positive().optional(),
      actions: z
        .array(
          z.object({
            label: z.string(),
            action: z.function(),
          })
        )
        .optional(),
      createdAt: timestampSchema,
    })
  ),
  toasts: z.array(
    z.object({
      id: z.string(),
      type: z.enum(["success", "error", "warning", "info"]),
      title: z.string().optional(),
      description: z.string(),
      duration: z.number().positive().optional(),
      action: z
        .object({
          label: z.string(),
          onClick: z.function(),
        })
        .optional(),
    })
  ),
  breadcrumbs: z.array(
    z.object({
      label: z.string(),
      href: z.string().optional(),
      isActive: z.boolean(),
    })
  ),
  pageLoading: z.boolean(),
  globalError: z.string().nullable(),
});

export const uiStoreActionsSchema = z.object({
  setTheme: z.function(),
  toggleSidebar: z.function(),
  setSidebarCollapsed: z.function(),
  setSidebarWidth: z.function(),
  openModal: z.function(),
  closeModal: z.function(),
  addNotification: z.function(),
  removeNotification: z.function(),
  clearNotifications: z.function(),
  addToast: z.function(),
  removeToast: z.function(),
  clearToasts: z.function(),
  setBreadcrumbs: z.function(),
  setPageLoading: z.function(),
  setGlobalError: z.function(),
  clearGlobalError: z.function(),
  reset: z.function(),
});

// Budget store schema
export const budgetStoreStateSchema = z.object({
  budgets: z.record(
    z.object({
      tripId: uuidSchema,
      total: positiveNumberSchema,
      spent: nonNegativeNumberSchema,
      currency: z.string().length(3),
      categories: z.record(
        z.object({
          allocated: nonNegativeNumberSchema,
          spent: nonNegativeNumberSchema,
        })
      ),
      expenses: z.array(
        z.object({
          id: uuidSchema,
          amount: positiveNumberSchema,
          currency: z.string().length(3),
          category: z.string(),
          description: z.string(),
          date: z.string().date(),
          createdAt: timestampSchema,
        })
      ),
      updatedAt: timestampSchema,
    })
  ),
  currentBudget: z
    .object({
      tripId: uuidSchema,
      total: positiveNumberSchema,
      spent: nonNegativeNumberSchema,
      currency: z.string().length(3),
      categories: z.record(z.unknown()),
      expenses: z.array(z.unknown()),
    })
    .nullable(),
  exchangeRates: z.record(z.number().positive()),
  ...loadingStateSchema.shape,
});

export const budgetStoreActionsSchema = z.object({
  fetchBudget: z.function(),
  createBudget: z.function(),
  updateBudget: z.function(),
  deleteBudget: z.function(),
  addExpense: z.function(),
  updateExpense: z.function(),
  deleteExpense: z.function(),
  updateCategory: z.function(),
  fetchExchangeRates: z.function(),
  convertCurrency: z.function(),
  reset: z.function(),
});

// API Key store schema
export const apiKeyStoreStateSchema = z.object({
  keys: z.array(
    z.object({
      id: uuidSchema,
      name: z.string(),
      service: z.enum(["openai", "anthropic", "google", "amadeus", "skyscanner"]),
      key: z.string(),
      isActive: z.boolean(),
      lastUsed: timestampSchema.optional(),
      usageCount: nonNegativeNumberSchema,
      createdAt: timestampSchema,
    })
  ),
  services: z.record(
    z.object({
      name: z.string(),
      description: z.string(),
      status: z.enum(["connected", "disconnected", "error"]),
      lastCheck: timestampSchema.optional(),
    })
  ),
  ...loadingStateSchema.shape,
});

export const apiKeyStoreActionsSchema = z.object({
  fetchKeys: z.function(),
  createKey: z.function(),
  updateKey: z.function(),
  deleteKey: z.function(),
  toggleKey: z.function(),
  testKey: z.function(),
  checkServiceStatus: z.function(),
  reset: z.function(),
});

// Store validation utilities
export const validateStoreState = <T>(
  schema: z.ZodSchema<T>,
  state: unknown,
  storeName?: string
): T => {
  try {
    return schema.parse(state);
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error(`${storeName || "Store"} state validation failed:`, error.issues);
      throw new Error(
        `Invalid store state: ${error.issues.map((i) => i.message).join(", ")}`
      );
    }
    throw error;
  }
};

export const safeValidateStoreState = <T>(
  schema: z.ZodSchema<T>,
  state: unknown,
  storeName?: string
) => {
  const result = schema.safeParse(state);
  if (!result.success) {
    console.warn(
      `${storeName || "Store"} state validation failed:`,
      result.error.issues
    );
  }
  return result;
};

// Middleware for Zustand store validation
export const storeValidationMiddleware =
  <T>(schema: z.ZodSchema<T>, storeName?: string) =>
  (config: (set: any, get: any, api: any) => T) =>
  (set: any, get: any, api: any) => {
    const store = config(
      (partial: any, replace: any) => {
        const newState = typeof partial === "function" ? partial(get()) : partial;

        if (process.env.NODE_ENV === "development") {
          const mergedState = replace ? newState : { ...get(), ...newState };
          const result = safeValidateStoreState(schema, mergedState, storeName);
          if (!result.success) {
            console.error(
              `Store mutation validation failed for ${storeName}:`,
              result.error.issues
            );
          }
        }

        return set(partial, replace);
      },
      get,
      api
    );

    // Validate initial state
    if (process.env.NODE_ENV === "development") {
      const result = safeValidateStoreState(schema, store, storeName);
      if (!result.success) {
        console.error(
          `Initial store state validation failed for ${storeName}:`,
          result.error.issues
        );
      }
    }

    return store;
  };

// Type exports
export type AuthStoreState = z.infer<typeof authStoreStateSchema>;
export type AuthStoreActions = z.infer<typeof authStoreActionsSchema>;
export type UserStoreState = z.infer<typeof userStoreStateSchema>;
export type UserStoreActions = z.infer<typeof userStoreActionsSchema>;
export type SearchStoreState = z.infer<typeof searchStoreStateSchema>;
export type SearchStoreActions = z.infer<typeof searchStoreActionsSchema>;
export type TripStoreState = z.infer<typeof tripStoreStateSchema>;
export type TripStoreActions = z.infer<typeof tripStoreActionsSchema>;
export type ChatStoreState = z.infer<typeof chatStoreStateSchema>;
export type ChatStoreActions = z.infer<typeof chatStoreActionsSchema>;
export type UIStoreState = z.infer<typeof uiStoreStateSchema>;
export type UIStoreActions = z.infer<typeof uiStoreActionsSchema>;
export type BudgetStoreState = z.infer<typeof budgetStoreStateSchema>;
export type BudgetStoreActions = z.infer<typeof budgetStoreActionsSchema>;
export type ApiKeyStoreState = z.infer<typeof apiKeyStoreStateSchema>;
export type ApiKeyStoreActions = z.infer<typeof apiKeyStoreActionsSchema>;
