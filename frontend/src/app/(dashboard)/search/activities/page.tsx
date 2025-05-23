"use client";

import { useState } from "react";
import { ActivitySearchForm } from "@/components/features/search/activity-search-form";
import { ActivityCard } from "@/components/features/search/activity-card";
import { SearchResults } from "@/components/features/search/search-results";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { useActivitySearch } from "@/lib/hooks/use-activity-search";
import { useSearchStore } from "@/stores/search-store";
import type { ActivitySearchParams, Activity } from "@/types/search";

export default function ActivitiesSearchPage() {
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(
    null
  );
  const { searchActivities, isSearching, searchError } = useActivitySearch();
  const { results, isLoading, error } = useSearchStore();

  const handleSearch = (params: ActivitySearchParams) => {
    searchActivities(params);
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

  const activities = results?.activities || [];
  const hasResults = activities.length > 0;

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
          {(isLoading || isSearching) && (
            <div className="flex items-center justify-center py-12">
              <LoadingSpinner />
              <span className="ml-2">Searching activities...</span>
            </div>
          )}

          {(error || searchError) && (
            <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
              <p className="text-destructive text-sm">
                {error || searchError?.message || "Something went wrong"}
              </p>
            </div>
          )}

          {!isLoading && !isSearching && hasResults && (
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

          {!isLoading &&
            !isSearching &&
            !hasResults &&
            !error &&
            !searchError && (
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
