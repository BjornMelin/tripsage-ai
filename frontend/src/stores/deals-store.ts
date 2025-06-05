import {
  type Deal,
  type DealAlert,
  DealAlertSchema,
  DealNotification,
  DealNotificationSchema,
  DealSchema,
  type DealState,
  type DealStats,
  type DealType,
  SearchDealsRequest,
} from "@/types/deals";
import { z } from "zod";
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface DealsStore extends DealState {
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
const generateId = () =>
  Date.now().toString(36) + Math.random().toString(36).substring(2, 5);
const getCurrentTimestamp = () => new Date().toISOString();

// Utility for validating deal objects
const validateDeal = (deal: unknown): deal is Deal => {
  return DealSchema.safeParse(deal).success;
};

// Utility for validating alert objects
const validateAlert = (alert: unknown): alert is DealAlert => {
  return DealAlertSchema.safeParse(alert).success;
};

// Calculate percentage discount
const calculateDiscountPercentage = (originalPrice: number, price: number): number => {
  if (originalPrice <= 0 || price <= 0 || originalPrice <= price) return 0;
  return Math.round(((originalPrice - price) / originalPrice) * 100);
};

// Calculate deals statistics
const calculateDealsStats = (deals: Deal[]): DealStats => {
  // Skip if no deals
  if (deals.length === 0) {
    return {
      totalCount: 0,
      byType: {},
      byDestination: {},
      avgDiscount: 0,
      avgSavings: 0,
    };
  }

  // Count by type
  const byType: Record<DealType, number> = {} as Record<DealType, number>;

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
      const discount = calculateDiscountPercentage(deal.originalPrice, deal.price);
      totalDiscountPercentage += discount;
      dealsWithDiscount++;
    }
  }

  // Calculate averages
  const avgSavings = dealsWithSavings > 0 ? totalSavings / dealsWithSavings : 0;
  const avgDiscount =
    dealsWithDiscount > 0 ? totalDiscountPercentage / dealsWithDiscount : 0;

  return {
    totalCount: deals.length,
    byType,
    byDestination,
    avgDiscount,
    avgSavings,
  };
};

// Match deal against filters
const matchDealWithFilters = (deal: Deal, filters?: DealState["filters"]): boolean => {
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
        ? calculateDiscountPercentage(deal.originalPrice, deal.price)
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
      // Initial state
      deals: {},
      featuredDeals: [],
      alerts: [],
      savedDeals: [],
      recentlyViewedDeals: [],
      filters: undefined,
      lastUpdated: null,
      isInitialized: false,

      // Deals management
      setDeals: (deals) =>
        set(() => ({
          deals,
          lastUpdated: getCurrentTimestamp(),
        })),

      addDeal: (deal) => {
        const result = DealSchema.safeParse(deal);
        if (result.success) {
          set((state) => {
            // Ensure deal has required timestamps
            const newDeal = {
              ...result.data,
              createdAt: result.data.createdAt || getCurrentTimestamp(),
              updatedAt: getCurrentTimestamp(),
            };

            return {
              deals: {
                ...state.deals,
                [newDeal.id]: newDeal,
              },
              lastUpdated: getCurrentTimestamp(),
            };
          });
          return true;
        }
        console.error("Invalid deal data:", result.error);
        return false;
      },

      updateDeal: (id, updates) => {
        const state = get();
        const existingDeal = state.deals[id];
        if (!existingDeal) return false;

        const updatedDeal = {
          ...existingDeal,
          ...updates,
          updatedAt: getCurrentTimestamp(),
        };

        const result = DealSchema.safeParse(updatedDeal);
        if (!result.success) {
          console.error("Invalid deal update:", result.error);
          return false;
        }

        set({
          deals: {
            ...state.deals,
            [id]: updatedDeal,
          },
          lastUpdated: getCurrentTimestamp(),
        });
        return true;
      },

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
            savedDeals: newSavedDeals,
            recentlyViewedDeals: newRecentlyViewedDeals,
            lastUpdated: getCurrentTimestamp(),
          };
        }),

      // Featured deals
      setFeaturedDeals: (dealIds) => set({ featuredDeals: dealIds }),

      addToFeaturedDeals: (dealId) =>
        set((state) => {
          if (!state.deals[dealId] || state.featuredDeals.includes(dealId)) {
            return state;
          }

          return {
            featuredDeals: [...state.featuredDeals, dealId],
          };
        }),

      removeFromFeaturedDeals: (dealId) =>
        set((state) => ({
          featuredDeals: state.featuredDeals.filter((id) => id !== dealId),
        })),

      // Deal alerts
      setAlerts: (alerts) => set({ alerts }),

      addAlert: (alert) => {
        const result = DealAlertSchema.safeParse(alert);
        if (result.success) {
          set((state) => {
            const newAlert = {
              ...result.data,
              id: result.data.id || generateId(),
              createdAt: result.data.createdAt || getCurrentTimestamp(),
              updatedAt: getCurrentTimestamp(),
            };

            return {
              alerts: [...state.alerts, newAlert],
            };
          });
          return true;
        }
        console.error("Invalid alert data:", result.error);
        return false;
      },

      updateAlert: (id, updates) => {
        const state = get();
        const alertIndex = state.alerts.findIndex((alert) => alert.id === id);
        if (alertIndex === -1) return false;

        const existingAlert = state.alerts[alertIndex];
        const updatedAlert = {
          ...existingAlert,
          ...updates,
          updatedAt: getCurrentTimestamp(),
        };

        const result = DealAlertSchema.safeParse(updatedAlert);
        if (!result.success) {
          console.error("Invalid alert update:", result.error);
          return false;
        }

        const newAlerts = [...state.alerts];
        newAlerts[alertIndex] = updatedAlert;

        set({
          alerts: newAlerts,
        });
        return true;
      },

      removeAlert: (id) =>
        set((state) => ({
          alerts: state.alerts.filter((alert) => alert.id !== id),
        })),

      toggleAlertActive: (id) =>
        set((state) => {
          const alertIndex = state.alerts.findIndex((alert) => alert.id === id);
          if (alertIndex === -1) return state;

          const newAlerts = [...state.alerts];
          newAlerts[alertIndex] = {
            ...newAlerts[alertIndex],
            isActive: !newAlerts[alertIndex].isActive,
            updatedAt: getCurrentTimestamp(),
          };

          return {
            alerts: newAlerts,
          };
        }),

      // Saved deals
      setSavedDeals: (dealIds) => set({ savedDeals: dealIds }),

      addToSavedDeals: (dealId) =>
        set((state) => {
          if (!state.deals[dealId] || state.savedDeals.includes(dealId)) {
            return state;
          }

          return {
            savedDeals: [...state.savedDeals, dealId],
          };
        }),

      removeFromSavedDeals: (dealId) =>
        set((state) => ({
          savedDeals: state.savedDeals.filter((id) => id !== dealId),
        })),

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

      clearRecentlyViewed: () => set({ recentlyViewedDeals: [] }),

      // Filtering
      setFilters: (filters) => set({ filters }),

      clearFilters: () => set({ filters: undefined }),

      // Computed properties & utilities
      getDealById: (id) => {
        const state = get();
        return state.deals[id];
      },

      getAlertById: (id) => {
        const state = get();
        return state.alerts.find((alert) => alert.id === id);
      },

      getFilteredDeals: () => {
        const state = get();
        const allDeals = Object.values(state.deals);

        if (!state.filters) return allDeals;

        return allDeals.filter((deal) => matchDealWithFilters(deal, state.filters));
      },

      getFeaturedDeals: () => {
        const state = get();
        return state.featuredDeals.map((id) => state.deals[id]).filter(Boolean);
      },

      getSavedDeals: () => {
        const state = get();
        return state.savedDeals.map((id) => state.deals[id]).filter(Boolean);
      },

      getRecentlyViewedDeals: () => {
        const state = get();
        return state.recentlyViewedDeals.map((id) => state.deals[id]).filter(Boolean);
      },

      getDealsStats: () => {
        const state = get();
        const allDeals = Object.values(state.deals);
        return calculateDealsStats(allDeals);
      },

      // State management
      initialize: () => set({ isInitialized: true }),

      reset: () =>
        set({
          deals: {},
          featuredDeals: [],
          alerts: [],
          savedDeals: [],
          recentlyViewedDeals: [],
          filters: undefined,
          lastUpdated: null,
          isInitialized: false,
        }),
    }),
    {
      name: "deals-storage",
      partialize: (state) => ({
        // Only persist certain parts of the state
        featuredDeals: state.featuredDeals,
        alerts: state.alerts,
        savedDeals: state.savedDeals,
        recentlyViewedDeals: state.recentlyViewedDeals,
        isInitialized: state.isInitialized,
        // Don't persist deals, as they may become outdated
        // Don't persist filters, reset them on reload
      }),
    }
  )
);
