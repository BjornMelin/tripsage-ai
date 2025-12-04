/**
 * @fileoverview Client-side activity search experience (renders within RSC shell).
 */

"use client";

import type { Activity, ActivitySearchParams } from "@schemas/search";
import type { UiTrip } from "@schemas/trips";
import {
  AlertCircleIcon,
  CheckCircleIcon,
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
import { useSearchOrchestration } from "@/hooks/search/use-search-orchestration";
import { openActivityBooking } from "@/lib/activities/booking";
import { getErrorMessage } from "@/lib/api/error-types";
import { useComparisonStore } from "@/stores/comparison-store";
import { useSearchResultsStore } from "@/stores/search-results-store";
import { addActivityToTrip, getPlanningTrips } from "./actions";

const AI_FALLBACK_PREFIX = "ai_fallback:";
/** Maximum number of items allowed in comparison views. */
const MAX_COMPARISON_ITEMS = 3;

/**
 * Activity search semantic colors aligned with statusVariants.
 * - Success indicator: green (active/success)
 * - AI suggestions: purple (distinct from verified results)
 */
const ACTIVITY_COLORS = {
  aiSuggestionBadge: "bg-purple-100",
  aiSuggestionIcon: "text-purple-500",
  successIcon: "text-green-700",
} as const;

const isActivity = (data: unknown): data is Activity =>
  typeof data === "object" && data !== null && "id" in data && "name" in data;

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
  const { initializeSearch, executeSearch, isSearching } = useSearchOrchestration();
  const searchError = useSearchResultsStore((state) => state.error);
  const activities = useSearchResultsStore((state) => state.results.activities ?? []);
  const searchMetadata = useSearchResultsStore((state) => state.metrics);
  const searchParams = useSearchParams();
  const primaryActionRef = useRef<HTMLButtonElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const [pendingAddFromComparison, setPendingAddFromComparison] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const { addItem, removeItem, clearByType, hasItem, getItemsByType } =
    useComparisonStore();

  const [isTripModalOpen, setIsTripModalOpen] = useState(false);
  const [trips, setTrips] = useState<UiTrip[]>([]);
  const [isPending, setIsPending] = useState(false);

  // Derived state for comparison list (computed per render to reflect store changes)
  const comparisonList = new Set(getItemsByType("activity").map((i) => i.id));

  // Initialize search type on mount
  useEffect(() => {
    initializeSearch("activity");
  }, [initializeSearch]);

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
          const normalizedParams = await onSubmitServer(initialParams);
          await executeSearch(normalizedParams ?? initialParams);
        } catch (error) {
          const message = getErrorMessage(error);
          toast({
            description: message,
            title: "Search failed",
            variant: "destructive",
          });
        }
      })();
    }
  }, [searchParams, executeSearch, onSubmitServer, toast]);

  const handleSearch = async (params: ActivitySearchParams) => {
    if (params.destination) {
      setHasSearched(true);
      try {
        const normalizedParams = await onSubmitServer(params); // server-side telemetry and validation
        await executeSearch(normalizedParams ?? params); // client fetch/store update
      } catch (error) {
        const message = getErrorMessage(error);
        toast({
          description: message,
          title: "Search failed",
          variant: "destructive",
        });
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
          ...(selectedActivity.images && { images: selectedActivity.images }),
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

  const [showComparisonModal, setShowComparisonModal] = useState(false);

  const toggleComparison = (activity: Activity) => {
    // Read current count from store selector (not memoized Set) for accurate size
    const currentCount = getItemsByType("activity").length;

    if (hasItem(activity.id)) {
      removeItem(activity.id);
      toast({
        description: `Removed "${activity.name}" from comparison`,
        title: "Removed from comparison",
      });
      return { nextSize: currentCount - 1, wasAdded: false };
    }

    if (currentCount >= MAX_COMPARISON_ITEMS) {
      toast({
        description: `You can compare up to ${MAX_COMPARISON_ITEMS} activities at once`,
        title: "Comparison limit reached",
        variant: "destructive",
      });
      return { nextSize: currentCount, wasAdded: false };
    }

    addItem("activity", activity.id, activity);
    toast({
      description: `Added "${activity.name}" to comparison`,
      title: "Added to comparison",
    });
    return { nextSize: currentCount + 1, wasAdded: true };
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
    // Read current count from store selector (not memoized Set) for accurate size
    const currentCount = getItemsByType("activity").length;
    removeItem(activityId);
    if (currentCount - 1 <= 1) {
      setShowComparisonModal(false);
    }
  };

  const handleAddFromComparison = (activity: Activity) => {
    setSelectedActivity(activity);
    setPendingAddFromComparison(true);
    setShowComparisonModal(false);
  };

  const hasActiveResults = activities.length > 0;

  const comparisonActivities = getItemsByType("activity")
    .map((item) => item.data)
    .filter(isActivity);

  const { verifiedActivities, aiSuggestions } = useMemo(() => {
    // Check if we have mixed results based on activity ID prefixes
    const hasMixedResults = activities.some((activity) =>
      activity.id.startsWith(AI_FALLBACK_PREFIX)
    );

    if (!hasMixedResults) {
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
        (activity) => !activity.id.startsWith(AI_FALLBACK_PREFIX)
      ),
    };
  }, [activities]);

  useEffect(() => {
    if (!selectedActivity) return;

    const canFocusPrimary =
      primaryActionRef.current && !primaryActionRef.current.disabled;
    const focusTarget = canFocusPrimary
      ? primaryActionRef.current
      : closeButtonRef.current;

    focusTarget?.focus();
  }, [selectedActivity]);

  useEffect(() => {
    if (!showComparisonModal && pendingAddFromComparison) {
      setPendingAddFromComparison(false);
      handleAddToTripClick();
    }
  }, [handleAddToTripClick, pendingAddFromComparison, showComparisonModal]);

  const handleBookActivity = () => {
    if (!selectedActivity) return;

    try {
      const opened = openActivityBooking(selectedActivity);
      if (!opened) {
        toast({
          description:
            "Booking link unavailable for this activity. Please search for booking options manually.",
          title: "Booking unavailable",
          variant: "destructive",
        });
        return;
      }
    } catch (error) {
      toast({
        description: getErrorMessage(error),
        title: "Booking unavailable",
        variant: "destructive",
      });
      return;
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
                            clearByType("activity");
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
                      <CheckCircleIcon
                        className={`h-5 w-5 ${ACTIVITY_COLORS.successIcon}`}
                      />
                      {activities.length} Activities Found
                    </h2>
                    {searchMetadata?.provider && (
                      <Badge variant="outline">
                        Provider: {searchMetadata.provider}
                      </Badge>
                    )}
                  </div>

                  {/* Mixed Results (Verified + AI) */}
                  {verifiedActivities.length > 0 && (
                    <div className="space-y-6">
                      <div>
                        <div className="flex items-center gap-2 mb-4">
                          <CheckCircleIcon
                            className={`h-5 w-5 ${ACTIVITY_COLORS.successIcon}`}
                          />
                          <h3 className="text-lg font-semibold">Verified Activities</h3>
                          <Badge variant="secondary">Verified</Badge>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {verifiedActivities.map((activity) => (
                            <ActivityCard
                              key={activity.id}
                              activity={activity}
                              onSelect={handleSelectActivity}
                              onCompare={handleCompareActivity}
                              sourceLabel="Verified"
                            />
                          ))}
                        </div>
                      </div>

                      {aiSuggestions.length > 0 && (
                        <>
                          <Separator />
                          <div>
                            <div className="flex items-center gap-2 mb-4">
                              <SparklesIcon
                                className={`h-5 w-5 ${ACTIVITY_COLORS.aiSuggestionIcon}`}
                              />
                              <h3 className="text-lg font-semibold">
                                More Ideas Powered by AI
                              </h3>
                              <Badge
                                variant="secondary"
                                className={ACTIVITY_COLORS.aiSuggestionBadge}
                              >
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
                  {verifiedActivities.length === 0 && (
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
