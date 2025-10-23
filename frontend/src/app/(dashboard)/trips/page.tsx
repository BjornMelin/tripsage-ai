"use client";

import { Filter, Grid, List, Plus, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { ConnectionStatusIndicator } from "@/components/features/realtime/connection-status-monitor";
import { TripCard } from "@/components/features/trips";
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
import { useTripsWithRealtime } from "@/hooks/use-trips-with-realtime";
import { type Trip, useTripStore } from "@/stores/trip-store";

type SortOption = "name" | "date" | "budget" | "destinations";
type FilterOption = "all" | "draft" | "upcoming" | "active" | "completed";

export default function TripsPage() {
  const { createTrip, deleteTrip } = useTripStore();
  const {
    trips,
    isLoading,
    error,
    realtimeStatus: _realtimeStatus,
  } = useTripsWithRealtime();
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("date");
  const [filterBy, setFilterBy] = useState<FilterOption>("all");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  const filteredAndSortedTrips = useMemo(() => {
    if (!trips) return [];

    let filtered = trips;

    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter(
        (trip: Trip) =>
          (trip.title || trip.name || "")
            .toLowerCase()
            .includes(searchQuery.toLowerCase()) ||
          trip.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (trip.destinations || []).some((dest) =>
            dest.name.toLowerCase().includes(searchQuery.toLowerCase())
          )
      );
    }

    // Apply status filter
    if (filterBy !== "all") {
      filtered = filtered.filter((trip: Trip) => {
        const now = new Date();
        const startDate =
          trip.startDate || trip.start_date
            ? new Date(trip.startDate || trip.start_date || "")
            : null;
        const endDate =
          trip.endDate || trip.end_date
            ? new Date(trip.endDate || trip.end_date || "")
            : null;

        switch (filterBy) {
          case "draft":
            return !startDate || !endDate;
          case "upcoming":
            return startDate && startDate > now;
          case "active":
            return startDate && endDate && startDate <= now && endDate >= now;
          case "completed":
            return endDate && endDate < now;
          default:
            return true;
        }
      });
    }

    // Apply sorting
    return filtered.sort((a: Trip, b: Trip) => {
      switch (sortBy) {
        case "name":
          return (a.title || a.name || "").localeCompare(b.title || b.name || "");
        case "date":
          return (
            new Date(b.createdAt || b.created_at || "").getTime() -
            new Date(a.createdAt || a.created_at || "").getTime()
          );
        case "budget":
          return (b.budget || 0) - (a.budget || 0);
        case "destinations":
          return (b.destinations || []).length - (a.destinations || []).length;
        default:
          return 0;
      }
    });
  }, [trips, searchQuery, sortBy, filterBy]);

  const handleCreateTrip = async () => {
    await createTrip({
      title: "New Trip",
      description: "",
      destinations: [],
      isPublic: false,
    });
  };

  const handleDeleteTrip = async (tripId: string) => {
    if (confirm("Are you sure you want to delete this trip?")) {
      await deleteTrip(tripId);
    }
  };

  const getStatusCounts = () => {
    if (!trips) return { draft: 0, upcoming: 0, active: 0, completed: 0 };

    const now = new Date();
    return trips.reduce(
      (counts: Record<string, number>, trip: Trip) => {
        const startDate =
          trip.startDate || trip.start_date
            ? new Date(trip.startDate || trip.start_date || "")
            : null;
        const endDate =
          trip.endDate || trip.end_date
            ? new Date(trip.endDate || trip.end_date || "")
            : null;

        if (!startDate || !endDate) {
          counts.draft++;
        } else if (startDate > now) {
          counts.upcoming++;
        } else if (startDate <= now && endDate >= now) {
          counts.active++;
        } else {
          counts.completed++;
        }

        return counts;
      },
      { draft: 0, upcoming: 0, active: 0, completed: 0 }
    );
  };

  const statusCounts = getStatusCounts();

  // Handle error state
  useEffect(() => {
    if (error) {
      console.error("Trips error:", error);
    }
  }, [error]);

  // Show loading state
  if (isLoading && (!trips || trips.length === 0)) {
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
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={`trip-skeleton-${i}-${Date.now()}`} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-4 bg-gray-200 rounded mb-4" />
                <div className="h-3 bg-gray-200 rounded mb-2" />
                <div className="h-3 bg-gray-200 rounded mb-4" />
                <div className="h-8 bg-gray-200 rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if ((!trips || trips.length === 0) && !isLoading) {
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
            <Button onClick={handleCreateTrip} size="lg">
              <Plus className="h-5 w-5 mr-2" />
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
            {trips?.length || 0} trip{(trips?.length || 0) !== 1 ? "s" : ""} in your
            collection
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <ConnectionStatusIndicator />
          <Button onClick={handleCreateTrip}>
            <Plus className="h-4 w-4 mr-2" />
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
            <div className="text-2xl font-bold text-blue-600">
              {statusCounts.upcoming}
            </div>
            <div className="text-sm text-muted-foreground">Upcoming</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-green-600">
              {statusCounts.active}
            </div>
            <div className="text-sm text-muted-foreground">Active</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-gray-600">
              {statusCounts.completed}
            </div>
            <div className="text-sm text-muted-foreground">Completed</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
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
          <SelectTrigger className="w-full md:w-40">
            <Filter className="h-4 w-4 mr-2" />
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
          <SelectTrigger className="w-full md:w-40">
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
            variant={viewMode === "grid" ? "default" : "ghost"}
            size="sm"
            onClick={() => setViewMode("grid")}
            className="rounded-r-none"
          >
            <Grid className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === "list" ? "default" : "ghost"}
            size="sm"
            onClick={() => setViewMode("list")}
            className="rounded-l-none"
          >
            <List className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Trips Grid/List */}
      {filteredAndSortedTrips.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <Search className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
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
              onDelete={handleDeleteTrip}
              className={viewMode === "list" ? "flex-row" : ""}
            />
          ))}
        </div>
      )}

      {/* Load More (if needed for pagination) */}
      {filteredAndSortedTrips.length > 0 && (
        <div className="text-center mt-8">
          <p className="text-sm text-muted-foreground">
            Showing {filteredAndSortedTrips.length} of {trips?.length || 0} trips
          </p>
        </div>
      )}
    </div>
  );
}
