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

export async function prefetchDehydratedState(
  prefetch: (queryClient: QueryClient) => Promise<void>
): Promise<DehydratedState> {
  const queryClient = createQueryClient();
  await prefetch(queryClient);

  const state = dehydrate(queryClient);
  queryClient.clear();
  return state;
}
