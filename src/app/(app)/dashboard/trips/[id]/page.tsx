/**
 * @fileoverview Trip detail route (RSC shell) with TanStack Query prefetch + hydration.
 */

import "server-only";

import { notFound } from "next/navigation";
import { TripDetailClient } from "@/features/trips/components/trip-detail-client";
import { requireUser } from "@/lib/auth/server";
import { keys } from "@/lib/keys";
import { HydrationBoundary } from "@/lib/query/hydration-boundary";
import { prefetchDehydratedState } from "@/lib/query/prefetch";
import { listItineraryItemsForTrip } from "@/server/queries/itinerary-items";
import { getTripByIdForUser } from "@/server/queries/trips";

type TripDetailPageProps = {
  params: Promise<{ id: string }>;
};

export default async function TripDetailPage({ params }: TripDetailPageProps) {
  const { supabase, user } = await requireUser();
  const { id } = await params;

  const tripId = Number.parseInt(id, 10);
  if (!Number.isFinite(tripId) || tripId <= 0) {
    notFound();
  }

  const detailKey = keys.trips.detail(user.id, tripId);

  const trip = await getTripByIdForUser(supabase, {
    currentUserId: user.id,
    tripId,
  });
  if (!trip) {
    notFound();
  }

  const state = await prefetchDehydratedState(async (queryClient) => {
    queryClient.setQueryData(detailKey, trip);

    await queryClient.prefetchQuery({
      queryFn: () => listItineraryItemsForTrip(supabase, { tripId }),
      queryKey: keys.trips.itinerary(user.id, tripId),
    });
  });

  return (
    <HydrationBoundary state={state}>
      <TripDetailClient tripId={tripId} userId={user.id} />
    </HydrationBoundary>
  );
}
