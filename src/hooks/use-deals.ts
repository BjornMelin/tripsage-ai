/**
 * @fileoverview React hooks for deals management and filtering.
 */

"use client";

import type { Deal, DealFilters, DealState, DealType } from "@schemas/deals";
import { useCallback, useEffect, useMemo } from "react";
import { useShallow } from "zustand/react/shallow";
import { useDealsStore } from "@/features/search/store/deals-store";
import { groupBy, mapToUnique } from "@/lib/collection-utils";

/**
 * Hook for accessing and managing deals.
 *
 * @returns Deal state, selectors, and actions for managing deals.
 */
export function useDeals() {
  const {
    addAlert,
    addDeal,
    addToFeaturedDeals,
    addToRecentlyViewed,
    addToSavedDeals,
    alerts,
    clearFilters,
    clearRecentlyViewed,
    deals,
    featuredDealItems,
    featuredDeals: featuredDealIds,
    filters,
    getAlertById,
    getDealById,
    getDealsStats,
    getFilteredDeals,
    initialize,
    isInitialized,
    lastUpdated,
    recentlyViewedDealItems,
    removeAlert,
    removeDeal,
    removeFromFeaturedDeals,
    removeFromSavedDeals,
    reset,
    savedDealItems,
    savedDeals: savedDealIds,
    setFilters: setFiltersInternal,
    toggleAlertActive,
    updateAlert,
    updateDeal,
  } = useDealsStore(
    useShallow((state) => ({
      addAlert: state.addAlert,
      addDeal: state.addDeal,
      addToFeaturedDeals: state.addToFeaturedDeals,
      addToRecentlyViewed: state.addToRecentlyViewed,
      addToSavedDeals: state.addToSavedDeals,
      alerts: state.alerts,
      clearFilters: state.clearFilters,
      clearRecentlyViewed: state.clearRecentlyViewed,
      deals: state.deals,
      featuredDealItems: state.featuredDealItems,
      featuredDeals: state.featuredDeals,
      filters: state.filters,
      getAlertById: state.getAlertById,
      getDealById: state.getDealById,
      getDealsStats: state.getDealsStats,
      getFilteredDeals: state.getFilteredDeals,
      initialize: state.initialize,
      isInitialized: state.isInitialized,
      lastUpdated: state.lastUpdated,
      recentlyViewedDealItems: state.recentlyViewedDealItems,
      removeAlert: state.removeAlert,
      removeDeal: state.removeDeal,
      removeFromFeaturedDeals: state.removeFromFeaturedDeals,
      removeFromSavedDeals: state.removeFromSavedDeals,
      reset: state.reset,
      savedDealItems: state.savedDealItems,
      savedDeals: state.savedDeals,
      setFilters: state.setFilters,
      toggleAlertActive: state.toggleAlertActive,
      updateAlert: state.updateAlert,
      updateDeal: state.updateDeal,
    }))
  );

  // Initialize the store if not already initialized
  useEffect(() => {
    if (!isInitialized) {
      initialize();
    }
  }, [initialize, isInitialized]);

  // Get all deals as array
  const allDeals = useMemo(() => Object.values(deals), [deals]);

  // Get filtered deals based on current filters
  // biome-ignore lint/correctness/useExhaustiveDependencies: ensure memo recomputes on state changes used inside store selectors.
  const filteredDeals = useMemo(
    () => getFilteredDeals(),
    [getFilteredDeals, deals, filters]
  );

  // Get featured deals
  const featuredDeals = featuredDealItems;

  // Get saved deals
  const savedDeals = savedDealItems;

  // Get recently viewed deals
  const recentlyViewedDeals = recentlyViewedDealItems;

  // Get deal statistics
  // biome-ignore lint/correctness/useExhaustiveDependencies: ensure memo recomputes on state changes used inside store selectors.
  const dealStats = useMemo(() => getDealsStats(), [getDealsStats, deals, filters]);

  // Convert IDs to Sets for O(1) membership checks.
  const savedDealIdSet = useMemo(() => new Set(savedDealIds), [savedDealIds]);
  const featuredDealIdSet = useMemo(() => new Set(featuredDealIds), [featuredDealIds]);

  // Utility to check if a deal is saved
  const isDealSaved = useCallback(
    (dealId: string) => savedDealIdSet.has(dealId),
    [savedDealIdSet]
  );

  // Utility to check if a deal is featured
  const isDealFeatured = useCallback(
    (dealId: string) => featuredDealIdSet.has(dealId),
    [featuredDealIdSet]
  );

  // Filter by deal type
  const filterByType = useCallback(
    (type: DealType) => {
      const currentFilters: DealFilters = filters ?? {};
      const types: DealType[] = currentFilters.types || [];

      // Toggle the type
      let newTypes: DealType[];
      if (types.includes(type)) {
        newTypes = types.filter((t) => t !== type);
      } else {
        newTypes = [...types, type];
      }

      setFiltersInternal({
        ...currentFilters,
        types: newTypes.length > 0 ? newTypes : undefined,
      });
    },
    [filters, setFiltersInternal]
  );

  // Filter by destination
  const filterByDestination = useCallback(
    (destination: string) => {
      const currentFilters: DealFilters = filters ?? {};
      const destinations: string[] = currentFilters.destinations || [];

      // Toggle the destination
      let newDestinations: string[];
      if (destinations.includes(destination)) {
        newDestinations = destinations.filter((d) => d !== destination);
      } else {
        newDestinations = [...destinations, destination];
      }

      setFiltersInternal({
        ...currentFilters,
        destinations: newDestinations.length > 0 ? newDestinations : undefined,
      });
    },
    [filters, setFiltersInternal]
  );

  // Set multiple filters at once
  const setFilters = useCallback(
    (filters: DealState["filters"]) => {
      setFiltersInternal(filters);
    },
    [setFiltersInternal]
  );

  // Sort deals by various criteria
  const sortDeals = useCallback(
    (
      deals: Deal[],
      sortBy: "price" | "discount" | "expiry" | "created",
      direction: "asc" | "desc" = "asc"
    ) => {
      return [...deals].sort((a, b) => {
        let comparison = 0;

        switch (sortBy) {
          case "price":
            comparison = a.price - b.price;
            break;
          case "discount": {
            const discountA = a.discountPercentage || 0;
            const discountB = b.discountPercentage || 0;
            comparison = discountA - discountB;
            break;
          }
          case "expiry":
            comparison =
              new Date(a.expiryDate).getTime() - new Date(b.expiryDate).getTime();
            break;
          case "created":
            comparison =
              new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
            break;
          default:
            comparison = 0;
        }

        return direction === "asc" ? comparison : -comparison;
      });
    },
    []
  );

  // Group deals by destination
  const dealsByDestination = useMemo(() => {
    return groupBy(allDeals, (deal) => deal.destination);
  }, [allDeals]);

  // Group deals by type
  const dealsByType = useMemo(() => {
    return groupBy(allDeals, (deal) => deal.type);
  }, [allDeals]);

  // Get unique destinations
  const uniqueDestinations = useMemo(() => {
    return mapToUnique(allDeals, (deal) => deal.destination);
  }, [allDeals]);

  // Get unique providers
  const uniqueProviders = useMemo(() => {
    return mapToUnique(allDeals, (deal) => deal.provider);
  }, [allDeals]);

  return {
    addAlert,

    // Actions
    addDeal,

    addToFeaturedDeals,

    addToRecentlyViewed,

    addToSavedDeals,
    alerts,
    allDeals,
    clearFilters,
    clearRecentlyViewed,

    // Computed
    dealStats,
    // State
    deals,
    dealsByDestination,
    dealsByType,
    featuredDeals,
    filterByDestination,

    // Filtering & Sorting
    filterByType,
    filteredDeals,
    filters,
    getAlertById,

    // Utilities
    getDealById,
    isDealFeatured,

    // Checks
    isDealSaved,
    lastUpdated,
    recentlyViewedDeals,
    removeAlert,
    removeDeal,
    removeFromFeaturedDeals,
    removeFromSavedDeals,

    // Reset
    reset,
    savedDeals,
    setFilters,
    sortDeals,
    toggleAlertActive,
    uniqueDestinations,
    uniqueProviders,
    updateAlert,
    updateDeal,
  };
}

/**
 * Custom hook for managing deal alerts
 */
export function useDealAlerts() {
  const { alerts, addAlert, updateAlert, removeAlert, toggleAlertActive } = useDeals();

  // Get active alerts
  const activeAlerts = useMemo(
    () => alerts.filter((alert) => alert.isActive),
    [alerts]
  );

  const isAlertWithDealType = useCallback(
    (
      alert: (typeof alerts)[number]
    ): alert is (typeof alerts)[number] & { dealType: string } =>
      typeof alert.dealType === "string" && alert.dealType.trim().length > 0,
    []
  );

  // Get alerts by type
  const alertsByType = useMemo(() => {
    return groupBy(alerts.filter(isAlertWithDealType), (alert) => alert.dealType);
  }, [alerts, isAlertWithDealType]);

  return {
    activeAlerts,
    addAlert,
    alerts,
    alertsByType,
    removeAlert,
    toggleAlertActive,
    updateAlert,
  };
}

/**
 * Custom hook for featured deals
 */
export function useFeaturedDeals() {
  const {
    featuredDeals,
    addToFeaturedDeals,
    removeFromFeaturedDeals,
    isDealFeatured,
    sortDeals,
  } = useDeals();

  // Sort featured deals by discount (highest first)
  const sortedByDiscount = useMemo(
    () => sortDeals(featuredDeals, "discount", "desc"),
    [featuredDeals, sortDeals]
  );

  // Get top deals (highest discount)
  const topDeals = useMemo(() => sortedByDiscount.slice(0, 5), [sortedByDiscount]);

  // Toggle featured status
  const toggleFeatured = useCallback(
    (dealId: string) => {
      if (isDealFeatured(dealId)) {
        removeFromFeaturedDeals(dealId);
      } else {
        addToFeaturedDeals(dealId);
      }
    },
    [isDealFeatured, addToFeaturedDeals, removeFromFeaturedDeals]
  );

  return {
    addToFeaturedDeals,
    featuredDeals,
    isDealFeatured,
    removeFromFeaturedDeals,
    sortedByDiscount,
    toggleFeatured,
    topDeals,
  };
}

/**
 * Custom hook for saved deals
 */
export function useSavedDeals() {
  const { savedDeals, addToSavedDeals, removeFromSavedDeals, isDealSaved, sortDeals } =
    useDeals();

  // Toggle saved status
  const toggleSaved = useCallback(
    (dealId: string) => {
      if (isDealSaved(dealId)) {
        removeFromSavedDeals(dealId);
      } else {
        addToSavedDeals(dealId);
      }
    },
    [isDealSaved, addToSavedDeals, removeFromSavedDeals]
  );

  // Sort saved deals by expiry (soonest first)
  const sortedByExpiry = useMemo(
    () => sortDeals(savedDeals, "expiry", "asc"),
    [savedDeals, sortDeals]
  );

  // Get deals expiring soon (within 3 days)
  const expiringSoon = useMemo(() => {
    const threeDaysFromNow = new Date();
    threeDaysFromNow.setDate(threeDaysFromNow.getDate() + 3);

    return savedDeals.filter((deal) => {
      const expiryDate = new Date(deal.expiryDate);
      return expiryDate <= threeDaysFromNow && expiryDate >= new Date();
    });
  }, [savedDeals]);

  return {
    addToSavedDeals,
    expiringSoon,
    isDealSaved,
    removeFromSavedDeals,
    savedDeals,
    sortedByExpiry,
    toggleSaved,
  };
}
