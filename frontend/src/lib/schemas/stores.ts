/**
 * Zod schemas for Zustand store state validation
 * Runtime validation for all store state mutations and data
 */

import { z } from "zod";

// Common validation patterns
const TIMESTAMP_SCHEMA = z.string().datetime();
const UUID_SCHEMA = z.string().uuid();
const EMAIL_SCHEMA = z.string().email();
const POSITIVE_NUMBER_SCHEMA = z.number().positive();
const NON_NEGATIVE_NUMBER_SCHEMA = z.number().nonnegative();

// Base store state patterns
const LOADING_STATE_SCHEMA = z.object({
  error: z.string().nullable(),
  isLoading: z.boolean(),
  lastUpdated: TIMESTAMP_SCHEMA.optional(),
});

const PAGINATION_STATE_SCHEMA = z.object({
  hasNext: z.boolean(),
  hasPrevious: z.boolean(),
  page: z.number().int().positive(),
  pageSize: z.number().int().positive().max(100),
  total: NON_NEGATIVE_NUMBER_SCHEMA,
});

// Auth store schema
export const authStoreStateSchema = z.object({
  error: z.string().nullable(),
  isAuthenticated: z.boolean(),
  isLoading: z.boolean(),
  lastAuthCheck: TIMESTAMP_SCHEMA.optional(),
  session: z
    .object({
      accessToken: z.string(),
      expiresAt: TIMESTAMP_SCHEMA,
      refreshToken: z.string(),
    })
    .nullable(),
  user: z
    .object({
      avatar: z.string().url().optional(),
      email: EMAIL_SCHEMA,
      emailVerified: z.boolean(),
      firstName: z.string(),
      id: UUID_SCHEMA,
      lastName: z.string(),
      role: z.enum(["user", "admin", "moderator"]),
      twoFactorEnabled: z.boolean(),
    })
    .nullable(),
});

export const authStoreActionsSchema = z.object({
  checkAuth: z.function(),
  clearError: z.function(),
  refreshToken: z.function(),
  signIn: z.function(),
  signOut: z.function(),
  signUp: z.function(),
  updateUser: z.function(),
});

// User store schema
export const userStoreStateSchema = z.object({
  profile: z
    .object({
      avatar: z.string().url().optional(),
      bio: z.string().optional(),
      currency: z.string().length(3).optional(),
      displayName: z.string().optional(),
      email: EMAIL_SCHEMA,
      firstName: z.string(),
      id: UUID_SCHEMA,
      language: z.string().optional(),
      lastName: z.string(),
      preferences: z.record(z.string(), z.unknown()).optional(),
      timezone: z.string().optional(),
    })
    .nullable(),
  ...LOADING_STATE_SCHEMA.shape,
});

export const userStoreActionsSchema = z.object({
  deleteAccount: z.function(),
  fetchProfile: z.function(),
  reset: z.function(),
  updatePreferences: z.function(),
  updateProfile: z.function(),
  uploadAvatar: z.function(),
});

// Search store schema
export const searchStoreStateSchema = z.object({
  currentParams: z.record(z.string(), z.unknown()).nullable(),
  currentSearchType: z
    .enum(["flight", "accommodation", "activity", "destination"])
    .nullable(),
  filters: z.record(z.string(), z.unknown()),
  pagination: PAGINATION_STATE_SCHEMA.optional(),
  recentSearches: z.array(
    z.object({
      id: z.string(),
      params: z.record(z.string(), z.unknown()),
      timestamp: TIMESTAMP_SCHEMA,
      type: z.enum(["flight", "accommodation", "activity", "destination"]),
    })
  ),
  results: z.object({
    accommodations: z.array(z.unknown()).optional(),
    activities: z.array(z.unknown()).optional(),
    destinations: z.array(z.unknown()).optional(),
    flights: z.array(z.unknown()).optional(),
  }),
  savedSearches: z.array(
    z.object({
      createdAt: TIMESTAMP_SCHEMA,
      id: z.string(),
      lastUsed: TIMESTAMP_SCHEMA.optional(),
      name: z.string(),
      params: z.record(z.string(), z.unknown()),
      type: z.enum(["flight", "accommodation", "activity", "destination"]),
    })
  ),
  sorting: z
    .object({
      direction: z.enum(["asc", "desc"]),
      field: z.string(),
    })
    .optional(),
  ...LOADING_STATE_SCHEMA.shape,
});

export const searchStoreActionsSchema = z.object({
  addToRecentSearches: z.function(),
  clearRecentSearches: z.function(),
  clearResults: z.function(),
  deleteSavedSearch: z.function(),
  executeSearch: z.function(),
  loadMore: z.function(),
  loadSavedSearch: z.function(),
  reset: z.function(),
  saveSearch: z.function(),
  setFilters: z.function(),
  setSearchType: z.function(),
  setSorting: z.function(),
  updateParams: z.function(),
});

// Trip store schema
export const tripStoreStateSchema = z.object({
  currentTrip: z
    .object({
      budget: z
        .object({
          currency: z.string().length(3),
          spent: NON_NEGATIVE_NUMBER_SCHEMA,
          total: POSITIVE_NUMBER_SCHEMA,
        })
        .optional(),
      destination: z.string(),
      endDate: z.string().date(),
      id: UUID_SCHEMA,
      itinerary: z.array(z.unknown()),
      startDate: z.string().date(),
      status: z.enum(["planning", "booked", "active", "completed", "cancelled"]),
      title: z.string(),
      travelers: z.array(z.unknown()),
    })
    .nullable(),
  filters: z.object({
    dateRange: z
      .object({
        end: z.string().date(),
        start: z.string().date(),
      })
      .optional(),
    search: z.string().optional(),
    status: z
      .array(z.enum(["planning", "booked", "active", "completed", "cancelled"]))
      .optional(),
  }),
  sorting: z.object({
    direction: z.enum(["asc", "desc"]),
    field: z.enum(["createdAt", "startDate", "title", "status"]),
  }),
  trips: z.array(
    z.object({
      budget: z
        .object({
          currency: z.string().length(3),
          spent: NON_NEGATIVE_NUMBER_SCHEMA,
          total: POSITIVE_NUMBER_SCHEMA,
        })
        .optional(),
      createdAt: TIMESTAMP_SCHEMA,
      description: z.string().optional(),
      destination: z.string(),
      endDate: z.string().date(),
      id: UUID_SCHEMA,
      itinerary: z.array(z.unknown()),
      startDate: z.string().date(),
      status: z.enum(["planning", "booked", "active", "completed", "cancelled"]),
      title: z.string(),
      travelers: z.array(
        z.object({
          email: EMAIL_SCHEMA.optional(),
          id: UUID_SCHEMA.optional(),
          name: z.string(),
          role: z.enum(["owner", "collaborator", "viewer"]),
        })
      ),
      updatedAt: TIMESTAMP_SCHEMA,
    })
  ),
  ...LOADING_STATE_SCHEMA.shape,
  pagination: PAGINATION_STATE_SCHEMA,
});

export const tripStoreActionsSchema = z.object({
  clearCurrentTrip: z.function(),
  clearFilters: z.function(),
  createTrip: z.function(),
  deleteTrip: z.function(),
  duplicateTrip: z.function(),
  fetchTrips: z.function(),
  loadMore: z.function(),
  refresh: z.function(),
  reset: z.function(),
  setCurrentTrip: z.function(),
  setSorting: z.function(),
  updateFilters: z.function(),
  updateTrip: z.function(),
});

// Chat store schema
export const chatStoreStateSchema = z.object({
  connectionStatus: z.enum(["connected", "connecting", "disconnected", "error"]),
  conversations: z.array(
    z.object({
      createdAt: TIMESTAMP_SCHEMA,
      id: UUID_SCHEMA,
      messages: z.array(
        z.object({
          content: z.string(),
          id: UUID_SCHEMA,
          metadata: z.record(z.string(), z.unknown()).optional(),
          role: z.enum(["user", "assistant", "system"]),
          timestamp: TIMESTAMP_SCHEMA,
        })
      ),
      status: z.enum(["active", "archived", "deleted"]),
      title: z.string(),
      updatedAt: TIMESTAMP_SCHEMA,
    })
  ),
  currentConversation: z
    .object({
      id: UUID_SCHEMA,
      messages: z.array(z.unknown()),
      status: z.enum(["active", "archived", "deleted"]),
      title: z.string(),
    })
    .nullable(),
  isTyping: z.boolean(),
  typingUsers: z.array(z.string()),
  ...LOADING_STATE_SCHEMA.shape,
});

export const chatStoreActionsSchema = z.object({
  addTypingUser: z.function(),
  archiveConversation: z.function(),
  createConversation: z.function(),
  deleteConversation: z.function(),
  deleteMessage: z.function(),
  editMessage: z.function(),
  fetchConversations: z.function(),
  removeTypingUser: z.function(),
  reset: z.function(),
  sendMessage: z.function(),
  setConnectionStatus: z.function(),
  setCurrentConversation: z.function(),
  setTyping: z.function(),
});

// UI store schema
export const uiStoreStateSchema = z.object({
  breadcrumbs: z.array(
    z.object({
      href: z.string().optional(),
      isActive: z.boolean(),
      label: z.string(),
    })
  ),
  globalError: z.string().nullable(),
  modals: z.record(
    z.string(),
    z.object({
      data: z.unknown().optional(),
      isOpen: z.boolean(),
    })
  ),
  notifications: z.array(
    z.object({
      actions: z
        .array(
          z.object({
            action: z.function(),
            label: z.string(),
          })
        )
        .optional(),
      createdAt: TIMESTAMP_SCHEMA,
      duration: z.number().positive().optional(),
      id: z.string(),
      message: z.string(),
      title: z.string(),
      type: z.enum(["success", "error", "warning", "info"]),
    })
  ),
  pageLoading: z.boolean(),
  sidebar: z.object({
    isCollapsed: z.boolean(),
    isOpen: z.boolean(),
    width: z.number().positive(),
  }),
  theme: z.enum(["light", "dark", "system"]),
  toasts: z.array(
    z.object({
      action: z
        .object({
          label: z.string(),
          onClick: z.function(),
        })
        .optional(),
      description: z.string(),
      duration: z.number().positive().optional(),
      id: z.string(),
      title: z.string().optional(),
      type: z.enum(["success", "error", "warning", "info"]),
    })
  ),
});

export const uiStoreActionsSchema = z.object({
  addNotification: z.function(),
  addToast: z.function(),
  clearGlobalError: z.function(),
  clearNotifications: z.function(),
  clearToasts: z.function(),
  closeModal: z.function(),
  openModal: z.function(),
  removeNotification: z.function(),
  removeToast: z.function(),
  reset: z.function(),
  setBreadcrumbs: z.function(),
  setGlobalError: z.function(),
  setPageLoading: z.function(),
  setSidebarCollapsed: z.function(),
  setSidebarWidth: z.function(),
  setTheme: z.function(),
  toggleSidebar: z.function(),
});

// Budget store schema
export const budgetStoreStateSchema = z.object({
  budgets: z.record(
    z.string(),
    z.object({
      categories: z.record(
        z.string(),
        z.object({
          allocated: NON_NEGATIVE_NUMBER_SCHEMA,
          spent: NON_NEGATIVE_NUMBER_SCHEMA,
        })
      ),
      currency: z.string().length(3),
      expenses: z.array(
        z.object({
          amount: POSITIVE_NUMBER_SCHEMA,
          category: z.string(),
          createdAt: TIMESTAMP_SCHEMA,
          currency: z.string().length(3),
          date: z.string().date(),
          description: z.string(),
          id: UUID_SCHEMA,
        })
      ),
      spent: NON_NEGATIVE_NUMBER_SCHEMA,
      total: POSITIVE_NUMBER_SCHEMA,
      tripId: UUID_SCHEMA,
      updatedAt: TIMESTAMP_SCHEMA,
    })
  ),
  currentBudget: z
    .object({
      categories: z.record(z.string(), z.unknown()),
      currency: z.string().length(3),
      expenses: z.array(z.unknown()),
      spent: NON_NEGATIVE_NUMBER_SCHEMA,
      total: POSITIVE_NUMBER_SCHEMA,
      tripId: UUID_SCHEMA,
    })
    .nullable(),
  exchangeRates: z.record(z.string(), z.number().positive()),
  ...LOADING_STATE_SCHEMA.shape,
});

export const budgetStoreActionsSchema = z.object({
  addExpense: z.function(),
  convertCurrency: z.function(),
  createBudget: z.function(),
  deleteBudget: z.function(),
  deleteExpense: z.function(),
  fetchBudget: z.function(),
  fetchExchangeRates: z.function(),
  reset: z.function(),
  updateBudget: z.function(),
  updateCategory: z.function(),
  updateExpense: z.function(),
});

// API Key store schema
export const apiKeyStoreStateSchema = z.object({
  keys: z.array(
    z.object({
      createdAt: TIMESTAMP_SCHEMA,
      id: UUID_SCHEMA,
      isActive: z.boolean(),
      key: z.string(),
      lastUsed: TIMESTAMP_SCHEMA.optional(),
      name: z.string(),
      service: z.enum(["openai", "anthropic", "google", "amadeus", "skyscanner"]),
      usageCount: NON_NEGATIVE_NUMBER_SCHEMA,
    })
  ),
  services: z.record(
    z.string(),
    z.object({
      description: z.string(),
      lastCheck: TIMESTAMP_SCHEMA.optional(),
      name: z.string(),
      status: z.enum(["connected", "disconnected", "error"]),
    })
  ),
  ...LOADING_STATE_SCHEMA.shape,
});

export const apiKeyStoreActionsSchema = z.object({
  checkServiceStatus: z.function(),
  createKey: z.function(),
  deleteKey: z.function(),
  fetchKeys: z.function(),
  reset: z.function(),
  testKey: z.function(),
  toggleKey: z.function(),
  updateKey: z.function(),
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
