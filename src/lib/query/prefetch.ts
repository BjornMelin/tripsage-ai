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
