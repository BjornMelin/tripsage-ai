// Export all stores for easy import

// Core foundation stores
export { useUIStore } from "./ui-store";
export { useAuthStore } from "./auth-store";
export { useServiceKeysStore } from "./service-keys-store";
export { useUserProfileStore } from "./user-store";

// Search stores (modernized with slice pattern)
export {
  useSearchStore,
  useSearchParamsStore,
  useSearchResultsStore,
  useSearchFiltersStore,
  useSearchHistoryStore,
} from "./search-store";

// Feature stores
export { useTripStore } from "./trip-store";
export { useChatStore } from "./chat-store";
export { useAgentStatusStore } from "./agent-status-store";
export { useBudgetStore } from "./budget-store";
export { useCurrencyStore } from "./currency-store";
export { useDealsStore } from "./deals-store";

// Export commonly used utility selectors from foundation stores
export * from "./ui-store";
export * from "./auth-store";
export * from "./service-keys-store";
export * from "./user-store";

// Export search utility selectors
export * from "./search-store";
