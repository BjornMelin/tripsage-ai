import { useEffect, useCallback, useMemo } from "react";
import { useDealsStore } from "@/stores/deals-store";
import type { Deal, DealAlert, DealType, DealState } from "@/types/deals";

/**
 * Custom hook for accessing and managing deals
 */
export function useDeals() {
  const dealsStore = useDealsStore();
  
  // Initialize the store if not already initialized
  useEffect(() => {
    if (!dealsStore.isInitialized) {
      dealsStore.initialize();
    }
  }, [dealsStore.isInitialized, dealsStore.initialize]);
  
  // Get all deals as array
  const allDeals = useMemo(() => Object.values(dealsStore.deals), [dealsStore.deals]);
  
  // Get filtered deals based on current filters
  const filteredDeals = useMemo(() => dealsStore.getFilteredDeals(), [dealsStore.getFilteredDeals]);
  
  // Get featured deals
  const featuredDeals = useMemo(() => dealsStore.getFeaturedDeals(), [dealsStore.getFeaturedDeals]);
  
  // Get saved deals
  const savedDeals = useMemo(() => dealsStore.getSavedDeals(), [dealsStore.getSavedDeals]);
  
  // Get recently viewed deals
  const recentlyViewedDeals = useMemo(() => dealsStore.getRecentlyViewedDeals(), [dealsStore.getRecentlyViewedDeals]);
  
  // Get deal statistics
  const dealStats = useMemo(() => dealsStore.getDealsStats(), [dealsStore.getDealsStats]);
  
  // Utility to check if a deal is saved
  const isDealSaved = useCallback(
    (dealId: string) => dealsStore.savedDeals.includes(dealId),
    [dealsStore.savedDeals]
  );
  
  // Utility to check if a deal is featured
  const isDealFeatured = useCallback(
    (dealId: string) => dealsStore.featuredDeals.includes(dealId),
    [dealsStore.featuredDeals]
  );
  
  // Filter by deal type
  const filterByType = useCallback(
    (type: DealType) => {
      const currentFilters = dealsStore.filters || {};
      const types = currentFilters.types || [];
      
      // Toggle the type
      let newTypes: DealType[];
      if (types.includes(type)) {
        newTypes = types.filter(t => t !== type);
      } else {
        newTypes = [...types, type];
      }
      
      dealsStore.setFilters({
        ...currentFilters,
        types: newTypes.length > 0 ? newTypes : undefined,
      });
    },
    [dealsStore.filters, dealsStore.setFilters]
  );
  
  // Filter by destination
  const filterByDestination = useCallback(
    (destination: string) => {
      const currentFilters = dealsStore.filters || {};
      const destinations = currentFilters.destinations || [];
      
      // Toggle the destination
      let newDestinations: string[];
      if (destinations.includes(destination)) {
        newDestinations = destinations.filter(d => d !== destination);
      } else {
        newDestinations = [...destinations, destination];
      }
      
      dealsStore.setFilters({
        ...currentFilters,
        destinations: newDestinations.length > 0 ? newDestinations : undefined,
      });
    },
    [dealsStore.filters, dealsStore.setFilters]
  );
  
  // Set multiple filters at once
  const setFilters = useCallback(
    (filters: DealState["filters"]) => {
      dealsStore.setFilters(filters);
    },
    [dealsStore.setFilters]
  );
  
  // Sort deals by various criteria
  const sortDeals = useCallback(
    (deals: Deal[], sortBy: "price" | "discount" | "expiry" | "created", direction: "asc" | "desc" = "asc") => {
      return [...deals].sort((a, b) => {
        let comparison = 0;
        
        switch (sortBy) {
          case "price":
            comparison = a.price - b.price;
            break;
          case "discount":
            const discountA = a.discountPercentage || 0;
            const discountB = b.discountPercentage || 0;
            comparison = discountA - discountB;
            break;
          case "expiry":
            comparison = new Date(a.expiryDate).getTime() - new Date(b.expiryDate).getTime();
            break;
          case "created":
            comparison = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
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
    return allDeals.reduce((acc, deal) => {
      const destination = deal.destination;
      if (!acc[destination]) {
        acc[destination] = [];
      }
      acc[destination].push(deal);
      return acc;
    }, {} as Record<string, Deal[]>);
  }, [allDeals]);
  
  // Group deals by type
  const dealsByType = useMemo(() => {
    return allDeals.reduce((acc, deal) => {
      const type = deal.type;
      if (!acc[type]) {
        acc[type] = [];
      }
      acc[type].push(deal);
      return acc;
    }, {} as Record<DealType, Deal[]>);
  }, [allDeals]);
  
  // Get unique destinations
  const uniqueDestinations = useMemo(() => {
    return [...new Set(allDeals.map(deal => deal.destination))];
  }, [allDeals]);
  
  // Get unique providers
  const uniqueProviders = useMemo(() => {
    return [...new Set(allDeals.map(deal => deal.provider))];
  }, [allDeals]);
  
  return {
    // State
    deals: dealsStore.deals,
    allDeals,
    filteredDeals,
    featuredDeals,
    savedDeals,
    recentlyViewedDeals,
    alerts: dealsStore.alerts,
    filters: dealsStore.filters,
    lastUpdated: dealsStore.lastUpdated,
    
    // Computed
    dealStats,
    dealsByDestination,
    dealsByType,
    uniqueDestinations,
    uniqueProviders,
    
    // Checks
    isDealSaved,
    isDealFeatured,
    
    // Actions
    addDeal: dealsStore.addDeal,
    updateDeal: dealsStore.updateDeal,
    removeDeal: dealsStore.removeDeal,
    
    addToSavedDeals: dealsStore.addToSavedDeals,
    removeFromSavedDeals: dealsStore.removeFromSavedDeals,
    
    addToFeaturedDeals: dealsStore.addToFeaturedDeals,
    removeFromFeaturedDeals: dealsStore.removeFromFeaturedDeals,
    
    addToRecentlyViewed: dealsStore.addToRecentlyViewed,
    clearRecentlyViewed: dealsStore.clearRecentlyViewed,
    
    addAlert: dealsStore.addAlert,
    updateAlert: dealsStore.updateAlert,
    removeAlert: dealsStore.removeAlert,
    toggleAlertActive: dealsStore.toggleAlertActive,
    
    // Filtering & Sorting
    filterByType,
    filterByDestination,
    setFilters,
    clearFilters: dealsStore.clearFilters,
    sortDeals,
    
    // Utilities
    getDealById: dealsStore.getDealById,
    getAlertById: dealsStore.getAlertById,
    
    // Reset
    reset: dealsStore.reset,
  };
}

/**
 * Custom hook for managing deal alerts
 */
export function useDealAlerts() {
  const { alerts, addAlert, updateAlert, removeAlert, toggleAlertActive } = useDeals();
  
  // Get active alerts
  const activeAlerts = useMemo(() => alerts.filter(alert => alert.isActive), [alerts]);
  
  // Get alerts by type
  const alertsByType = useMemo(() => {
    return alerts.reduce((acc, alert) => {
      const type = alert.dealType;
      if (type) {
        if (!acc[type]) {
          acc[type] = [];
        }
        acc[type].push(alert);
      }
      return acc;
    }, {} as Record<DealType, DealAlert[]>);
  }, [alerts]);
  
  return {
    alerts,
    activeAlerts,
    alertsByType,
    addAlert,
    updateAlert,
    removeAlert,
    toggleAlertActive,
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
    sortDeals 
  } = useDeals();
  
  // Sort featured deals by discount (highest first)
  const sortedByDiscount = useMemo(
    () => sortDeals(featuredDeals, "discount", "desc"),
    [featuredDeals, sortDeals]
  );
  
  // Get top deals (highest discount)
  const topDeals = useMemo(
    () => sortedByDiscount.slice(0, 5),
    [sortedByDiscount]
  );
  
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
    featuredDeals,
    sortedByDiscount,
    topDeals,
    addToFeaturedDeals,
    removeFromFeaturedDeals,
    toggleFeatured,
    isDealFeatured,
  };
}

/**
 * Custom hook for saved deals
 */
export function useSavedDeals() {
  const { 
    savedDeals, 
    addToSavedDeals, 
    removeFromSavedDeals, 
    isDealSaved,
    sortDeals 
  } = useDeals();
  
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
    
    return savedDeals.filter(deal => {
      const expiryDate = new Date(deal.expiryDate);
      return expiryDate <= threeDaysFromNow && expiryDate >= new Date();
    });
  }, [savedDeals]);
  
  return {
    savedDeals,
    sortedByExpiry,
    expiringSoon,
    addToSavedDeals,
    removeFromSavedDeals,
    toggleSaved,
    isDealSaved,
  };
}