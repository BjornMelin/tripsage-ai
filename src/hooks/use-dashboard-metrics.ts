/**
 * @fileoverview React hook for dashboard metrics data fetching.
 */

"use client";

import type { DashboardMetrics, TimeWindow } from "@schemas/dashboard";
import { dashboardMetricsSchema } from "@schemas/dashboard";
import { useQuery } from "@tanstack/react-query";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { useCurrentUserId } from "@/hooks/use-current-user-id";
import { keys } from "@/lib/keys";
import { staleTimes } from "@/lib/query/config";

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
  const userId = useCurrentUserId();
  const isEnabled = enabled && !!userId;

  return useQuery({
    enabled: isEnabled,
    queryFn: async (): Promise<DashboardMetrics> => {
      const response = await authenticatedApi.get<DashboardMetrics>(
        `/dashboard?window=${window}`
      );
      // Validate response against schema for runtime type safety
      return dashboardMetricsSchema.parse(response);
    },
    queryKey: userId
      ? keys.dashboard.metrics(userId, window)
      : keys.dashboard.metricsDisabled(),
    refetchInterval: polling ? refetchInterval : false,
    refetchIntervalInBackground: false,
    staleTime: staleTimes.dashboard,
  });
}
