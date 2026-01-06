/**
 * @fileoverview Trips route (RSC shell) with TanStack Query prefetch + hydration.
 */

import { requireUser } from "@/lib/auth/server";
import { keys } from "@/lib/keys";
import { HydrationBoundary } from "@/lib/query/hydration-boundary";
import { prefetchDehydratedState } from "@/lib/query/prefetch";
import { listTripsForUser } from "@/server/queries/trips";
import TripsClient from "./trips-client";

export default async function TripsPage() {
  const { supabase, user } = await requireUser();

  const state = await prefetchDehydratedState(async (queryClient) => {
    await queryClient.prefetchQuery({
      queryFn: () => listTripsForUser(supabase, { currentUserId: user.id }),
      queryKey: keys.trips.list(user.id),
    });
  });

  return (
    <HydrationBoundary state={state}>
      <TripsClient userId={user.id} />
    </HydrationBoundary>
  );
}
