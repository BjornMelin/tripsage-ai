/*
 * @fileoverview Optimistic trip updates component.
 * Shows real-time collaboration with instant UI feedback.
 */

"use client";

import type { UiTrip } from "@schemas/trips";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/use-toast";
import { type UpdateTripData, useTripRealtime, useUpdateTrip } from "@/hooks";
import type { UpdateTables } from "@/lib/supabase/database.types";

type TripUpdate = UpdateTables<"trips">;
type TripUpdateKey = keyof TripUpdate;

import { useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  Calendar,
  CheckCircle,
  Clock,
  DollarSign,
  Loader2,
  MapPin,
  Users,
} from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

/**
 * Interface for the optimistic trip updates props.
 */
interface OptimisticTripUpdatesProps {
  /** The ID of the trip to update. */
  tripId: number;
}

/**
 * Component demonstrating optimistic updates for trip editing
 * Shows real-time collaboration with instant UI feedback
 */
export function OptimisticTripUpdates({ tripId }: OptimisticTripUpdatesProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const updateTrip = useUpdateTrip();
  const { isConnected, errors } = useTripRealtime(tripId.toString());

  const [formData, setFormData] = useState<Partial<TripUpdate>>({});
  // Snapshots to support rollback when mutation fails and cache is missing
  const prevTripRef = useRef<UiTrip | null>(null);
  const prevFormRef = useRef<Partial<TripUpdate> | null>(null);
  const [optimisticUpdates, setOptimisticUpdates] = useState<
    Record<
      string,
      {
        value: TripUpdate[keyof TripUpdate];
        status: "pending" | "success" | "error";
        timestamp: Date;
      }
    >
  >({});
  const tripNameInputId = useId();
  const destinationInputId = useId();
  const budgetInputId = useId();
  const travelersInputId = useId();

  // TODO: Replace mock trip data with real trip data from hook or API.
  //
  // Requirements:
  // - Use `useTrip(tripId)` hook if available, or fetch trip data from `/api/trips/[id]`
  // - Load trip data on component mount using tripId prop
  // - Handle loading and error states for trip data fetching
  // - Update trip state when real-time updates are received via Supabase Realtime
  // - Ensure trip data is properly typed and validated
  // - Add proper cleanup for subscriptions/listeners
  //
  // Mock trip data - in real implementation, this would come from useTrip(tripId)
  const [trip, setTrip] = useState<UiTrip>({
    budget: 5000,
    createdAt: new Date().toISOString(),
    currency: "USD",
    destination: "Paris, France",
    destinations: [],
    endDate: "2024-07-15",
    id: String(tripId),
    preferences: {},
    startDate: "2024-07-01",
    status: "planning",
    tags: ["Visit Eiffel Tower", "Try local cuisine"],
    title: "Summer Europe Trip",
    travelers: 2,
    tripType: "leisure",
    updatedAt: new Date().toISOString(),
    userId: "user-123",
    visibility: "private",
  });

  /**
   * Initialize form data with current trip values.
   */
  useEffect(() => {
    // Initialize form data with current trip values
    setFormData({
      budget: trip.budget,
      destination: trip.destination,
      name: trip.title,
      travelers: trip.travelers,
    });
  }, [trip]);

  /**
   * Handle optimistic update.
   *
   * @param field - The field to update.
   * @param value - The value to update the field to.
   * @returns A promise that resolves to the optimistic update.
   */
  const handleOptimisticUpdate = async (
    field: TripUpdateKey,
    value: TripUpdate[TripUpdateKey]
  ) => {
    const updateKey = String(field);

    // Snapshot current state for rollback
    prevTripRef.current = trip;
    prevFormRef.current = formData;

    // Apply optimistic update to local state
    setOptimisticUpdates((prev) => ({
      ...prev,
      [updateKey]: {
        status: "pending",
        timestamp: new Date(),
        value,
      },
    }));

    // Update local trip state optimistically
    setTrip((prev) => ({
      ...prev,
      [field]: value,
      updated_at: new Date().toISOString(),
    }));

    try {
      // Perform actual update
      const updates = { [field]: value } as UpdateTripData;

      await updateTrip.mutateAsync({
        data: updates,
        tripId,
      });

      // Mark as successful and clear snapshots
      setOptimisticUpdates((prev) => ({
        ...prev,
        [updateKey]: {
          ...prev[updateKey],
          status: "success",
        },
      }));
      prevTripRef.current = null;
      prevFormRef.current = null;

      // Clear the optimistic update after a delay
      setTimeout(() => {
        setOptimisticUpdates((prev) => {
          const { [updateKey]: _removed, ...rest } = prev;
          return rest;
        });
      }, 2000);

      /**
       * Show a success toast.
       */
      toast({
        description: `Trip ${field} has been updated successfully.`,
        title: "Updated",
      });
    } catch (_error) {
      // Revert optimistic update on error using cache or snapshots
      const currentTrip = queryClient.getQueryData(["trip", tripId]) as
        | UiTrip
        | undefined;
      if (currentTrip) {
        setTrip(currentTrip);
        setFormData({
          budget: currentTrip.budget,
          destination: currentTrip.destination,
          name: currentTrip.title,
          travelers: currentTrip.travelers,
        });
      } else {
        if (prevTripRef.current) setTrip(prevTripRef.current);
        if (prevFormRef.current) setFormData(prevFormRef.current);
      }

      /**
       * Set the optimistic update to error.
       */
      setOptimisticUpdates((prev) => ({
        ...prev,
        [updateKey]: {
          ...prev[updateKey],
          status: "error",
        },
      }));

      /**
       * Show a failure toast.
       */
      toast({
        description: `Failed to update trip ${field}. Please try again.`,
        title: "Update Failed",
        variant: "destructive",
      });
    }
  };

  /**
   * Handle input change.
   *
   * @param field - The field to update.
   * @param value - The value to update the field to.
   * @returns A promise that resolves to the input change.
   */
  const handleInputChange = (
    field: TripUpdateKey,
    value: TripUpdate[TripUpdateKey]
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  /**
   * Handle input blur.
   *
   * @param field - The field to update.
   * @returns A promise that resolves to the input blur.
   */
  const handleInputBlur = (field: keyof TripUpdate) => {
    const value = formData[field];
    if (value !== trip[field as keyof UiTrip]) {
      handleOptimisticUpdate(field, value);
    }
  };

  /**
   * Get the field status.
   *
   * @param field - The field to get the status of.
   * @returns The field status.
   */
  const getFieldStatus = (field: string) => {
    const update = optimisticUpdates[field];
    if (!update) return null;

    switch (update.status) {
      case "pending":
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case "success":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "error":
        return <AlertCircle className="h-4 w-4 text-red-500" />;
    }
  };

  /**
   * Get the connection status.
   *
   * @returns The connection status.
   */
  const getConnectionStatus = () => {
    if (!isConnected) {
      return (
        <Badge variant="destructive" className="mb-4">
          <AlertCircle className="h-3 w-3 mr-1" />
          Offline - Changes will sync when reconnected
        </Badge>
      );
    }

    if (errors.length > 0) {
      return (
        <Badge variant="secondary" className="mb-4">
          <AlertCircle className="h-3 w-3 mr-1" />
          Connection issues detected
        </Badge>
      );
    }

    return (
      <Badge variant="default" className="mb-4 bg-green-500">
        <CheckCircle className="h-3 w-3 mr-1" />
        Live updates enabled
      </Badge>
    );
  };

  /**
   * Render the optimistic trip updates component.
   *
   * @returns The optimistic trip updates component.
   */
  return (
    <div className="space-y-6">
      {getConnectionStatus()}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <MapPin className="h-5 w-5" />
            <span>Trip Details</span>
          </CardTitle>
          <CardDescription>
            Edit your trip details. Changes are saved automatically and shared with
            collaborators in real-time.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor={tripNameInputId} className="flex items-center space-x-2">
                <span>Trip Name</span>
                {getFieldStatus("name")}
              </Label>
              <Input
                id={tripNameInputId}
                value={formData.name || ""}
                onChange={(e) => handleInputChange("name", e.target.value)}
                onBlur={() => handleInputBlur("name")}
                placeholder="Enter trip name..."
              />
            </div>

            <div className="space-y-2">
              <Label
                htmlFor={destinationInputId}
                className="flex items-center space-x-2"
              >
                <span>Destination</span>
                {getFieldStatus("destination")}
              </Label>
              <Input
                id={destinationInputId}
                value={formData.destination || ""}
                onChange={(e) => handleInputChange("destination", e.target.value)}
                onBlur={() => handleInputBlur("destination")}
                placeholder="Enter destination..."
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor={budgetInputId} className="flex items-center space-x-2">
                <DollarSign className="h-4 w-4" />
                <span>Budget</span>
                {getFieldStatus("budget")}
              </Label>
              <Input
                id={budgetInputId}
                type="number"
                value={formData.budget || 0}
                onChange={(e) =>
                  handleInputChange("budget", Number.parseInt(e.target.value, 10))
                }
                onBlur={() => handleInputBlur("budget")}
                placeholder="Enter budget..."
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor={travelersInputId} className="flex items-center space-x-2">
                <Users className="h-4 w-4" />
                <span>Travelers</span>
                {getFieldStatus("travelers")}
              </Label>
              <Input
                id={travelersInputId}
                type="number"
                min="1"
                value={formData.travelers || 1}
                onChange={(e) =>
                  handleInputChange("travelers", Number.parseInt(e.target.value, 10))
                }
                onBlur={() => handleInputBlur("travelers")}
                placeholder="Number of travelers..."
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label className="flex items-center space-x-2">
              <Calendar className="h-4 w-4" />
              <span>Trip Dates</span>
            </Label>
            <div className="grid grid-cols-2 gap-4">
              <Input
                type="date"
                value={trip.startDate}
                onChange={(e) => handleOptimisticUpdate("start_date", e.target.value)}
              />
              <Input
                type="date"
                value={trip.endDate}
                onChange={(e) => handleOptimisticUpdate("end_date", e.target.value)}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity Feed */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Clock className="h-5 w-5" />
            <span>Recent Updates</span>
          </CardTitle>
        </CardHeader>

        <CardContent>
          <div className="space-y-3">
            {Object.entries(optimisticUpdates).map(([field, update]) => (
              <div
                key={field}
                className="flex items-center justify-between p-3 rounded-lg bg-muted/50"
              >
                <div className="flex items-center space-x-3">
                  {getFieldStatus(field)}
                  <div>
                    <div className="text-sm font-medium">
                      Updated {field.replace("_", " ")}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {update.timestamp.toLocaleTimeString()}
                    </div>
                  </div>
                </div>
                <Badge
                  variant={
                    update.status === "success"
                      ? "default"
                      : update.status === "error"
                        ? "destructive"
                        : "secondary"
                  }
                >
                  {update.status}
                </Badge>
              </div>
            ))}

            {Object.keys(optimisticUpdates).length === 0 && (
              <div className="text-center text-muted-foreground py-6">
                No recent updates. Make changes to see real-time sync in action!
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Collaboration indicator showing who else is currently editing
 *
 * @param tripId - The ID of the trip to show the collaborators for.
 * @returns The collaboration indicator component.
 */
export function CollaborationIndicator({ tripId: _tripId }: { tripId: number }) {
  const [activeCollaborators] = useState([
    { editing: "budget", id: "user-456", name: "Alice Johnson" },
    { editing: null, id: "user-789", name: "Bob Smith" },
  ]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Users className="h-5 w-5" />
          <span>Active Collaborators</span>
        </CardTitle>
      </CardHeader>

      <CardContent>
        <div className="space-y-2">
          {activeCollaborators.map((collaborator) => (
            <div
              key={collaborator.id}
              className="flex items-center justify-between p-2 rounded-lg bg-muted/50"
            >
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <span className="text-sm font-medium">{collaborator.name}</span>
              </div>

              {collaborator.editing && (
                <Badge variant="secondary" className="text-xs">
                  Editing {collaborator.editing}
                </Badge>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
