"use client";

import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import {
  Loader2,
  Save,
  Users,
  Calendar,
  MapPin,
  DollarSign,
  CheckCircle,
  AlertCircle,
  Clock,
} from "lucide-react";
import { useSupabaseTrips, useTripRealtime } from "@/hooks";
import type { Trip, TripUpdate } from "@/lib/supabase/types";

interface OptimisticTripUpdatesProps {
  tripId: number;
}

/**
 * Component demonstrating optimistic updates for trip editing
 * Shows real-time collaboration with instant UI feedback
 */
export function OptimisticTripUpdates({ tripId }: OptimisticTripUpdatesProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { updateTrip } = useSupabaseTrips();
  const { isConnected, errors } = useTripRealtime(tripId);

  const [formData, setFormData] = useState<Partial<TripUpdate>>({});
  const [optimisticUpdates, setOptimisticUpdates] = useState<
    Record<
      string,
      {
        value: any;
        status: "pending" | "success" | "error";
        timestamp: Date;
      }
    >
  >({});

  // Mock trip data - in real implementation, this would come from useTrip(tripId)
  const [trip, setTrip] = useState<Trip>({
    id: tripId,
    user_id: "user-123",
    name: "Summer Europe Trip",
    destination: "Paris, France",
    start_date: "2024-07-01",
    end_date: "2024-07-15",
    budget: 5000,
    travelers: 2,
    status: "planning",
    trip_type: "leisure",
    flexibility: {},
    notes: ["Visit Eiffel Tower", "Try local cuisine"],
    search_metadata: {},
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  });

  useEffect(() => {
    // Initialize form data with current trip values
    setFormData({
      name: trip.name,
      destination: trip.destination,
      budget: trip.budget,
      travelers: trip.travelers,
    });
  }, [trip]);

  const handleOptimisticUpdate = async (field: keyof TripUpdate, value: any) => {
    const updateId = `${field}-${Date.now()}`;

    // Apply optimistic update to local state
    setOptimisticUpdates((prev) => ({
      ...prev,
      [field]: {
        value,
        status: "pending",
        timestamp: new Date(),
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
      await updateTrip.mutateAsync({
        id: tripId,
        updates: { [field]: value },
      });

      // Mark as successful
      setOptimisticUpdates((prev) => ({
        ...prev,
        [field]: {
          ...prev[field],
          status: "success",
        },
      }));

      // Clear the optimistic update after a delay
      setTimeout(() => {
        setOptimisticUpdates((prev) => {
          const { [field]: removed, ...rest } = prev;
          return rest;
        });
      }, 2000);

      toast({
        title: "Updated",
        description: `Trip ${field} has been updated successfully.`,
      });
    } catch (error) {
      // Revert optimistic update on error
      const currentTrip = queryClient.getQueryData(["trip", tripId]) as
        | Trip
        | undefined;
      if (currentTrip) {
        setTrip(currentTrip);
      }

      setOptimisticUpdates((prev) => ({
        ...prev,
        [field]: {
          ...prev[field],
          status: "error",
        },
      }));

      toast({
        title: "Update Failed",
        description: `Failed to update trip ${field}. Please try again.`,
        variant: "destructive",
      });
    }
  };

  const handleInputChange = (field: keyof TripUpdate, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleInputBlur = (field: keyof TripUpdate) => {
    const value = formData[field];
    if (value !== trip[field as keyof Trip]) {
      handleOptimisticUpdate(field, value);
    }
  };

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
              <Label htmlFor="trip-name" className="flex items-center space-x-2">
                <span>Trip Name</span>
                {getFieldStatus("name")}
              </Label>
              <Input
                id="trip-name"
                value={formData.name || ""}
                onChange={(e) => handleInputChange("name", e.target.value)}
                onBlur={() => handleInputBlur("name")}
                placeholder="Enter trip name..."
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="destination" className="flex items-center space-x-2">
                <span>Destination</span>
                {getFieldStatus("destination")}
              </Label>
              <Input
                id="destination"
                value={formData.destination || ""}
                onChange={(e) => handleInputChange("destination", e.target.value)}
                onBlur={() => handleInputBlur("destination")}
                placeholder="Enter destination..."
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="budget" className="flex items-center space-x-2">
                <DollarSign className="h-4 w-4" />
                <span>Budget</span>
                {getFieldStatus("budget")}
              </Label>
              <Input
                id="budget"
                type="number"
                value={formData.budget || 0}
                onChange={(e) =>
                  handleInputChange("budget", Number.parseInt(e.target.value))
                }
                onBlur={() => handleInputBlur("budget")}
                placeholder="Enter budget..."
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="travelers" className="flex items-center space-x-2">
                <Users className="h-4 w-4" />
                <span>Travelers</span>
                {getFieldStatus("travelers")}
              </Label>
              <Input
                id="travelers"
                type="number"
                min="1"
                value={formData.travelers || 1}
                onChange={(e) =>
                  handleInputChange("travelers", Number.parseInt(e.target.value))
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
                value={trip.start_date}
                onChange={(e) => handleOptimisticUpdate("start_date", e.target.value)}
              />
              <Input
                type="date"
                value={trip.end_date}
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
 */
export function CollaborationIndicator({ tripId }: { tripId: number }) {
  const [activeCollaborators] = useState([
    { id: "user-456", name: "Alice Johnson", editing: "budget" },
    { id: "user-789", name: "Bob Smith", editing: null },
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
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
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
