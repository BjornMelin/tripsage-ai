"use client";

import type { Activity } from "@schemas/search";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ActivityCard } from "@/components/features/search/activity-card";
import { ActivitySearchForm } from "@/components/features/search/activity-search-form";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import {
  type ActivitySearchParams,
  useActivitySearch,
} from "@/hooks/use-activity-search";
import { openActivityBooking } from "@/lib/activities/booking";

// URL search parameters are handled inline

export default function ActivitiesSearchPage() {
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);
  const { searchActivities, isSearching, searchError, results, searchMetadata } =
    useActivitySearch();
  const searchParams = useSearchParams();

  // Initialize search with URL parameters
  useEffect(() => {
    const destination = searchParams.get("destination");
    const category = searchParams.get("category");

    if (destination) {
      const initialParams: ActivitySearchParams = {
        category: category || undefined,
        destination,
      };
      searchActivities(initialParams);
    }
  }, [searchParams, searchActivities]);

  const handleSearch = (params: import("@schemas/search").ActivitySearchParams) => {
    if (params.destination) {
      searchActivities(params);
    }
  };

  const handleSelectActivity = (activity: Activity) => {
    setSelectedActivity(activity);
    // TODO: Integrate with trip planning or booking flow
  };

  const handleCompareActivity = (_activity: Activity) => {
    // TODO: Add to comparison list
  };

  const activities = results ?? [];
  const hasActiveResults = activities.length > 0;

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
          {isSearching && (
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

          {!isSearching && hasActiveResults && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">
                  {activities.length} Activities Found
                </h2>
                {searchMetadata?.cached && (
                  <span className="text-sm text-muted-foreground">Cached results</span>
                )}
              </div>

              {searchMetadata?.notes && searchMetadata.notes.length > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 space-y-1">
                  {searchMetadata.notes.map((note) => (
                    <p key={note} className="text-sm text-blue-800">
                      {note}
                    </p>
                  ))}
                </div>
              )}

              {searchMetadata?.primarySource === "mixed" && (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold mb-2">Verified Activities</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {activities
                        .filter(
                          (a) =>
                            !a.id.startsWith("ai_fallback:") &&
                            searchMetadata.sources.includes("googleplaces")
                        )
                        .map((activity) => (
                          <ActivityCard
                            key={activity.id}
                            activity={activity}
                            onSelect={handleSelectActivity}
                            onCompare={handleCompareActivity}
                            sourceLabel="Verified via Google Places"
                          />
                        ))}
                    </div>
                  </div>
                  {activities.some((a) => a.id.startsWith("ai_fallback:")) && (
                    <div>
                      <h3 className="text-lg font-semibold mb-2">
                        More Ideas Powered by AI
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {activities
                          .filter((a) => a.id.startsWith("ai_fallback:"))
                          .map((activity) => (
                            <ActivityCard
                              key={activity.id}
                              activity={activity}
                              onSelect={handleSelectActivity}
                              onCompare={handleCompareActivity}
                              sourceLabel="AI suggestion"
                            />
                          ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {searchMetadata?.primarySource !== "mixed" && (
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
              )}
            </div>
          )}

          {!isSearching && !hasActiveResults && !searchError && (
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
                  if (selectedActivity) {
                    const opened = openActivityBooking(selectedActivity);
                    if (!opened) {
                      // Fallback: show message that booking is unavailable
                      alert(
                        "Booking link unavailable for this activity. Please search for booking options manually."
                      );
                    }
                  }
                  setSelectedActivity(null);
                }}
                className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-md"
              >
                View Booking Options
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
