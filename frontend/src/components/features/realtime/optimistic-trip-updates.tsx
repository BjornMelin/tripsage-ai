/**
 * @fileoverview Optimistic trip updates component for realtime collaboration UI.
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
import { type UpdateTripData, useTrip, useUpdateTrip } from "@/hooks/use-trips";
import { queryKeys } from "@/lib/query-keys";
import type { UpdateTables } from "@/lib/supabase/database.types";
import { statusVariants } from "@/lib/variants/status";

type TripUpdate = UpdateTables<"trips">;
type TripUpdateKey = keyof TripUpdate;

/**
 * Consistent color palette aligned with statusVariants for update statuses
 */
const UPDATE_STATUS_COLORS = {
  error: "text-red-700",
  pending: "text-blue-700",
  success: "text-green-700",
} as const;

const COLLABORATOR_STATUS_COLORS = {
  active: "bg-green-700",
} as const;

import { useQueryClient } from "@tanstack/react-query";
import {
  AlertCircleIcon,
  CalendarIcon,
  CheckCircleIcon,
  ClockIcon,
  DollarSignIcon,
  Loader2Icon,
  MapPinIcon,
  UsersIcon,
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
  const {
    data: fetchedTrip,
    error: tripError,
    isConnected,
    isLoading,
    realtimeStatus,
  } = useTrip(tripId);

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

  const [trip, setTrip] = useState<UiTrip | null>(null);

  const fieldToUiKey: Partial<Record<TripUpdateKey, keyof UiTrip>> = {
    budget: "budget",
    destination: "destination",
    end_date: "endDate",
    name: "title",
    start_date: "startDate",
    travelers: "travelers",
  };

  useEffect(() => {
    if (!fetchedTrip) return;

    setTrip(fetchedTrip);

    setFormData((prev) => {
      const next = {
        budget: fetchedTrip.budget,
        destination: fetchedTrip.destination,
        name: fetchedTrip.title,
        travelers: fetchedTrip.travelers,
      } as Partial<TripUpdate>;

      const hasChanged =
        prev.budget !== next.budget ||
        prev.destination !== next.destination ||
        prev.name !== next.name ||
        prev.travelers !== next.travelers;

      return hasChanged ? next : prev;
    });
  }, [fetchedTrip]);

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
    if (!trip) {
      toast({
        description: "Trip data is still loading. Please wait and try again.",
        title: "Loading",
      });
      return;
    }

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
    setTrip((prev) => {
      if (!prev) return prev;
      const uiKey = fieldToUiKey[field];
      if (!uiKey) {
        if (process.env.NODE_ENV !== "production") {
          console.warn("Unmapped trip update field", {
            field,
            tripId,
            value,
          });
        }
        return prev;
      }
      return {
        ...prev,
        [uiKey]: value as UiTrip[keyof UiTrip],
        updatedAt: new Date().toISOString(),
      };
    });

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
      const currentTrip = queryClient.getQueryData<UiTrip | null>(
        queryKeys.trips.detail(tripId)
      );
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
    const uiKey = fieldToUiKey[field];
    const currentValue = uiKey && trip ? trip[uiKey] : undefined;
    if (value !== currentValue) {
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
        return (
          <Loader2Icon
            className={`h-4 w-4 animate-spin ${UPDATE_STATUS_COLORS.pending}`}
          />
        );
      case "success":
        return (
          <CheckCircleIcon className={`h-4 w-4 ${UPDATE_STATUS_COLORS.success}`} />
        );
      case "error":
        return <AlertCircleIcon className={`h-4 w-4 ${UPDATE_STATUS_COLORS.error}`} />;
    }
  };

  /**
   * Get the connection status.
   *
   * @returns The connection status.
   */
  const getConnectionStatus = () => {
    const realtimeErrors = realtimeStatus?.errors ?? [];
    if (!isConnected) {
      return (
        <Badge variant="destructive" className="mb-4">
          <AlertCircleIcon className="h-3 w-3 mr-1" />
          Offline - Changes will sync when reconnected
        </Badge>
      );
    }

    if (realtimeErrors.length > 0) {
      return (
        <Badge variant="secondary" className="mb-4">
          <AlertCircleIcon className="h-3 w-3 mr-1" />
          Connection issues detected
        </Badge>
      );
    }

    return (
      <Badge className={`mb-4 ${statusVariants({ status: "active" })}`}>
        <CheckCircleIcon className="h-3 w-3 mr-1" />
        Live updates enabled
      </Badge>
    );
  };

  /**
   * Render the optimistic trip updates component.
   *
   * @returns The optimistic trip updates component.
   */
  if (tripError) {
    return (
      <div className="space-y-4">
        {getConnectionStatus()}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2 text-destructive">
              <AlertCircleIcon className="h-5 w-5" />
              <span>Unable to load trip</span>
            </CardTitle>
            <CardDescription>
              {tripError.message ?? "Please try again later."}
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  if (isLoading && !trip) {
    return (
      <div className="space-y-4">
        {getConnectionStatus()}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Loader2Icon className="h-5 w-5 animate-spin" />
              <span>Loading trip...</span>
            </CardTitle>
            <CardDescription>
              Fetching the latest trip details and real-time connection status.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  if (!trip) {
    return (
      <div className="space-y-4">
        {getConnectionStatus()}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <AlertCircleIcon className="h-5 w-5" />
              <span>No trip found</span>
            </CardTitle>
            <CardDescription>
              The requested trip could not be found. Please verify the trip ID.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {getConnectionStatus()}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <MapPinIcon className="h-5 w-5" />
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
                <DollarSignIcon className="h-4 w-4" />
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
                <UsersIcon className="h-4 w-4" />
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
              <CalendarIcon className="h-4 w-4" />
              <span>Trip Dates</span>
            </Label>
            <div className="grid grid-cols-2 gap-4">
              <Input
                type="date"
                value={trip.startDate ?? ""}
                onChange={(e) => handleOptimisticUpdate("start_date", e.target.value)}
              />
              <Input
                type="date"
                value={trip.endDate ?? ""}
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
            <ClockIcon className="h-5 w-5" />
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
          <UsersIcon className="h-5 w-5" />
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
                <div
                  className={`w-2 h-2 rounded-full ${COLLABORATOR_STATUS_COLORS.active}`}
                />
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
