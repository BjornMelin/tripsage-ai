/**
 * @fileoverview Zustand store for managing travel deals, alerts, and filters.
 */

import {
  DEAL_ALERT_SCHEMA,
  DEAL_SCHEMA,
  type Deal,
  type DealAlert,
  type DealState,
  type DealStats,
  type DealType,
} from "@schemas/deals";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { compact } from "@/lib/collection-utils";
import { nowIso, secureId } from "@/lib/security/random";
import { createStoreLogger } from "@/lib/telemetry/store-logger";

const logger = createStoreLogger({ storeName: "deals" });

interface DealsStore extends DealState {
  // Base state fields materialized on the store
  deals: Record<string, Deal>;
  featuredDeals: string[];
  savedDeals: string[];
  recentlyViewedDeals: string[];
  alerts: DealAlert[];
  filters: DealState["filters"] | undefined;
  lastUpdated: string | null;
  isInitialized: boolean;
  // Deals management
  setDeals: (deals: Record<string, Deal>) => void;
  addDeal: (deal: unknown) => boolean;
  updateDeal: (id: string, updates: Partial<Deal>) => boolean;
  removeDeal: (id: string) => void;

  // Featured deals
  setFeaturedDeals: (dealIds: string[]) => void;
  addToFeaturedDeals: (dealId: string) => void;
  removeFromFeaturedDeals: (dealId: string) => void;

  // Deal alerts
  setAlerts: (alerts: DealAlert[]) => void;
  addAlert: (alert: unknown) => boolean;
  updateAlert: (id: string, updates: Partial<DealAlert>) => boolean;
  removeAlert: (id: string) => void;
  toggleAlertActive: (id: string) => void;

  // Saved deals
  setSavedDeals: (dealIds: string[]) => void;
  addToSavedDeals: (dealId: string) => void;
  removeFromSavedDeals: (dealId: string) => void;

  // Recently viewed deals
  addToRecentlyViewed: (dealId: string) => void;
  clearRecentlyViewed: () => void;

  // Filtering
  setFilters: (filters: DealState["filters"]) => void;
  clearFilters: () => void;

  // Computed properties & utilities
  getDealById: (id: string) => Deal | undefined;
  getAlertById: (id: string) => DealAlert | undefined;
  getFilteredDeals: () => Deal[];
  getFeaturedDeals: () => Deal[];
  getSavedDeals: () => Deal[];
  getRecentlyViewedDeals: () => Deal[];
  getDealsStats: () => DealStats;

  // State management
  initialize: () => void;
  reset: () => void;
}

// Helper functions
const GENERATE_ID = () => secureId(12);
const GET_CURRENT_TIMESTAMP = () => nowIso();

// Utility for validating deal objects
const _validateDeal = (deal: unknown): deal is Deal => {
  return DEAL_SCHEMA.safeParse(deal).success;
};

// Utility for validating alert objects
const _validateAlert = (alert: unknown): alert is DealAlert => {
  return DEAL_ALERT_SCHEMA.safeParse(alert).success;
};

// Calculate percentage discount
const CALCULATE_DISCOUNT_PERCENTAGE = (
  originalPrice: number,
  price: number
): number => {
  if (originalPrice <= 0 || price <= 0 || originalPrice <= price) return 0;
  return Math.round(((originalPrice - price) / originalPrice) * 100);
};

// Calculate deals statistics
const CALCULATE_DEALS_STATS = (deals: Deal[]): DealStats => {
  // Skip if no deals
  if (deals.length === 0) {
    return {
      avgDiscount: 0,
      avgSavings: 0,
      byDestination: {},
      byType: {
        accommodation: 0,
        activity: 0,
        // biome-ignore lint/style/useNamingConvention: External API field names
        error_fare: 0,
        // biome-ignore lint/style/useNamingConvention: External API field names
        flash_sale: 0,
        flight: 0,
        package: 0,
        promotion: 0,
        transportation: 0,
      },
      totalCount: 0,
    };
  }

  // Count by type
  const byType: Record<DealType, number> = {
    accommodation: 0,
    activity: 0,
    // biome-ignore lint/style/useNamingConvention: External API field names
    error_fare: 0,
    // biome-ignore lint/style/useNamingConvention: External API field names
    flash_sale: 0,
    flight: 0,
    package: 0,
    promotion: 0,
    transportation: 0,
  };

  // Count by destination
  const byDestination: Record<string, number> = {};

  // Calculate average savings and discount
  let totalSavings = 0;
  let dealsWithSavings = 0;
  let totalDiscountPercentage = 0;
  let dealsWithDiscount = 0;

  for (const deal of deals) {
    // Count by type
    byType[deal.type] = (byType[deal.type] || 0) + 1;

    // Count by destination
    byDestination[deal.destination] = (byDestination[deal.destination] || 0) + 1;

    // Calculate savings and discount
    if (deal.originalPrice && deal.originalPrice > deal.price) {
      totalSavings += deal.originalPrice - deal.price;
      dealsWithSavings++;
    }

    if (deal.discountPercentage && deal.discountPercentage > 0) {
      totalDiscountPercentage += deal.discountPercentage;
      dealsWithDiscount++;
    } else if (deal.originalPrice && deal.originalPrice > deal.price) {
      const discount = CALCULATE_DISCOUNT_PERCENTAGE(deal.originalPrice, deal.price);
      totalDiscountPercentage += discount;
      dealsWithDiscount++;
    }
  }

  // Calculate averages
  const avgSavings = dealsWithSavings > 0 ? totalSavings / dealsWithSavings : 0;
  const avgDiscount =
    dealsWithDiscount > 0 ? totalDiscountPercentage / dealsWithDiscount : 0;

  return {
    avgDiscount,
    avgSavings,
    byDestination,
    byType,
    totalCount: deals.length,
  };
};

// Match deal against filters
const MATCH_DEAL_WITH_FILTERS = (
  deal: Deal,
  filters?: DealState["filters"]
): boolean => {
  if (!filters) return true;

  // Match deal type
  if (filters.types && filters.types.length > 0 && !filters.types.includes(deal.type)) {
    return false;
  }

  // Match origin
  if (filters.origins && filters.origins.length > 0) {
    if (!deal.origin || !filters.origins.includes(deal.origin)) {
      return false;
    }
  }

  // Match destination
  if (filters.destinations && filters.destinations.length > 0) {
    if (!filters.destinations.includes(deal.destination)) {
      return false;
    }
  }

  // Match provider
  if (filters.providers && filters.providers.length > 0) {
    if (!filters.providers.includes(deal.provider)) {
      return false;
    }
  }

  // Match minimum discount
  if (filters.minDiscount !== undefined && filters.minDiscount > 0) {
    const discount =
      deal.discountPercentage ||
      (deal.originalPrice
        ? CALCULATE_DISCOUNT_PERCENTAGE(deal.originalPrice, deal.price)
        : 0);

    if (discount < filters.minDiscount) {
      return false;
    }
  }

  // Match maximum price
  if (filters.maxPrice !== undefined && filters.maxPrice > 0) {
    if (deal.price > filters.maxPrice) {
      return false;
    }
  }

  // Match date range
  if (filters.dateRange) {
    const { start, end } = filters.dateRange;

    if (start && deal.startDate && new Date(deal.startDate) < new Date(start)) {
      return false;
    }

    if (end && deal.endDate && new Date(deal.endDate) > new Date(end)) {
      return false;
    }
  }

  return true;
};

export const useDealsStore = create<DealsStore>()(
  persist(
    (set, get) => ({
      addAlert: (alert) => {
        const result = DEAL_ALERT_SCHEMA.safeParse(alert);
        if (result.success) {
          set((state) => {
            const newAlert = {
              ...result.data,
              createdAt: result.data.createdAt || GET_CURRENT_TIMESTAMP(),
              id: result.data.id || GENERATE_ID(),
              updatedAt: GET_CURRENT_TIMESTAMP(),
            };

            return {
              alerts: [...state.alerts, newAlert],
            };
          });
          return true;
        }
        logger.error("Invalid alert data", { error: result.error });
        return false;
      },

      addDeal: (deal) => {
        const result = DEAL_SCHEMA.safeParse(deal);
        if (result.success) {
          set((state) => {
            // Ensure deal has required timestamps
            const newDeal = {
              ...result.data,
              createdAt: result.data.createdAt || GET_CURRENT_TIMESTAMP(),
              updatedAt: GET_CURRENT_TIMESTAMP(),
            };

            return {
              deals: {
                ...state.deals,
                [newDeal.id]: newDeal,
              },
              lastUpdated: GET_CURRENT_TIMESTAMP(),
            };
          });
          return true;
        }
        logger.error("Invalid deal data", { error: result.error });
        return false;
      },

      addToFeaturedDeals: (dealId) =>
        set((state) => {
          if (!state.deals[dealId] || state.featuredDeals.includes(dealId)) {
            return state;
          }

          return {
            featuredDeals: [...state.featuredDeals, dealId],
          };
        }),

      // Recently viewed deals
      addToRecentlyViewed: (dealId) =>
        set((state) => {
          if (!state.deals[dealId]) return state;

          // Remove if already exists (to move to front)
          const filtered = state.recentlyViewedDeals.filter((id) => id !== dealId);

          // Add to front and limit to 20 items
          return {
            recentlyViewedDeals: [dealId, ...filtered].slice(0, 20),
          };
        }),

      addToSavedDeals: (dealId) =>
        set((state) => {
          if (!state.deals[dealId] || state.savedDeals.includes(dealId)) {
            return state;
          }

          return {
            savedDeals: [...state.savedDeals, dealId],
          };
        }),
      alerts: [],

      clearFilters: () => set({ filters: undefined }),

      clearRecentlyViewed: () => set({ recentlyViewedDeals: [] }),
      // Initial state
      deals: {},
      featuredDeals: [],
      filters: undefined,

      getAlertById: (id) => {
        const state = get();
        return state.alerts.find((alert) => alert.id === id);
      },

      // Computed properties & utilities
      getDealById: (id) => {
        const state = get();
        return state.deals[id];
      },

      getDealsStats: () => {
        const state = get();
        const allDeals = Object.values(state.deals);
        return CALCULATE_DEALS_STATS(allDeals);
      },

      getFeaturedDeals: () => {
        const state = get();
        return compact(state.featuredDeals.map((id) => state.deals[id]));
      },

      getFilteredDeals: () => {
        const state = get();
        const allDeals = Object.values(state.deals);

        if (!state.filters) return allDeals;

        return allDeals.filter((deal) => MATCH_DEAL_WITH_FILTERS(deal, state.filters));
      },

      getRecentlyViewedDeals: () => {
        const state = get();
        return compact(state.recentlyViewedDeals.map((id) => state.deals[id]));
      },

      getSavedDeals: () => {
        const state = get();
        return compact(state.savedDeals.map((id) => state.deals[id]));
      },

      // State management
      initialize: () => set({ isInitialized: true }),
      isInitialized: false,
      lastUpdated: null,
      recentlyViewedDeals: [],

      removeAlert: (id) =>
        set((state) => ({
          alerts: state.alerts.filter((alert) => alert.id !== id),
        })),

      removeDeal: (id) =>
        set((state) => {
          const { deals, featuredDeals, savedDeals, recentlyViewedDeals } = state;

          // Remove from all collections
          const newDeals = { ...deals };
          delete newDeals[id];

          const newFeaturedDeals = featuredDeals.filter((dealId) => dealId !== id);
          const newSavedDeals = savedDeals.filter((dealId) => dealId !== id);
          const newRecentlyViewedDeals = recentlyViewedDeals.filter(
            (dealId) => dealId !== id
          );

          return {
            deals: newDeals,
            featuredDeals: newFeaturedDeals,
            lastUpdated: GET_CURRENT_TIMESTAMP(),
            recentlyViewedDeals: newRecentlyViewedDeals,
            savedDeals: newSavedDeals,
          };
        }),

      removeFromFeaturedDeals: (dealId) =>
        set((state) => ({
          featuredDeals: state.featuredDeals.filter((id) => id !== dealId),
        })),

      removeFromSavedDeals: (dealId) =>
        set((state) => ({
          savedDeals: state.savedDeals.filter((id) => id !== dealId),
        })),

      reset: () =>
        set({
          alerts: [],
          deals: {},
          featuredDeals: [],
          filters: undefined,
          isInitialized: false,
          lastUpdated: null,
          recentlyViewedDeals: [],
          savedDeals: [],
        }),
      savedDeals: [],

      // Deal alerts
      setAlerts: (alerts) => set({ alerts }),

      // Deals management
      setDeals: (deals) =>
        set(() => ({
          deals,
          lastUpdated: GET_CURRENT_TIMESTAMP(),
        })),

      // Featured deals
      setFeaturedDeals: (dealIds) => set({ featuredDeals: dealIds }),

      // Filtering
      setFilters: (filters) => set({ filters }),

      // Saved deals
      setSavedDeals: (dealIds) => set({ savedDeals: dealIds }),

      toggleAlertActive: (id) =>
        set((state) => {
          const alertIndex = state.alerts.findIndex((alert) => alert.id === id);
          if (alertIndex === -1) return state;

          const newAlerts = [...state.alerts];
          newAlerts[alertIndex] = {
            ...newAlerts[alertIndex],
            isActive: !newAlerts[alertIndex].isActive,
            updatedAt: GET_CURRENT_TIMESTAMP(),
          };

          return {
            alerts: newAlerts,
          };
        }),

      updateAlert: (id, updates) => {
        const state = get();
        const alertIndex = state.alerts.findIndex((alert) => alert.id === id);
        if (alertIndex === -1) return false;

        const existingAlert = state.alerts[alertIndex];
        const updatedAlert = {
          ...existingAlert,
          ...updates,
          updatedAt: GET_CURRENT_TIMESTAMP(),
        };

        const result = DEAL_ALERT_SCHEMA.safeParse(updatedAlert);
        if (!result.success) {
          logger.error("Invalid alert update", { error: result.error });
          return false;
        }

        const newAlerts = [...state.alerts];
        newAlerts[alertIndex] = updatedAlert;

        set({
          alerts: newAlerts,
        });
        return true;
      },

      updateDeal: (id, updates) => {
        const state = get();
        const existingDeal = state.deals[id];
        if (!existingDeal) return false;

        const updatedDeal = {
          ...existingDeal,
          ...updates,
          updatedAt: GET_CURRENT_TIMESTAMP(),
        };

        const result = DEAL_SCHEMA.safeParse(updatedDeal);
        if (!result.success) {
          logger.error("Invalid deal update", { error: result.error });
          return false;
        }

        set({
          deals: {
            ...state.deals,
            [id]: updatedDeal,
          },
          lastUpdated: GET_CURRENT_TIMESTAMP(),
        });
        return true;
      },
    }),
    {
      name: "deals-storage",
      partialize: (state) => ({
        alerts: state.alerts,
        // Only persist certain parts of the state
        featuredDeals: state.featuredDeals,
        isInitialized: state.isInitialized,
        recentlyViewedDeals: state.recentlyViewedDeals,
        savedDeals: state.savedDeals,
        // Don't persist deals, as they may become outdated
        // Don't persist filters, reset them on reload
      }),
    }
  )
);
