/**
 * @fileoverview Zustand store state validation schemas.
 * Runtime validation for all store state mutations and data across auth, user, search, trip, chat, UI, budget, and API key stores.
 */

import { z } from "zod";
import { messageRoleSchema } from "./chat";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====
// Core store state patterns and reusable schemas

// Common validation patterns using registry primitives
const TIMESTAMP_SCHEMA = primitiveSchemas.isoDateTime;
const UUID_SCHEMA = primitiveSchemas.uuid;
const EMAIL_SCHEMA = primitiveSchemas.email;
const URL_SCHEMA = primitiveSchemas.url;
const POSITIVE_NUMBER_SCHEMA = primitiveSchemas.positiveNumber;
const NON_NEGATIVE_NUMBER_SCHEMA = primitiveSchemas.nonNegativeNumber;

/**
 * Base loading state schema for store state.
 * Includes error handling and loading indicators.
 */
const LOADING_STATE_SCHEMA = z.object({
  error: z.string().nullable(),
  isLoading: z.boolean(),
  lastUpdated: TIMESTAMP_SCHEMA.optional(),
});

/**
 * Base pagination state schema for store state.
 * Includes pagination metadata for list views.
 */
const PAGINATION_STATE_SCHEMA = z.object({
  hasNext: z.boolean(),
  hasPrevious: z.boolean(),
  page: z.number().int().positive(),
  pageSize: z.number().int().positive().max(100),
  total: NON_NEGATIVE_NUMBER_SCHEMA,
});

/**
 * Zod schema for auth-specific user preferences (UI settings).
 * Note: Distinct from memory.ts USER_PREFERENCES_SCHEMA which is for travel preferences.
 */
export const AUTH_USER_PREFERENCES_SCHEMA = z.object({
  analytics: z.boolean().optional(),
  autoSaveSearches: z.boolean().optional(),
  dateFormat: z.enum(["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]).optional(),
  language: z.string().optional(),
  locationServices: z.boolean().optional(),
  notifications: z
    .object({
      email: z.boolean().optional(),
      marketing: z.boolean().optional(),
      priceAlerts: z.boolean().optional(),
      tripReminders: z.boolean().optional(),
    })
    .optional(),
  smartSuggestions: z.boolean().optional(),
  theme: z.enum(["light", "dark", "system"]).optional(),
  timeFormat: z.enum(["12h", "24h"]).optional(),
  timezone: z.string().optional(),
  units: z.enum(["metric", "imperial"]).optional(),
});

/** TypeScript type for auth user preferences. */
export type AuthUserPreferences = z.infer<typeof AUTH_USER_PREFERENCES_SCHEMA>;

/**
 * Zod schema for auth user security settings.
 * Includes two-factor authentication and security questions.
 */
export const AUTH_USER_SECURITY_SCHEMA = z.object({
  lastPasswordChange: primitiveSchemas.isoDateTime.optional(),
  securityQuestions: z
    .array(
      z.object({
        answer: z.string(), // This would be hashed in real implementation
        question: z.string(),
      })
    )
    .optional(),
  twoFactorEnabled: z.boolean().optional(),
});

/** TypeScript type for auth user security. */
export type AuthUserSecurity = z.infer<typeof AUTH_USER_SECURITY_SCHEMA>;

/**
 * Zod schema for auth user entities.
 * Validates user data including profile, preferences, and security settings.
 */
export const AUTH_USER_SCHEMA = z.object({
  avatarUrl: URL_SCHEMA.optional(),
  bio: z.string().optional(),
  createdAt: primitiveSchemas.isoDateTime,
  displayName: z.string().optional(),
  email: EMAIL_SCHEMA,
  firstName: z.string().optional(),
  id: primitiveSchemas.uuid,
  isEmailVerified: z.boolean(),
  lastName: z.string().optional(),
  location: z.string().optional(),
  preferences: AUTH_USER_PREFERENCES_SCHEMA.optional(),
  security: AUTH_USER_SECURITY_SCHEMA.optional(),
  updatedAt: primitiveSchemas.isoDateTime,
  website: URL_SCHEMA.optional(),
});

/** TypeScript type for auth users. */
export type AuthUser = z.infer<typeof AUTH_USER_SCHEMA>;

/**
 * Zod schema for authentication token information.
 * Validates access and refresh tokens with expiration.
 */
export const AUTH_TOKEN_INFO_SCHEMA = z.object({
  accessToken: z.string(),
  expiresAt: primitiveSchemas.isoDateTime,
  refreshToken: z.string().optional(),
  tokenType: z.string().default("Bearer"),
});

/** TypeScript type for auth token information. */
export type AuthTokenInfo = z.infer<typeof AUTH_TOKEN_INFO_SCHEMA>;

/**
 * Zod schema for authentication session entities.
 * Validates session data including device information and expiration.
 */
export const AUTH_SESSION_SCHEMA = z.object({
  createdAt: primitiveSchemas.isoDateTime,
  deviceInfo: z
    .object({
      deviceId: z.string().optional(),
      ipAddress: z.string().optional(),
      userAgent: z.string().optional(),
    })
    .optional(),
  expiresAt: primitiveSchemas.isoDateTime,
  id: primitiveSchemas.uuid,
  lastActivity: primitiveSchemas.isoDateTime,
  userId: primitiveSchemas.uuid,
});

/** TypeScript type for auth sessions. */
export type AuthSession = z.infer<typeof AUTH_SESSION_SCHEMA>;

// ===== STATE SCHEMAS =====
// Schemas for Zustand store state management

/**
 * Zod schema for auth store state.
 * Manages authentication state including user, session, and loading indicators.
 */
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
      avatar: URL_SCHEMA.optional(),
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

/** TypeScript type for auth store state. */
export type AuthStoreState = z.infer<typeof authStoreStateSchema>;

/**
 * Zod schema for auth store actions.
 * Validates action function signatures for auth store.
 */
export const authStoreActionsSchema = z.object({
  checkAuth: z.function(),
  clearError: z.function(),
  refreshToken: z.function(),
  signIn: z.function(),
  signOut: z.function(),
  signUp: z.function(),
  updateUser: z.function(),
});

/** TypeScript type for auth store actions. */
export type AuthStoreActions = z.infer<typeof authStoreActionsSchema>;

/**
 * Zod schema for user store state.
 * Manages user profile data and loading state.
 */
export const userStoreStateSchema = z
  .object({
    profile: z
      .object({
        avatar: URL_SCHEMA.optional(),
        bio: z.string().optional(),
        currency: primitiveSchemas.isoCurrency.optional(),
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
  })
  .merge(LOADING_STATE_SCHEMA);

/** TypeScript type for user store state. */
export type UserStoreState = z.infer<typeof userStoreStateSchema>;

/**
 * Zod schema for user store actions.
 * Validates action function signatures for user store.
 */
export const userStoreActionsSchema = z.object({
  deleteAccount: z.function(),
  fetchProfile: z.function(),
  reset: z.function(),
  updatePreferences: z.function(),
  updateProfile: z.function(),
  uploadAvatar: z.function(),
});

/** TypeScript type for user store actions. */
export type UserStoreActions = z.infer<typeof userStoreActionsSchema>;

/**
 * Zod schema for search store state.
 * Manages search parameters, results, filters, and saved searches.
 */
export const searchStoreStateSchema = z
  .object({
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
  })
  .merge(LOADING_STATE_SCHEMA);

/** TypeScript type for search store state. */
export type SearchStoreState = z.infer<typeof searchStoreStateSchema>;

/**
 * Zod schema for search store actions.
 * Validates action function signatures for search store.
 */
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

/** TypeScript type for search store actions. */
export type SearchStoreActions = z.infer<typeof searchStoreActionsSchema>;

/**
 * Zod schema for trip store state.
 * Manages trip data, filters, pagination, and current trip selection.
 */
export const tripStoreStateSchema = z
  .object({
    currentTrip: z
      .object({
        budget: z
          .object({
            currency: primitiveSchemas.isoCurrency,
            spent: NON_NEGATIVE_NUMBER_SCHEMA,
            total: POSITIVE_NUMBER_SCHEMA,
          })
          .optional(),
        destination: z.string(),
        endDate: z.iso.date(),
        id: UUID_SCHEMA,
        itinerary: z.array(z.unknown()),
        startDate: z.iso.date(),
        status: z.enum(["planning", "booked", "active", "completed", "cancelled"]),
        title: z.string(),
        travelers: z.array(z.unknown()),
      })
      .nullable(),
    filters: z.object({
      dateRange: z
        .object({
          end: z.iso.date(),
          start: z.iso.date(),
        })
        .optional(),
      search: z.string().optional(),
      status: z
        .array(z.enum(["planning", "booked", "active", "completed", "cancelled"]))
        .optional(),
    }),
    pagination: PAGINATION_STATE_SCHEMA,
    sorting: z.object({
      direction: z.enum(["asc", "desc"]),
      field: z.enum(["createdAt", "startDate", "title", "status"]),
    }),
    trips: z.array(
      z.object({
        budget: z
          .object({
            currency: primitiveSchemas.isoCurrency,
            spent: NON_NEGATIVE_NUMBER_SCHEMA,
            total: POSITIVE_NUMBER_SCHEMA,
          })
          .optional(),
        createdAt: TIMESTAMP_SCHEMA,
        description: z.string().optional(),
        destination: z.string(),
        endDate: z.iso.date(),
        id: UUID_SCHEMA,
        itinerary: z.array(z.unknown()),
        startDate: z.iso.date(),
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
  })
  .merge(LOADING_STATE_SCHEMA);

/** TypeScript type for trip store state. */
export type TripStoreState = z.infer<typeof tripStoreStateSchema>;

/**
 * Zod schema for trip store actions.
 * Validates action function signatures for trip store.
 */
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

/** TypeScript type for trip store actions. */
export type TripStoreActions = z.infer<typeof tripStoreActionsSchema>;

/**
 * Zod schema for chat store state.
 * Manages conversations, messages, typing indicators, and connection status.
 */
export const chatStoreStateSchema = z
  .object({
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
            role: messageRoleSchema,
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
  })
  .merge(LOADING_STATE_SCHEMA);

/** TypeScript type for chat store state. */
export type ChatStoreState = z.infer<typeof chatStoreStateSchema>;

/**
 * Zod schema for chat store actions.
 * Validates action function signatures for chat store.
 */
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

/** TypeScript type for chat store actions. */
export type ChatStoreActions = z.infer<typeof chatStoreActionsSchema>;

/**
 * Zod schema for UI store state.
 * Manages UI state including modals, notifications, toasts, sidebar, and theme.
 */
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

/** TypeScript type for UI store state. */
export type UiStoreState = z.infer<typeof uiStoreStateSchema>;

/**
 * Zod schema for UI store actions.
 * Validates action function signatures for UI store.
 */
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

/** TypeScript type for UI store actions. */
export type UiStoreActions = z.infer<typeof uiStoreActionsSchema>;

/**
 * Zod schema for budget store state.
 * Manages budgets, expenses, exchange rates, and current budget selection.
 */
export const budgetStoreStateSchema = z
  .object({
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
        currency: primitiveSchemas.isoCurrency,
        expenses: z.array(
          z.object({
            amount: POSITIVE_NUMBER_SCHEMA,
            category: z.string(),
            createdAt: TIMESTAMP_SCHEMA,
            currency: primitiveSchemas.isoCurrency,
            date: z.iso.date(),
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
        currency: primitiveSchemas.isoCurrency,
        expenses: z.array(z.unknown()),
        spent: NON_NEGATIVE_NUMBER_SCHEMA,
        total: POSITIVE_NUMBER_SCHEMA,
        tripId: UUID_SCHEMA,
      })
      .nullable(),
    exchangeRates: z.record(z.string(), z.number().positive()),
  })
  .merge(LOADING_STATE_SCHEMA);

/** TypeScript type for budget store state. */
export type BudgetStoreState = z.infer<typeof budgetStoreStateSchema>;

/**
 * Zod schema for budget store actions.
 * Validates action function signatures for budget store.
 */
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

/** TypeScript type for budget store actions. */
export type BudgetStoreActions = z.infer<typeof budgetStoreActionsSchema>;

/**
 * Zod schema for API key store state.
 * Manages API keys, service status, and usage tracking.
 */
export const apiKeyStoreStateSchema = z
  .object({
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
  })
  .merge(LOADING_STATE_SCHEMA);

/** TypeScript type for API key store state. */
export type ApiKeyStoreState = z.infer<typeof apiKeyStoreStateSchema>;

/**
 * Zod schema for API key store actions.
 * Validates action function signatures for API key store.
 */
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

/** TypeScript type for API key store actions. */
export type ApiKeyStoreActions = z.infer<typeof apiKeyStoreActionsSchema>;

// ===== UTILITY FUNCTIONS =====
// Validation helpers and middleware for store state

/**
 * Validates store state against a schema.
 * Throws an error with detailed validation messages if validation fails.
 *
 * @param schema - Zod schema to validate against
 * @param state - Store state to validate
 * @param storeName - Optional store name for error messages
 * @returns Validated store state
 * @throws {Error} When validation fails with detailed error information
 */
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

/**
 * Safely validates store state with error handling.
 * Returns a result object with success/error information instead of throwing.
 *
 * @param schema - Zod schema to validate against
 * @param state - Store state to validate
 * @param storeName - Optional store name for error messages
 * @returns Validation result with success/error information
 */
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

/**
 * Middleware for Zustand store validation.
 * Wraps store configuration with development-time state validation.
 *
 * @param schema - Zod schema to validate state against
 * @param storeName - Optional store name for error messages
 * @returns Middleware function for Zustand store configuration
 */
export const storeValidationMiddleware =
  <T>(schema: z.ZodSchema<T>, storeName?: string) =>
  // biome-ignore lint/suspicious/noExplicitAny: Zustand store API requires flexible typing
  (config: (set: any, get: any, api: any) => T) =>
  // biome-ignore lint/suspicious/noExplicitAny: Zustand store API requires flexible typing
  (set: any, get: any, api: any) => {
    const store = config(
      // biome-ignore lint/suspicious/noExplicitAny: Zustand partial state can be any shape
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
