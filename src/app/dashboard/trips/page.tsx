/**
 * @fileoverview Trips management page with filtering, sorting, and search.
 */

"use client";

import {
  FilterIcon,
  GridIcon,
  ListIcon,
  Loader2Icon,
  PlusIcon,
  SearchIcon,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import { ConnectionStatusIndicator } from "@/features/realtime/components/connection-status-monitor";
import { TripCard } from "@/features/trips/components/trip-card";
import { useCurrentUserId } from "@/hooks/use-current-user-id";
import { type Trip, useCreateTrip, useDeleteTrip, useTrips } from "@/hooks/use-trips";
import { getErrorMessage } from "@/lib/api/error-types";
import { nowIso } from "@/lib/security/random";
import { parseTripDate } from "@/lib/trips/parse-trip-date";

/**
 * Trip status count colors aligned with statusVariants.
 * Matches trip status semantic colors.
 */
const TRIP_STATUS_COLORS = {
  active: "text-green-700", // aligned with active status
  completed: "text-gray-600", // neutral completed state
  upcoming: "text-blue-700", // aligned with info status
} as const;

const CONNECTED_MESSAGE = "Connected — live updates enabled";
const ERROR_MESSAGE =
  "Disconnected — live updates paused due to sync errors. Please check your network.";
const DISCONNECTED_MESSAGE =
  "Disconnected — live updates paused, please check your network.";

type ConnectionState = "connected" | "error" | "disconnected";

const TRIP_SKELETON_KEYS = [
  "trip-skeleton-0",
  "trip-skeleton-1",
  "trip-skeleton-2",
  "trip-skeleton-3",
  "trip-skeleton-4",
  "trip-skeleton-5",
] as const;

const getConnectionStatusMessage = (state: ConnectionState): string => {
  if (state === "connected") return CONNECTED_MESSAGE;
  if (state === "error") return ERROR_MESSAGE;
  return DISCONNECTED_MESSAGE;
};

const getConnectionState = (
  realtimeErrorCount: number,
  isConnected: boolean
): ConnectionState => {
  if (realtimeErrorCount > 0) return "error";
  if (isConnected) return "connected";
  return "disconnected";
};

const isInvalidTripDateRange = (
  startDate: Date | null,
  endDate: Date | null
): boolean => !!startDate && !!endDate && endDate.getTime() < startDate.getTime();

type TripStatus = "draft" | "upcoming" | "active" | "completed";
type SortOption = "name" | "date" | "budget" | "destinations";
type FilterOption = "all" | "draft" | "upcoming" | "active" | "completed";

const getTripStatus = (trip: Trip, nowTs: number): TripStatus => {
  const startDate = parseTripDate(trip.startDate, { context: "TripsPage" });
  const endDate = parseTripDate(trip.endDate, { context: "TripsPage" });
  const isInvalidRange = isInvalidTripDateRange(startDate, endDate);

  if (isInvalidRange || !startDate || !endDate) {
    return "draft";
  }
  if (startDate.getTime() > nowTs) {
    return "upcoming";
  }
  if (endDate.getTime() < nowTs) {
    return "completed";
  }
  return "active";
};

/**
 * Renders the trips management dashboard with filtering, sorting, and view
 * toggles backed by realtime queries.
 *
 * @returns Trips management layout with grid/list modes.
 */
export default function TripsPage() {
  const createTripMutation = useCreateTrip();
  const deleteTripMutation = useDeleteTrip();
  const { data: trips, isLoading, error, isConnected, realtimeStatus } = useTrips();
  const currentUserId = useCurrentUserId();
  const { toast } = useToast();
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("date");
  const [filterBy, setFilterBy] = useState<FilterOption>("all");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [pendingDeleteTripId, setPendingDeleteTripId] = useState<string | null>(null);
  const lastErrorMessageRef = useRef<string | null>(null);

  const tripsArray = trips ?? [];
  const realtimeErrorCount = Array.isArray(realtimeStatus?.errors)
    ? realtimeStatus.errors.length
    : 0;
  const connectionState = getConnectionState(realtimeErrorCount, isConnected);
  const connectionStatusMessage = getConnectionStatusMessage(connectionState);

  const filteredAndSortedTrips = useMemo(() => {
    if (tripsArray.length === 0) return [];

    let filtered = tripsArray;
    const nowTs = Date.now();
    const searchQueryLower = searchQuery.toLowerCase();

    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter(
        (trip: Trip) =>
          (trip.title || "").toLowerCase().includes(searchQueryLower) ||
          trip.description?.toLowerCase().includes(searchQueryLower) ||
          (trip.destinations || []).some((dest) =>
            dest.name.toLowerCase().includes(searchQueryLower)
          )
      );
    }

    // Apply status filter
    if (filterBy !== "all") {
      filtered = filtered.filter((trip: Trip) => {
        const status = getTripStatus(trip, nowTs);
        return status === filterBy;
      });
    }

    // Apply sorting
    return [...filtered].sort((a: Trip, b: Trip) => {
      switch (sortBy) {
        case "name":
          return (a.title || "").localeCompare(b.title || "");
        case "date": {
          const parsedB =
            parseTripDate(b.createdAt, { context: "TripsPage" }) ?? new Date(0);
          const parsedA =
            parseTripDate(a.createdAt, { context: "TripsPage" }) ?? new Date(0);
          return parsedB.getTime() - parsedA.getTime();
        }
        case "budget":
          return (b.budget || 0) - (a.budget || 0);
        case "destinations":
          return (b.destinations || []).length - (a.destinations || []).length;
        default:
          return 0;
      }
    });
  }, [tripsArray, searchQuery, sortBy, filterBy]);

  const handleCreateTrip = async () => {
    try {
      await createTripMutation.mutateAsync({
        currency: "USD",
        destination: "Destination TBD",
        endDate: nowIso(),
        startDate: nowIso(),
        status: "planning",
        title: "New Trip",
        travelers: 1,
        tripType: "leisure",
        visibility: "private",
      });
    } catch (createError) {
      toast({
        description: getErrorMessage(createError),
        title: "Unable to create trip",
        variant: "destructive",
      });
    }
  };

  const handleDeleteTrip = (tripId: string) => {
    setPendingDeleteTripId(tripId);
    setIsDeleteDialogOpen(true);
  };

  const confirmDeleteTrip = async () => {
    if (!pendingDeleteTripId) return;
    try {
      await deleteTripMutation.mutateAsync(pendingDeleteTripId);
      toast({
        description: "Your trip has been deleted.",
        title: "Trip deleted",
      });
    } catch (deleteError) {
      toast({
        description: getErrorMessage(deleteError),
        title: "Unable to delete trip",
        variant: "destructive",
      });
    } finally {
      setIsDeleteDialogOpen(false);
      setPendingDeleteTripId(null);
    }
  };

  const statusCounts = useMemo(() => {
    const tripsForCounts = trips ?? [];
    if (tripsForCounts.length === 0) {
      return { active: 0, completed: 0, draft: 0, upcoming: 0 };
    }

    const nowTs = Date.now();
    return tripsForCounts.reduce(
      (counts: Record<string, number>, trip: Trip) => {
        const status = getTripStatus(trip, nowTs);
        counts[status]++;
        return counts;
      },
      { active: 0, completed: 0, draft: 0, upcoming: 0 }
    );
  }, [trips]);

  // Handle error state
  useEffect(() => {
    if (error) {
      const message = getErrorMessage(error) || "Unable to load trips.";
      if (message !== lastErrorMessageRef.current) {
        lastErrorMessageRef.current = message;
        toast({
          description: message,
          title: "Unable to load trips",
          variant: "destructive",
        });
      }
      if (process.env.NODE_ENV === "development") {
        console.error("Trips error:", error);
      }
    } else {
      lastErrorMessageRef.current = null;
    }
  }, [error, toast]);

  // Show loading state
  if (isLoading && tripsArray.length === 0) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">My Trips</h1>
            <p className="text-muted-foreground">Loading your trips...</p>
          </div>
          <div className="flex items-center space-x-4">
            <ConnectionStatusIndicator />
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {TRIP_SKELETON_KEYS.map((key) => (
            <Card key={key} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-4 bg-muted rounded mb-4" />
                <div className="h-3 bg-muted rounded mb-2" />
                <div className="h-3 bg-muted rounded mb-4" />
                <div className="h-8 bg-muted rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (tripsArray.length === 0 && !isLoading) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">My Trips</h1>
            <p className="text-muted-foreground">
              Plan and organize your travel adventures
            </p>
          </div>
        </div>

        <Card className="max-w-md mx-auto">
          <CardHeader className="text-center">
            <CardTitle>No trips yet</CardTitle>
            <CardDescription>
              Start planning your next adventure by creating your first trip
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center">
            <Button
              onClick={handleCreateTrip}
              size="lg"
              disabled={createTripMutation.isPending}
            >
              <PlusIcon className="h-5 w-5 mr-2" />
              Create Your First Trip
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">My Trips</h1>
          <p className="text-muted-foreground">
            {tripsArray.length} trip{tripsArray.length !== 1 ? "s" : ""} in your
            collection
          </p>
        </div>
        <div className="flex items-center space-x-4" data-testid="trips-connection">
          <div data-connection-state={connectionState}>
            <ConnectionStatusIndicator />
            <output
              aria-live={connectionState === "error" ? "assertive" : "polite"}
              className="sr-only"
            >
              {connectionStatusMessage}
            </output>
          </div>
          <Button onClick={handleCreateTrip} disabled={createTripMutation.isPending}>
            <PlusIcon className="h-4 w-4 mr-2" />
            Create Trip
          </Button>
        </div>
      </div>

      {/* Status Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{statusCounts.draft}</div>
            <div className="text-sm text-muted-foreground">Draft</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className={`text-2xl font-bold ${TRIP_STATUS_COLORS.upcoming}`}>
              {statusCounts.upcoming}
            </div>
            <div className="text-sm text-muted-foreground">Upcoming</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className={`text-2xl font-bold ${TRIP_STATUS_COLORS.active}`}>
              {statusCounts.active}
            </div>
            <div className="text-sm text-muted-foreground">Active</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className={`text-2xl font-bold ${TRIP_STATUS_COLORS.completed}`}>
              {statusCounts.completed}
            </div>
            <div className="text-sm text-muted-foreground">Completed</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search trips, destinations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>

        <Select
          value={filterBy}
          onValueChange={(value) => setFilterBy(value as FilterOption)}
        >
          <SelectTrigger aria-label="Filter trips" className="w-full md:w-40">
            <FilterIcon className="h-4 w-4 mr-2" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Trips</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="upcoming">Upcoming</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={sortBy}
          onValueChange={(value) => setSortBy(value as SortOption)}
        >
          <SelectTrigger aria-label="Sort trips" className="w-full md:w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="date">Latest</SelectItem>
            <SelectItem value="name">Name</SelectItem>
            <SelectItem value="budget">Budget</SelectItem>
            <SelectItem value="destinations">Destinations</SelectItem>
          </SelectContent>
        </Select>

        <div className="flex border rounded-md">
          <Button
            aria-label="Grid view"
            aria-pressed={viewMode === "grid"}
            data-state={viewMode === "grid" ? "on" : "off"}
            variant={viewMode === "grid" ? "default" : "ghost"}
            size="sm"
            onClick={() => setViewMode("grid")}
            className="rounded-r-none"
          >
            <GridIcon className="h-4 w-4" />
          </Button>
          <Button
            aria-label="List view"
            aria-pressed={viewMode === "list"}
            data-state={viewMode === "list" ? "on" : "off"}
            variant={viewMode === "list" ? "default" : "ghost"}
            size="sm"
            onClick={() => setViewMode("list")}
            className="rounded-l-none"
          >
            <ListIcon className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Trips Grid/List */}
      {filteredAndSortedTrips.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <SearchIcon className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No trips found</h3>
            <p className="text-muted-foreground mb-4">
              Try adjusting your search or filter criteria
            </p>
            <Button
              variant="outline"
              onClick={() => {
                setSearchQuery("");
                setFilterBy("all");
              }}
            >
              Clear Filters
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div
          data-testid="trips-view"
          data-view-mode={viewMode}
          className={
            viewMode === "grid"
              ? "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
              : "space-y-4"
          }
        >
          {filteredAndSortedTrips.map((trip: Trip) => (
            <TripCard
              key={trip.id}
              trip={trip}
              onDelete={
                currentUserId && trip.userId && trip.userId === currentUserId
                  ? handleDeleteTrip
                  : undefined
              }
              className={viewMode === "list" ? "flex-row" : ""}
            />
          ))}
        </div>
      )}

      {/* Load More (if needed for pagination) */}
      {filteredAndSortedTrips.length > 0 && (
        <div className="text-center mt-8">
          <p className="text-sm text-muted-foreground">
            Showing {filteredAndSortedTrips.length} of {tripsArray.length} trips
          </p>
        </div>
      )}

      <AlertDialog
        open={isDeleteDialogOpen}
        onOpenChange={(open) => {
          setIsDeleteDialogOpen(open);
          if (!open) {
            setPendingDeleteTripId(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete trip?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete your trip and
              remove its data from your account.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteTripMutation.isPending}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={async (event) => {
                event.preventDefault();
                await confirmDeleteTrip();
              }}
              disabled={deleteTripMutation.isPending}
              aria-busy={deleteTripMutation.isPending}
            >
              {deleteTripMutation.isPending ? (
                <>
                  <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                "Delete"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
