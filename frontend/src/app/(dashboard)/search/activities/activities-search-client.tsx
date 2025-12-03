/**
 * @fileoverview Client-side activity search experience (renders within RSC shell).
 */

"use client";

import type { Activity, ActivitySearchParams } from "@schemas/search";
import type { UiTrip } from "@schemas/trips";
import {
  AlertCircleIcon,
  CheckCircleIcon,
  InfoIcon,
  SearchIcon,
  SparklesIcon,
  TicketIcon,
  XIcon,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ActivityCard } from "@/components/features/search/activity-card";
import { ActivityComparisonModal } from "@/components/features/search/activity-comparison-modal";
import { ActivitySearchForm } from "@/components/features/search/activity-search-form";
import { TripSelectionModal } from "@/components/features/search/trip-selection-modal";
import { SearchLayout } from "@/components/layouts/search-layout";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { CardLoadingSkeleton } from "@/components/ui/query-states";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useToast } from "@/components/ui/use-toast";
import { useActivitySearch } from "@/hooks/search/use-activity-search";
import { openActivityBooking } from "@/lib/activities/booking";
import { getErrorMessage } from "@/lib/api/error-types";
import { addActivityToTrip, getPlanningTrips } from "./actions";

const AI_FALLBACK_PREFIX = "ai_fallback:";
const GOOGLE_PLACES_SOURCE = "googleplaces";
/** Maximum number of items allowed in comparison views. */
const MAX_COMPARISON_ITEMS = 3;

/** Activity search client component props. */
interface ActivitiesSearchClientProps {
  onSubmitServer: (params: ActivitySearchParams) => Promise<ActivitySearchParams>;
}

/** Activity search client component. */
export default function ActivitiesSearchClient({
  onSubmitServer,
}: ActivitiesSearchClientProps) {
  const { toast } = useToast();
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);
  const {
    searchActivities,
    isSearching,
    searchError,
    setSearchError,
    results,
    searchMetadata,
  } = useActivitySearch();
  const searchParams = useSearchParams();
  const primaryActionRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const [pendingAddFromComparison, setPendingAddFromComparison] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const noteItems = searchMetadata?.notes?.map((note, index) => ({
    id: `note-${index}`,
    note,
  }));

  const [isTripModalOpen, setIsTripModalOpen] = useState(false);
  const [trips, setTrips] = useState<UiTrip[]>([]);
  const [isPending, setIsPending] = useState(false);

  // Initialize search with URL parameters
  useEffect(() => {
    const destination = searchParams.get("destination");
    const category = searchParams.get("category");

    if (destination) {
      const initialParams: ActivitySearchParams = {
        category: category || undefined,
        destination,
      };
      setHasSearched(true);
      (async () => {
        try {
          await onSubmitServer(initialParams);
          await searchActivities(initialParams);
        } catch (error) {
          const message = getErrorMessage(error);
          setSearchError(new Error(message));
          toast({
            description: message,
            title: "Search failed",
            variant: "destructive",
          });
        }
      })();
    }
  }, [searchParams, searchActivities, onSubmitServer, setSearchError, toast]);

  const handleSearch = async (params: ActivitySearchParams) => {
    if (params.destination) {
      setHasSearched(true);
      try {
        await onSubmitServer(params); // server-side telemetry and validation
      } catch (error) {
        const message = getErrorMessage(error);
        setSearchError(new Error(message));
        return;
      }

      try {
        await searchActivities(params); // client fetch/store update
      } catch (error) {
        const message = getErrorMessage(error);
        setSearchError(new Error(message));
      }
    }
  };

  const handleAddToTripClick = useCallback(async () => {
    setIsPending(true);
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
    } finally {
      setIsPending(false);
    }
  }, [toast]);

  const handleConfirmAddToTrip = async (tripId: string) => {
    if (!selectedActivity) return;

    setIsPending(true);
    try {
      await addActivityToTrip(tripId, {
        currency: "USD",
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
      });

      setIsTripModalOpen(false);
      setSelectedActivity(null);
    } catch (error) {
      toast({
        description: getErrorMessage(error),
        title: "Error",
        variant: "destructive",
      });
    } finally {
      setIsPending(false);
    }
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
    const isCurrentlySelected = comparisonList.has(activity.id);

    if (isCurrentlySelected) {
      setComparisonList((prev) => {
        const next = new Set(prev);
        next.delete(activity.id);
        return next;
      });
      toast({
        description: `Removed "${activity.name}" from comparison`,
        title: "Removed from comparison",
      });
      const nextSize = Math.max(0, comparisonList.size - 1);
      return { nextSize, wasAdded: false };
    }

    if (comparisonList.size >= MAX_COMPARISON_ITEMS) {
      toast({
        description: `You can compare up to ${MAX_COMPARISON_ITEMS} activities at once`,
        title: "Comparison limit reached",
        variant: "destructive",
      });
      return { nextSize: comparisonList.size, wasAdded: false };
    }

    setComparisonList((prev) => {
      const next = new Set(prev);
      next.add(activity.id);
      return next;
    });

    toast({
      description: `Added "${activity.name}" to comparison`,
      title: "Added to comparison",
    });

    const nextSize = comparisonList.size + 1;
    return { nextSize, wasAdded: true };
  };

  const handleCompareActivity = (activity: Activity) => {
    const { nextSize, wasAdded } = toggleComparison(activity);

    if (wasAdded && nextSize >= 2) {
      setShowComparisonModal(true);
    } else if (!wasAdded && nextSize <= 1) {
      setShowComparisonModal(false);
    }
  };

  const handleRemoveFromComparison = (activityId: string) => {
    setComparisonList((prev) => {
      const newSet = new Set(prev);
      newSet.delete(activityId);

      if (newSet.size <= 1) {
        setShowComparisonModal(false);
      }

      return newSet;
    });
  };

  const handleAddFromComparison = (activity: Activity) => {
    setSelectedActivity(activity);
    setPendingAddFromComparison(true);
    setShowComparisonModal(false);
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
    if (!selectedActivity) return;

    const focusTarget =
      (primaryActionRef.current && !primaryActionRef.current.disabled
        ? primaryActionRef.current
        : null) ?? closeButtonRef.current;

    focusTarget?.focus();
  }, [selectedActivity]);

  useEffect(() => {
    if (!showComparisonModal && pendingAddFromComparison) {
      setPendingAddFromComparison(false);
      handleAddToTripClick();
    }
  }, [handleAddToTripClick, pendingAddFromComparison, showComparisonModal]);

  const handleBookActivity = () => {
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
          description: getErrorMessage(error),
          title: "Booking unavailable",
          variant: "destructive",
        });
      }
    }
    setSelectedActivity(null);
  };

  return (
    <SearchLayout>
      <TooltipProvider>
        <div className="space-y-6">
          {/* Search Form Section */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TicketIcon className="h-5 w-5" />
                    Search Activities
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ActivitySearchForm onSearch={handleSearch} />
                </CardContent>
              </Card>
            </div>

            <div className="lg:col-span-2 space-y-4">
              {/* Comparison Bar */}
              {comparisonList.size > 0 && (
                <Card className="border-primary/50 bg-primary/5">
                  <CardContent className="py-4">
                    <div className="flex items-center justify-between flex-wrap gap-4">
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary">
                          {comparisonList.size}/{MAX_COMPARISON_ITEMS}
                        </Badge>
                        <span className="text-sm font-medium">
                          Activities selected for comparison
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              size="sm"
                              onClick={() => setShowComparisonModal(true)}
                              disabled={comparisonList.size < 2}
                            >
                              Compare Now
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>
                            {comparisonList.size < 2
                              ? "Select at least 2 activities"
                              : "Open comparison view"}
                          </TooltipContent>
                        </Tooltip>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setComparisonList(new Set());
                            toast({
                              description: "Comparison list cleared",
                              title: "Cleared",
                            });
                          }}
                        >
                          Clear
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Loading State */}
              {isSearching && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <SearchIcon className="h-5 w-5 animate-pulse" />
                      Searching activities...
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardLoadingSkeleton count={3} />
                  </CardContent>
                </Card>
              )}

              {/* Error State */}
              {searchError && (
                <Alert variant="destructive">
                  <AlertCircleIcon className="h-4 w-4" />
                  <AlertTitle>Search Error</AlertTitle>
                  <AlertDescription>
                    {searchError.message || "Something went wrong"}
                  </AlertDescription>
                </Alert>
              )}

              {/* Results */}
              {!isSearching && hasActiveResults && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold flex items-center gap-2">
                      <CheckCircleIcon className="h-5 w-5 text-green-500" />
                      {activities.length} Activities Found
                    </h2>
                    {searchMetadata?.cached && (
                      <Badge variant="outline">Cached results</Badge>
                    )}
                  </div>

                  {/* Notes */}
                  {noteItems && noteItems.length > 0 && (
                    <Alert>
                      <InfoIcon className="h-4 w-4" />
                      <AlertTitle>Search Notes</AlertTitle>
                      <AlertDescription>
                        <ul className="list-disc list-inside space-y-1">
                          {noteItems.map((item) => (
                            <li key={item.id}>{item.note}</li>
                          ))}
                        </ul>
                      </AlertDescription>
                    </Alert>
                  )}

                  {/* Mixed Results (Verified + AI) */}
                  {searchMetadata?.primarySource === "mixed" && (
                    <div className="space-y-6">
                      <div>
                        <div className="flex items-center gap-2 mb-4">
                          <CheckCircleIcon className="h-5 w-5 text-green-500" />
                          <h3 className="text-lg font-semibold">Verified Activities</h3>
                          <Badge variant="secondary">Google Places</Badge>
                        </div>
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
                        <>
                          <Separator />
                          <div>
                            <div className="flex items-center gap-2 mb-4">
                              <SparklesIcon className="h-5 w-5 text-purple-500" />
                              <h3 className="text-lg font-semibold">
                                More Ideas Powered by AI
                              </h3>
                              <Badge variant="secondary" className="bg-purple-100">
                                AI Suggestions
                              </Badge>
                            </div>
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
                        </>
                      )}
                    </div>
                  )}

                  {/* Standard Results */}
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

              {/* Empty State */}
              {!isSearching && !hasActiveResults && !searchError && hasSearched && (
                <Card>
                  <CardContent className="text-center py-12">
                    <div className="flex flex-col items-center gap-4">
                      <div className="rounded-full bg-muted p-4">
                        <SearchIcon className="h-8 w-8 text-muted-foreground" />
                      </div>
                      <div className="space-y-2">
                        <h3 className="text-lg font-semibold">No activities found</h3>
                        <p className="text-muted-foreground max-w-md">
                          Try searching for a different destination or adjusting your
                          filters.
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Initial State */}
              {!isSearching && !hasSearched && !searchError && (
                <Card className="bg-muted/50">
                  <CardContent className="text-center py-12">
                    <div className="flex flex-col items-center gap-4">
                      <div className="rounded-full bg-background p-4 shadow-sm">
                        <TicketIcon className="h-8 w-8 text-primary" />
                      </div>
                      <div className="space-y-2">
                        <h3 className="text-lg font-semibold">
                          Discover Amazing Activities
                        </h3>
                        <p className="text-muted-foreground max-w-md">
                          Search for activities and experiences at your destination.
                          Compare options and add them to your trip.
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>

          {/* Floating Compare Button */}
          {comparisonList.size > 0 && (
            <div className="fixed bottom-6 right-6 z-40">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="lg"
                    onClick={() => setShowComparisonModal(true)}
                    disabled={comparisonList.size < 2}
                    className="shadow-lg"
                  >
                    <TicketIcon className="h-4 w-4 mr-2" />
                    Compare ({comparisonList.size})
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="left">
                  {comparisonList.size < 2
                    ? `Select ${2 - comparisonList.size} more to compare`
                    : "Open comparison view"}
                </TooltipContent>
              </Tooltip>
            </div>
          )}

          {/* Comparison Modal */}
          <ActivityComparisonModal
            isOpen={showComparisonModal}
            onClose={() => setShowComparisonModal(false)}
            activities={comparisonActivities}
            onRemove={handleRemoveFromComparison}
            onAddToTrip={handleAddFromComparison}
          />

          {/* Activity Selection Dialog */}
          <Dialog
            open={!!selectedActivity && !isTripModalOpen}
            onOpenChange={(open) => !open && setSelectedActivity(null)}
          >
            <DialogContent>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <TicketIcon className="h-5 w-5" />
                  Activity Selected
                </DialogTitle>
                <DialogDescription>{selectedActivity?.name}</DialogDescription>
              </DialogHeader>
              <div className="py-4">
                <p className="text-sm text-muted-foreground">
                  What would you like to do with this activity?
                </p>
              </div>
              <DialogFooter className="flex-col sm:flex-row gap-2">
                <Button
                  variant="outline"
                  ref={closeButtonRef}
                  onClick={() => setSelectedActivity(null)}
                  className="flex-1"
                >
                  <XIcon className="h-4 w-4 mr-2" />
                  Close
                </Button>
                <Button
                  ref={primaryActionRef}
                  onClick={handleAddToTripClick}
                  disabled={isPending}
                  className="flex-1"
                >
                  {isPending ? "Loading..." : "Add to Trip"}
                </Button>
                <Button
                  variant="secondary"
                  onClick={handleBookActivity}
                  className="flex-1"
                >
                  Book Now
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* Trip Selection Modal */}
          {selectedActivity && isTripModalOpen && (
            <TripSelectionModal
              isOpen={isTripModalOpen}
              onClose={() => {
                setIsTripModalOpen(false);
                setSelectedActivity(null);
              }}
              activity={selectedActivity}
              trips={trips}
              onAddToTrip={handleConfirmAddToTrip}
              isAdding={isPending}
            />
          )}
        </div>
      </TooltipProvider>
    </SearchLayout>
  );
}
