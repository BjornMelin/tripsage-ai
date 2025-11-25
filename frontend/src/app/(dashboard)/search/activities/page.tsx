/**
 * @fileoverview Activity search page with trip planning integration.
 * Allows searching for activities and adding them to existing trips.
 */

"use client";

import type { Activity } from "@schemas/search";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useRef, useState, useTransition } from "react";
import { ActivityCard } from "@/components/features/search/activity-card";
import { ActivityComparisonModal } from "@/components/features/search/activity-comparison-modal";
import { ActivitySearchForm } from "@/components/features/search/activity-search-form";
import { TripSelectionModal } from "@/components/features/search/trip-selection-modal";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { useToast } from "@/components/ui/use-toast";
import {
  type ActivitySearchParams,
  useActivitySearch,
} from "@/hooks/use-activity-search";
import { openActivityBooking } from "@/lib/activities/booking";
import { addActivityToTrip, getPlanningTrips } from "./actions";

const AI_FALLBACK_PREFIX = "ai_fallback:";
const GOOGLE_PLACES_SOURCE = "googleplaces";

// URL search parameters are handled inline

export default function ActivitiesSearchPage() {
  const { toast } = useToast();
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);
  const { searchActivities, isSearching, searchError, results, searchMetadata } =
    useActivitySearch();
  const searchParams = useSearchParams();
  const dialogRef = useRef<HTMLDivElement>(null);
  const noteItems = searchMetadata?.notes?.map((note, index) => ({
    id: `${note}-${index}`,
    note,
  }));

  const [isTripModalOpen, setIsTripModalOpen] = useState(false);
  const [trips, setTrips] = useState<import("@schemas/trips").UiTrip[]>([]);
  const [isPending, startTransition] = useTransition();

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

  const handleAddToTripClick = () => {
    startTransition(async () => {
      try {
        const fetchedTrips = await getPlanningTrips();
        setTrips(fetchedTrips);
        setIsTripModalOpen(true);
      } catch (_error) {
        toast({
          description: "Failed to load trips. Please try again.",
          title: "Error",
          variant: "destructive",
        });
      }
    });
  };

  const handleConfirmAddToTrip = async (tripId: string) => {
    if (!selectedActivity) return;

    await new Promise<void>((resolve) => {
      startTransition(async () => {
        try {
          await addActivityToTrip(Number(tripId), {
            currency: "USD", // Default
            description: selectedActivity.description,
            externalId: selectedActivity.id,
            location: selectedActivity.location,
            metadata: {
              images: selectedActivity.images,
              rating: selectedActivity.rating,
              type: selectedActivity.type,
            },
            price: selectedActivity.price,
            title: selectedActivity.name,
          });

          toast({
            description: `Added "${selectedActivity.name}" to your trip`,
            title: "Activity added",
            variant: "default",
          });

          setIsTripModalOpen(false);
          setSelectedActivity(null);
        } catch (error) {
          toast({
            description:
              error instanceof Error ? error.message : "Failed to add activity",
            title: "Error",
            variant: "destructive",
          });
        } finally {
          resolve();
        }
      });
    });
  };

  const handleSelectActivity = (activity: Activity) => {
    setSelectedActivity(activity);
  };

  const [comparisonList, setComparisonList] = useState<Set<string>>(new Set());
  const [showComparisonModal, setShowComparisonModal] = useState(false);

  // Load from sessionStorage on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = sessionStorage.getItem("activity-comparison-list");
      if (stored) {
        try {
          const ids = JSON.parse(stored) as string[];
          setComparisonList(new Set(ids));
        } catch {
          // Invalid storage, ignore
        }
      }
    }
  }, []);

  // Save to sessionStorage when comparison list changes
  useEffect(() => {
    if (typeof window !== "undefined") {
      if (comparisonList.size > 0) {
        sessionStorage.setItem(
          "activity-comparison-list",
          JSON.stringify(Array.from(comparisonList))
        );
      } else {
        sessionStorage.removeItem("activity-comparison-list");
      }
    }
  }, [comparisonList]);

  const toggleComparison = (activity: Activity) => {
    setComparisonList((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(activity.id)) {
        newSet.delete(activity.id);
        toast({
          description: `Removed "${activity.name}" from comparison`,
          title: "Removed from comparison",
          variant: "default",
        });
      } else {
        if (newSet.size >= 3) {
          toast({
            description: "You can compare up to 3 activities at once",
            title: "Comparison limit reached",
            variant: "default",
          });
          return prev;
        }
        newSet.add(activity.id);
        toast({
          description: `Added "${activity.name}" to comparison`,
          title: "Added to comparison",
          variant: "default",
        });
      }
      return newSet;
    });
  };

  const handleCompareActivity = (activity: Activity) => {
    toggleComparison(activity);
    // Auto-open comparison modal if 2+ items are selected and we just added one
    if (comparisonList.size >= 1 && !comparisonList.has(activity.id)) {
      setShowComparisonModal(true);
    }
  };

  const handleRemoveFromComparison = (activityId: string) => {
    setComparisonList((prev) => {
      const newSet = new Set(prev);
      newSet.delete(activityId);
      return newSet;
    });
    if (comparisonList.size <= 1) {
      setShowComparisonModal(false);
    }
  };

  const handleAddFromComparison = (activity: Activity) => {
    setShowComparisonModal(false);
    setSelectedActivity(activity);
    // Slight delay to allow modal transition
    setTimeout(() => {
      handleAddToTripClick();
    }, 100);
  };

  const activities = results ?? [];
  const hasActiveResults = activities.length > 0;

  const comparisonActivities = useMemo(() => {
    return activities.filter((a) => comparisonList.has(a.id));
  }, [activities, comparisonList]);

  const { verifiedActivities, aiSuggestions } = useMemo(() => {
    if (searchMetadata?.primarySource !== "mixed") {
      return {
        aiSuggestions: [] as Activity[],
        verifiedActivities: [] as Activity[],
      };
    }

    return {
      aiSuggestions: activities.filter((activity) =>
        activity.id.startsWith(AI_FALLBACK_PREFIX)
      ),
      verifiedActivities: activities.filter(
        (activity) =>
          !activity.id.startsWith(AI_FALLBACK_PREFIX) &&
          (searchMetadata.sources ?? []).includes(GOOGLE_PLACES_SOURCE)
      ),
    };
  }, [activities, searchMetadata?.primarySource, searchMetadata?.sources]);

  useEffect(() => {
    if (selectedActivity) {
      dialogRef.current?.focus();
    }
  }, [selectedActivity]);

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

              {noteItems && noteItems.length > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 space-y-1">
                  {noteItems.map((item) => (
                    <p key={item.id} className="text-sm text-blue-800">
                      {item.note}
                    </p>
                  ))}
                </div>
              )}

              {searchMetadata?.primarySource === "mixed" && (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-lg font-semibold mb-2">Verified Activities</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {verifiedActivities.map((activity) => (
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
                  {aiSuggestions.length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold mb-2">
                        More Ideas Powered by AI
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {aiSuggestions.map((activity) => (
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

      {comparisonList.size > 0 && (
        <div className="fixed bottom-6 right-6 z-40">
          <button
            type="button"
            onClick={() => setShowComparisonModal(true)}
            className="bg-primary text-primary-foreground px-4 py-2 rounded-full shadow-lg flex items-center gap-2 hover:bg-primary/90 transition-colors"
          >
            <span>Compare ({comparisonList.size})</span>
          </button>
        </div>
      )}

      <ActivityComparisonModal
        isOpen={showComparisonModal}
        onClose={() => setShowComparisonModal(false)}
        activities={comparisonActivities}
        onRemove={handleRemoveFromComparison}
        onAddToTrip={handleAddFromComparison}
      />

      {selectedActivity && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
          onClick={() => setSelectedActivity(null)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setSelectedActivity(null);
            }
          }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="activity-modal-title"
        >
          <div
            ref={dialogRef}
            tabIndex={-1}
            role="document"
            className="bg-background rounded-lg p-6 max-w-md w-full"
            onClick={(event) => event.stopPropagation()}
            onKeyDown={(event) => event.stopPropagation()}
          >
            <h3 id="activity-modal-title" className="text-lg font-semibold mb-4">
              Activity Selected
            </h3>
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
                onClick={handleAddToTripClick}
                disabled={isPending}
                className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-md"
              >
                {isPending ? "Loading..." : "Add to Trip"}
              </button>
              <button
                type="button"
                onClick={() => {
                  if (selectedActivity) {
                    try {
                      const opened = openActivityBooking(selectedActivity);
                      if (!opened) {
                        toast({
                          description:
                            "Booking link unavailable for this activity. Please search for booking options manually.",
                          title: "Booking unavailable",
                          variant: "destructive",
                        });
                      }
                    } catch (error) {
                      toast({
                        description:
                          error instanceof Error
                            ? error.message
                            : "Failed to open booking link",
                        title: "Booking unavailable",
                        variant: "destructive",
                      });
                    }
                  }
                  setSelectedActivity(null);
                }}
                className="flex-1 px-4 py-2 bg-outline border border-input hover:bg-accent hover:text-accent-foreground rounded-md"
              >
                Book Now
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedActivity && (
        <TripSelectionModal
          isOpen={isTripModalOpen}
          onClose={() => setIsTripModalOpen(false)}
          activity={selectedActivity}
          trips={trips}
          onAddToTrip={handleConfirmAddToTrip}
          isAdding={isPending}
        />
      )}
    </div>
  );
}
