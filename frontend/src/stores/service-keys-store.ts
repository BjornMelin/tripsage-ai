import { create } from "zustand";
import { persist, devtools } from "zustand/middleware";
import { z } from "zod";

// Validation schemas for API keys
export const ServiceKeyStatusSchema = z.enum([
  "active",
  "inactive",
  "expired",
  "invalid",
  "pending",
]);
export const ServiceTypeSchema = z.enum([
  "flights",
  "accommodation",
  "maps",
  "weather",
  "calendar",
  "currency",
  "translation",
  "payment",
  "analytics",
  "email",
  "sms",
  "storage",
  "ai",
  "other",
]);

export const ServiceKeySchema = z.object({
  id: z.string(),
  service: z.string(),
  serviceType: ServiceTypeSchema,
  displayName: z.string(),
  description: z.string().optional(),
  apiKey: z.string(),
  apiSecret: z.string().optional(),
  baseUrl: z.string().url().optional(),
  status: ServiceKeyStatusSchema,
  isValid: z.boolean(),
  lastValidated: z.string().optional(),
  createdAt: z.string(),
  updatedAt: z.string(),
  expiresAt: z.string().optional(),
  metadata: z.record(z.unknown()).optional(),
  usage: z
    .object({
      requestCount: z.number().default(0),
      lastUsed: z.string().optional(),
      dailyLimit: z.number().optional(),
      monthlyLimit: z.number().optional(),
      dailyUsage: z.number().default(0),
      monthlyUsage: z.number().default(0),
    })
    .optional(),
});

export const ServiceConfigSchema = z.object({
  service: z.string(),
  serviceType: ServiceTypeSchema,
  displayName: z.string(),
  description: z.string(),
  isRequired: z.boolean(),
  documentationUrl: z.string().url().optional(),
  setupInstructions: z.string().optional(),
  testEndpoint: z.string().optional(),
  defaultBaseUrl: z.string().url().optional(),
  supportedFeatures: z.array(z.string()).default([]),
  config: z.object({
    requiresSecret: z.boolean().default(false),
    allowCustomBaseUrl: z.boolean().default(false),
    hasUsageLimits: z.boolean().default(false),
    supportsTestMode: z.boolean().default(false),
  }),
});

export const ValidationResultSchema = z.object({
  isValid: z.boolean(),
  status: ServiceKeyStatusSchema,
  message: z.string().optional(),
  details: z.record(z.unknown()).optional(),
  testedAt: z.string(),
  responseTime: z.number().optional(),
});

// Types derived from schemas
export type ServiceKeyStatus = z.infer<typeof ServiceKeyStatusSchema>;
export type ServiceType = z.infer<typeof ServiceTypeSchema>;
export type ServiceKey = z.infer<typeof ServiceKeySchema>;
export type ServiceConfig = z.infer<typeof ServiceConfigSchema>;
export type ValidationResult = z.infer<typeof ValidationResultSchema>;

export interface ServiceKeyInput {
  service: string;
  serviceType: ServiceType;
  apiKey: string;
  apiSecret?: string;
  baseUrl?: string;
  metadata?: Record<string, unknown>;
}

export interface ValidationOptions {
  testEndpoint?: boolean;
  checkUsage?: boolean;
  timeout?: number;
}

// Service Keys store interface
interface ServiceKeysState {
  // Service keys data
  keys: Record<string, ServiceKey>;
  supportedServices: Record<string, ServiceConfig>;

  // Loading and validation states
  isLoading: boolean;
  isValidating: Record<string, boolean>;
  isSaving: Record<string, boolean>;

  // Error states
  error: string | null;
  validationErrors: Record<string, string>;

  // Computed properties
  activeKeys: ServiceKey[];
  invalidKeys: ServiceKey[];
  expiringKeys: ServiceKey[];
  keysByServiceType: Record<ServiceType, ServiceKey[]>;
  totalUsageStats: {
    totalRequests: number;
    activeServices: number;
    recentlyUsed: number;
  };

  // Service management actions
  setSupportedServices: (services: Record<string, ServiceConfig>) => void;
  addSupportedService: (service: ServiceConfig) => void;
  updateSupportedService: (serviceId: string, updates: Partial<ServiceConfig>) => void;

  // Key management actions
  addKey: (keyInput: ServiceKeyInput) => Promise<string | null>;
  updateKey: (keyId: string, updates: Partial<ServiceKey>) => Promise<boolean>;
  removeKey: (keyId: string) => Promise<boolean>;
  setKeys: (keys: Record<string, ServiceKey>) => void;

  // Validation actions
  validateKey: (
    keyId: string,
    options?: ValidationOptions
  ) => Promise<ValidationResult>;
  validateAllKeys: () => Promise<Record<string, ValidationResult>>;
  testKeyConnection: (keyInput: ServiceKeyInput) => Promise<ValidationResult>;

  // Key status management
  setKeyStatus: (keyId: string, status: ServiceKeyStatus) => void;
  markKeyAsUsed: (keyId: string) => void;
  updateUsageStats: (keyId: string, requestCount?: number) => void;

  // Bulk operations
  validateExpiredKeys: () => Promise<void>;
  refreshAllKeys: () => Promise<void>;
  exportKeys: () => string;
  importKeys: (data: string) => Promise<boolean>;

  // Service-specific helpers
  getKeyByService: (service: string) => ServiceKey | null;
  getKeysByServiceType: (serviceType: ServiceType) => ServiceKey[];
  getRequiredMissingServices: () => ServiceConfig[];

  // Utility actions
  clearErrors: () => void;
  clearValidationError: (keyId: string) => void;
  reset: () => void;
}

// Helper functions
const generateId = () =>
  Date.now().toString(36) + Math.random().toString(36).substring(2, 5);
const getCurrentTimestamp = () => new Date().toISOString();

// Default supported services configuration
const defaultSupportedServices: Record<string, ServiceConfig> = {
  duffel: {
    service: "duffel",
    serviceType: "flights",
    displayName: "Duffel Flights API",
    description: "Flight search and booking API",
    isRequired: true,
    documentationUrl: "https://docs.duffel.com/",
    defaultBaseUrl: "https://api.duffel.com",
    supportedFeatures: ["search", "booking", "cancellation"],
    config: {
      requiresSecret: false,
      allowCustomBaseUrl: false,
      hasUsageLimits: true,
      supportsTestMode: true,
    },
  },
  airbnb: {
    service: "airbnb",
    serviceType: "accommodation",
    displayName: "Airbnb API",
    description: "Accommodation search and booking",
    isRequired: false,
    documentationUrl: "https://developers.airbnb.com/",
    supportedFeatures: ["search", "details", "booking"],
    config: {
      requiresSecret: true,
      allowCustomBaseUrl: false,
      hasUsageLimits: true,
      supportsTestMode: false,
    },
  },
  google_maps: {
    service: "google_maps",
    serviceType: "maps",
    displayName: "Google Maps API",
    description: "Maps, geocoding, and places API",
    isRequired: true,
    documentationUrl: "https://developers.google.com/maps/documentation",
    defaultBaseUrl: "https://maps.googleapis.com",
    supportedFeatures: ["geocoding", "places", "directions", "static_maps"],
    config: {
      requiresSecret: false,
      allowCustomBaseUrl: false,
      hasUsageLimits: true,
      supportsTestMode: true,
    },
  },
  openweathermap: {
    service: "openweathermap",
    serviceType: "weather",
    displayName: "OpenWeatherMap API",
    description: "Weather data and forecasts",
    isRequired: false,
    documentationUrl: "https://openweathermap.org/api",
    defaultBaseUrl: "https://api.openweathermap.org",
    supportedFeatures: ["current", "forecast", "history"],
    config: {
      requiresSecret: false,
      allowCustomBaseUrl: false,
      hasUsageLimits: true,
      supportsTestMode: true,
    },
  },
};

export const useServiceKeysStore = create<ServiceKeysState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        keys: {},
        supportedServices: defaultSupportedServices,

        // Loading states
        isLoading: false,
        isValidating: {},
        isSaving: {},

        // Error states
        error: null,
        validationErrors: {},

        // Computed properties
        get activeKeys() {
          return Object.values(get().keys).filter((key) => key.status === "active");
        },

        get invalidKeys() {
          return Object.values(get().keys).filter(
            (key) => !key.isValid || key.status === "invalid"
          );
        },

        get expiringKeys() {
          const now = new Date();
          const thirtyDaysFromNow = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);

          return Object.values(get().keys).filter((key) => {
            if (!key.expiresAt) return false;
            const expiresAt = new Date(key.expiresAt);
            return expiresAt <= thirtyDaysFromNow && expiresAt > now;
          });
        },

        get keysByServiceType() {
          const keys = Object.values(get().keys);
          const grouped: Record<ServiceType, ServiceKey[]> = {} as Record<
            ServiceType,
            ServiceKey[]
          >;

          keys.forEach((key) => {
            if (!grouped[key.serviceType]) {
              grouped[key.serviceType] = [];
            }
            grouped[key.serviceType].push(key);
          });

          return grouped;
        },

        get totalUsageStats() {
          const keys = Object.values(get().keys);
          const activeServices = keys.filter((key) => key.status === "active").length;
          const totalRequests = keys.reduce(
            (sum, key) => sum + (key.usage?.requestCount || 0),
            0
          );

          const now = new Date();
          const last24Hours = new Date(now.getTime() - 24 * 60 * 60 * 1000);
          const recentlyUsed = keys.filter(
            (key) => key.usage?.lastUsed && new Date(key.usage.lastUsed) > last24Hours
          ).length;

          return {
            totalRequests,
            activeServices,
            recentlyUsed,
          };
        },

        // Service management actions
        setSupportedServices: (services) => {
          // Validate each service config
          const validatedServices: Record<string, ServiceConfig> = {};

          Object.entries(services).forEach(([key, service]) => {
            const result = ServiceConfigSchema.safeParse(service);
            if (result.success) {
              validatedServices[key] = result.data;
            } else {
              console.error(`Invalid service config for ${key}:`, result.error);
            }
          });

          set({ supportedServices: validatedServices });
        },

        addSupportedService: (service) => {
          const result = ServiceConfigSchema.safeParse(service);
          if (result.success) {
            set((state) => ({
              supportedServices: {
                ...state.supportedServices,
                [service.service]: result.data,
              },
            }));
          } else {
            console.error("Invalid service config:", result.error);
          }
        },

        updateSupportedService: (serviceId, updates) => {
          set((state) => {
            const existingService = state.supportedServices[serviceId];
            if (!existingService) return state;

            const updatedService = { ...existingService, ...updates };
            const result = ServiceConfigSchema.safeParse(updatedService);

            if (result.success) {
              return {
                supportedServices: {
                  ...state.supportedServices,
                  [serviceId]: result.data,
                },
              };
            } else {
              console.error("Invalid service config update:", result.error);
              return state;
            }
          });
        },

        // Key management actions
        addKey: async (keyInput) => {
          const keyId = generateId();
          const timestamp = getCurrentTimestamp();

          set((state) => ({
            isSaving: { ...state.isSaving, [keyId]: true },
          }));

          try {
            const serviceConfig = get().supportedServices[keyInput.service];
            if (!serviceConfig) {
              throw new Error(`Unsupported service: ${keyInput.service}`);
            }

            const newKey: ServiceKey = {
              id: keyId,
              service: keyInput.service,
              serviceType: keyInput.serviceType,
              displayName: serviceConfig.displayName,
              description: serviceConfig.description,
              apiKey: keyInput.apiKey,
              apiSecret: keyInput.apiSecret,
              baseUrl: keyInput.baseUrl || serviceConfig.defaultBaseUrl,
              status: "pending",
              isValid: false,
              createdAt: timestamp,
              updatedAt: timestamp,
              metadata: keyInput.metadata,
              usage: {
                requestCount: 0,
                dailyUsage: 0,
                monthlyUsage: 0,
              },
            };

            const result = ServiceKeySchema.safeParse(newKey);
            if (!result.success) {
              throw new Error("Invalid key data");
            }

            // Validate the key
            const validationResult = await get().testKeyConnection(keyInput);

            set((state) => ({
              keys: {
                ...state.keys,
                [keyId]: {
                  ...result.data,
                  status: validationResult.status,
                  isValid: validationResult.isValid,
                  lastValidated: validationResult.testedAt,
                },
              },
              isSaving: { ...state.isSaving, [keyId]: false },
            }));

            return keyId;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to add key";
            set((state) => ({
              error: message,
              isSaving: { ...state.isSaving, [keyId]: false },
            }));
            return null;
          }
        },

        updateKey: async (keyId, updates) => {
          const existingKey = get().keys[keyId];
          if (!existingKey) return false;

          set((state) => ({
            isSaving: { ...state.isSaving, [keyId]: true },
          }));

          try {
            const updatedKey = {
              ...existingKey,
              ...updates,
              updatedAt: getCurrentTimestamp(),
            };

            const result = ServiceKeySchema.safeParse(updatedKey);
            if (!result.success) {
              throw new Error("Invalid key data");
            }

            set((state) => ({
              keys: {
                ...state.keys,
                [keyId]: result.data,
              },
              isSaving: { ...state.isSaving, [keyId]: false },
            }));

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to update key";
            set((state) => ({
              error: message,
              isSaving: { ...state.isSaving, [keyId]: false },
            }));
            return false;
          }
        },

        removeKey: async (keyId) => {
          try {
            set((state) => {
              const newKeys = { ...state.keys };
              delete newKeys[keyId];

              const newValidationErrors = { ...state.validationErrors };
              delete newValidationErrors[keyId];

              return {
                keys: newKeys,
                validationErrors: newValidationErrors,
              };
            });

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to remove key";
            set({ error: message });
            return false;
          }
        },

        setKeys: (keys) => {
          // Validate all keys
          const validatedKeys: Record<string, ServiceKey> = {};

          Object.entries(keys).forEach(([keyId, key]) => {
            const result = ServiceKeySchema.safeParse(key);
            if (result.success) {
              validatedKeys[keyId] = result.data;
            } else {
              console.error(`Invalid key data for ${keyId}:`, result.error);
            }
          });

          set({ keys: validatedKeys });
        },

        // Validation actions
        validateKey: async (keyId, options = {}) => {
          const key = get().keys[keyId];
          if (!key) {
            throw new Error("Key not found");
          }

          set((state) => ({
            isValidating: { ...state.isValidating, [keyId]: true },
          }));

          try {
            // Mock validation - replace with actual API calls
            await new Promise((resolve) => setTimeout(resolve, 1000));

            const validationResult: ValidationResult = {
              isValid: true,
              status: "active",
              message: "Key is valid and active",
              testedAt: getCurrentTimestamp(),
              responseTime: Math.random() * 500 + 100,
            };

            const result = ValidationResultSchema.parse(validationResult);

            // Update key with validation results
            set((state) => ({
              keys: {
                ...state.keys,
                [keyId]: {
                  ...state.keys[keyId],
                  status: result.status,
                  isValid: result.isValid,
                  lastValidated: result.testedAt,
                },
              },
              isValidating: { ...state.isValidating, [keyId]: false },
              validationErrors: (() => {
                const newErrors = { ...state.validationErrors };
                delete newErrors[keyId];
                return newErrors;
              })(),
            }));

            return result;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Validation failed";
            const validationResult: ValidationResult = {
              isValid: false,
              status: "invalid",
              message,
              testedAt: getCurrentTimestamp(),
            };

            set((state) => ({
              keys: {
                ...state.keys,
                [keyId]: {
                  ...state.keys[keyId],
                  status: "invalid",
                  isValid: false,
                  lastValidated: validationResult.testedAt,
                },
              },
              isValidating: { ...state.isValidating, [keyId]: false },
              validationErrors: {
                ...state.validationErrors,
                [keyId]: message,
              },
            }));

            return validationResult;
          }
        },

        validateAllKeys: async () => {
          const keys = Object.keys(get().keys);
          const results: Record<string, ValidationResult> = {};

          await Promise.all(
            keys.map(async (keyId) => {
              try {
                results[keyId] = await get().validateKey(keyId);
              } catch (error) {
                console.error(`Failed to validate key ${keyId}:`, error);
              }
            })
          );

          return results;
        },

        testKeyConnection: async (keyInput) => {
          try {
            // Mock connection test - replace with actual API calls
            await new Promise((resolve) => setTimeout(resolve, 500));

            return ValidationResultSchema.parse({
              isValid: true,
              status: "active",
              message: "Connection successful",
              testedAt: getCurrentTimestamp(),
              responseTime: Math.random() * 300 + 50,
            });
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Connection test failed";
            return ValidationResultSchema.parse({
              isValid: false,
              status: "invalid",
              message,
              testedAt: getCurrentTimestamp(),
            });
          }
        },

        // Key status management
        setKeyStatus: (keyId, status) => {
          const result = ServiceKeyStatusSchema.safeParse(status);
          if (result.success) {
            set((state) => {
              const key = state.keys[keyId];
              if (!key) return state;

              return {
                keys: {
                  ...state.keys,
                  [keyId]: {
                    ...key,
                    status: result.data,
                    updatedAt: getCurrentTimestamp(),
                  },
                },
              };
            });
          }
        },

        markKeyAsUsed: (keyId) => {
          set((state) => {
            const key = state.keys[keyId];
            if (!key) return state;

            const now = getCurrentTimestamp();

            return {
              keys: {
                ...state.keys,
                [keyId]: {
                  ...key,
                  usage: {
                    ...key.usage,
                    requestCount: (key.usage?.requestCount || 0) + 1,
                    lastUsed: now,
                  },
                  updatedAt: now,
                },
              },
            };
          });
        },

        updateUsageStats: (keyId, requestCount = 1) => {
          set((state) => {
            const key = state.keys[keyId];
            if (!key) return state;

            const now = new Date();
            const today = now.toDateString();
            const month = `${now.getFullYear()}-${now.getMonth()}`;

            const lastUsed = key.usage?.lastUsed ? new Date(key.usage.lastUsed) : null;
            const isNewDay = !lastUsed || lastUsed.toDateString() !== today;
            const isNewMonth =
              !lastUsed || `${lastUsed.getFullYear()}-${lastUsed.getMonth()}` !== month;

            return {
              keys: {
                ...state.keys,
                [keyId]: {
                  ...key,
                  usage: {
                    ...key.usage,
                    requestCount: (key.usage?.requestCount || 0) + requestCount,
                    lastUsed: getCurrentTimestamp(),
                    dailyUsage: isNewDay
                      ? requestCount
                      : (key.usage?.dailyUsage || 0) + requestCount,
                    monthlyUsage: isNewMonth
                      ? requestCount
                      : (key.usage?.monthlyUsage || 0) + requestCount,
                  },
                  updatedAt: getCurrentTimestamp(),
                },
              },
            };
          });
        },

        // Bulk operations
        validateExpiredKeys: async () => {
          const keys = Object.values(get().keys);
          const expiredKeys = keys.filter((key) => {
            if (!key.expiresAt) return false;
            return new Date(key.expiresAt) <= new Date();
          });

          for (const key of expiredKeys) {
            await get().validateKey(key.id);
          }
        },

        refreshAllKeys: async () => {
          set({ isLoading: true });

          try {
            await get().validateAllKeys();
            set({ isLoading: false });
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to refresh keys";
            set({ isLoading: false, error: message });
          }
        },

        exportKeys: () => {
          const state = get();
          const exportData = {
            keys: state.keys,
            supportedServices: state.supportedServices,
            exportedAt: getCurrentTimestamp(),
            version: "1.0",
          };

          return JSON.stringify(exportData, null, 2);
        },

        importKeys: async (data) => {
          try {
            const importData = JSON.parse(data);

            if (importData.keys) {
              get().setKeys(importData.keys);
            }

            if (importData.supportedServices) {
              get().setSupportedServices(importData.supportedServices);
            }

            return true;
          } catch (error) {
            const message =
              error instanceof Error ? error.message : "Failed to import keys";
            set({ error: message });
            return false;
          }
        },

        // Service-specific helpers
        getKeyByService: (service) => {
          const keys = Object.values(get().keys);
          return (
            keys.find((key) => key.service === service && key.status === "active") ||
            null
          );
        },

        getKeysByServiceType: (serviceType) => {
          const keys = Object.values(get().keys);
          return keys.filter((key) => key.serviceType === serviceType);
        },

        getRequiredMissingServices: () => {
          const { supportedServices, keys } = get();
          const requiredServices = Object.values(supportedServices).filter(
            (service) => service.isRequired
          );
          const activeServices = new Set(
            Object.values(keys)
              .filter((key) => key.status === "active")
              .map((key) => key.service)
          );

          return requiredServices.filter(
            (service) => !activeServices.has(service.service)
          );
        },

        // Utility actions
        clearErrors: () => {
          set({
            error: null,
            validationErrors: {},
          });
        },

        clearValidationError: (keyId) => {
          set((state) => {
            const newValidationErrors = { ...state.validationErrors };
            delete newValidationErrors[keyId];
            return { validationErrors: newValidationErrors };
          });
        },

        reset: () => {
          set({
            keys: {},
            isLoading: false,
            isValidating: {},
            isSaving: {},
            error: null,
            validationErrors: {},
          });
        },
      }),
      {
        name: "service-keys-storage",
        partialize: (state) => ({
          // Only persist keys and service configurations
          keys: state.keys,
          supportedServices: state.supportedServices,
        }),
      }
    ),
    { name: "ServiceKeysStore" }
  )
);

// Utility selectors for common use cases
export const useServiceKeys = () =>
  useServiceKeysStore((state) => ({
    keys: state.keys,
    activeKeys: state.activeKeys,
    invalidKeys: state.invalidKeys,
    isLoading: state.isLoading,
    error: state.error,
  }));

export const useServiceKeyByService = (service: string) =>
  useServiceKeysStore((state) => state.getKeyByService(service));

export const useServiceKeysByType = (serviceType: ServiceType) =>
  useServiceKeysStore((state) => state.getKeysByServiceType(serviceType));

export const useServiceKeyValidation = (keyId: string) =>
  useServiceKeysStore((state) => ({
    isValidating: state.isValidating[keyId] || false,
    error: state.validationErrors[keyId] || null,
    validateKey: () => state.validateKey(keyId),
  }));

export const useSupportedServices = () =>
  useServiceKeysStore((state) => state.supportedServices);

export const useRequiredMissingServices = () =>
  useServiceKeysStore((state) => state.getRequiredMissingServices());

export const useServiceKeyUsageStats = () =>
  useServiceKeysStore((state) => state.totalUsageStats);
