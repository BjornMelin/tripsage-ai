"use client";

import { ActivityCard } from "@/components/features/search/activity-card";
import { ActivitySearchForm } from "@/components/features/search/activity-search-form";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import {
  type ActivitySearchParams,
  useActivitySearch,
} from "@/hooks/use-activity-search";
import { useSearchStore } from "@/stores/search-store";
import type { Activity } from "@/types/search";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

// URL search parameters are handled inline

export default function ActivitiesSearchPage() {
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);
  const { searchActivities, isSearching, searchError } = useActivitySearch();
  const { hasResults, isSearching: storeIsSearching } = useSearchStore();
  const searchParams = useSearchParams();

  // Initialize search with URL parameters
  useEffect(() => {
    const destination = searchParams.get("destination");
    // const date = searchParams.get("date"); // Future use
    const category = searchParams.get("category");
    // const maxPrice = searchParams.get("maxPrice"); // Future use

    if (destination) {
      const initialParams: ActivitySearchParams = {
        destination,
        category: category || undefined,
      };
      searchActivities(initialParams);
    }
  }, [searchParams, searchActivities]);

  const handleSearch = (params: import("@/types/search").ActivitySearchParams) => {
    // Convert the params to the hook's expected format
    if (params.destination) {
      const hookParams: ActivitySearchParams = {
        destination: params.destination,
        category: params.category,
      };
      searchActivities(hookParams);
    }
  };

  const handleSelectActivity = (activity: Activity) => {
    setSelectedActivity(activity);
    console.log("Selected activity:", activity);
    // TODO: Integrate with trip planning or booking flow
  };

  const handleCompareActivity = (activity: Activity) => {
    console.log("Compare activity:", activity);
    // TODO: Add to comparison list
  };

  // Mock activities data - in real implementation, this would come from the search results
  const activities: Activity[] = [];
  const hasActiveResults = hasResults && activities.length > 0;

  return (
    <div className="container mx-auto py-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Search Activities</h1>
        <p className="text-muted-foreground">
          Discover exciting activities and experiences for your trip
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <ActivitySearchForm onSearch={handleSearch} />
        </div>

        <div className="lg:col-span-2">
          {(storeIsSearching || isSearching) && (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner />
              <span className="ml-2">Searching activities...</span>
            </div>
          )}

          {searchError && (
            <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
              <p className="text-destructive text-sm">
                {searchError?.message || "Something went wrong"}
              </p>
            </div>
          )}

          {!storeIsSearching && !isSearching && hasActiveResults && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">
                  {activities.length} Activities Found
                </h2>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {activities.map((activity) => (
                  <ActivityCard
                    key={activity.id}
                    activity={activity}
                    onSelect={handleSelectActivity}
                    onCompare={handleCompareActivity}
                  />
                ))}
              </div>
            </div>
          )}

          {!storeIsSearching && !isSearching && !hasActiveResults && !searchError && (
            <div className="text-center py-12">
              <p className="text-muted-foreground">
                Use the search form to find activities at your destination
              </p>
            </div>
          )}
        </div>
      </div>

      {selectedActivity && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-background rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold mb-4">Activity Selected</h3>
            <p className="text-sm text-muted-foreground mb-4">
              You selected: {selectedActivity.name}
            </p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setSelectedActivity(null)}
                className="flex-1 px-4 py-2 bg-secondary text-secondary-foreground rounded-md"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => {
                  // TODO: Add to trip or proceed to booking
                  setSelectedActivity(null);
                }}
                className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-md"
              >
                Add to Trip
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
