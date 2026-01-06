/**
 * @fileoverview Server helpers for TanStack Query prefetch + dehydration.
 */

import "server-only";

import {
  type DehydratedState,
  dehydrate,
  type QueryClient,
} from "@tanstack/react-query";
import { createQueryClient } from "@/lib/query/query-client";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/**
 * Prefetches queries on the server and returns dehydrated state for client hydration.
 *
 * Creates a `QueryClient`, executes the provided `prefetch` callback to populate
 * queries, and dehydrates the resulting state for SSR/RSC hydration workflows.
 *
 * Errors are logged via the server logger and re-thrown for upstream handling.
 *
 * @param prefetch - Async callback that receives a `QueryClient` to prefetch queries.
 * @returns Dehydrated query state for client rehydration.
 *
 * @example
 * const state = await prefetchDehydratedState(async (queryClient) => {
 *   await queryClient.prefetchQuery({ queryKey: ["example"], queryFn: fetcher });
 * });
 */
export function prefetchDehydratedState(
  prefetch: (queryClient: QueryClient) => Promise<void>
): Promise<DehydratedState> {
  const logger = createServerLogger("query.prefetch");

  return withTelemetrySpan("query.prefetch.dehydrate", {}, async (span) => {
    try {
      const queryClient = createQueryClient();
      await prefetch(queryClient);

      const state = dehydrate(queryClient);
      span.setAttribute("query.prefetch.queries_count", state.queries.length);
      return state;
    } catch (error) {
      logger.error("Prefetch dehydration failed", { error });
      throw error;
    }
  });
}
