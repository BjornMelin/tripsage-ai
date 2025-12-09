/**
 * @fileoverview React hook for dashboard metrics data fetching.
 *
 * Uses @tanstack/react-query with automatic polling for fresh data.
 * Validates API responses with Zod schema for type safety.
 */

"use client";

import type { DashboardMetrics, TimeWindow } from "@schemas/dashboard";
import { dashboardMetricsSchema } from "@schemas/dashboard";
import { useQuery } from "@tanstack/react-query";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { queryKeys, staleTimes } from "@/lib/query-keys";

/**
 * Options for the useDashboardMetrics hook.
 */
export interface UseDashboardMetricsOptions {
  /** Time window for metrics aggregation (default: "24h") */
  window?: TimeWindow;
  /** Enable/disable automatic polling (default: true) */
  polling?: boolean;
  /** Custom refetch interval in milliseconds (default: 30000) */
  refetchInterval?: number;
  /** Enable/disable the query (default: true) */
  enabled?: boolean;
}

/**
 * Hook for fetching dashboard metrics with automatic polling.
 *
 * @param options - Configuration options for the hook
 * @returns Query result with metrics data, loading state, and error handling
 *
 * @example
 * ```tsx
 * const { data, isLoading, isError } = useDashboardMetrics({ window: "7d" });
 * ```
 */
export function useDashboardMetrics(options: UseDashboardMetricsOptions = {}) {
  const {
    window = "24h",
    polling = true,
    refetchInterval = 30000,
    enabled = true,
  } = options;

  const { authenticatedApi } = useAuthenticatedApi();

  return useQuery({
    enabled,
    queryFn: async (): Promise<DashboardMetrics> => {
      const response = await authenticatedApi.get<DashboardMetrics>(
        `/dashboard?window=${window}`
      );
      // Validate response against schema for runtime type safety
      return dashboardMetricsSchema.parse(response);
    },
    queryKey: queryKeys.dashboard.metrics(window),
    refetchInterval: polling ? refetchInterval : false,
    refetchIntervalInBackground: false,
    staleTime: staleTimes.dashboard,
  });
}
