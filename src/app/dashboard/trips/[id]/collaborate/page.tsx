/**
 * @fileoverview Trip collaboration page.
 */

"use client";

import { ClockIcon, EditIcon, Loader2Icon, Share2Icon, UsersIcon } from "lucide-react";
import { useParams } from "next/navigation";
import { ConnectionStatusMonitor } from "@/components/features/realtime/connection-status-monitor";
import {
  CollaborationIndicator,
  OptimisticTripUpdates,
} from "@/components/features/realtime/optimistic-trip-updates";
import { TripActivityFeed } from "@/components/features/trips/trip-activity-feed";
import { TripCollaboratorsPanel } from "@/components/features/trips/trip-collaborators-panel";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { useCurrentUserId } from "@/hooks/use-current-user-id";
import { useTripActivityFeed } from "@/hooks/use-trip-activity-feed";
import {
  getTripEditPermission,
  useTripCollaborators,
} from "@/hooks/use-trip-collaborators";
import { useTrip } from "@/hooks/use-trips";

/**
 * Trip collaboration page component.
 *
 * Displays interface for managing collaborators, real-time editing, activity monitoring,
 * and sharing settings.
 *
 * @returns The trip collaboration page JSX element
 */
export default function TripCollaborationPage() {
  const params = useParams();
  const tripIdParam = params.id as string;
  const tripIdNumber = Number.parseInt(tripIdParam, 10);
  // Pass null to useTrip when tripId is invalid to prevent requests to /api/trips/NaN
  const validTripId = Number.isNaN(tripIdNumber) ? null : tripIdNumber;

  const currentUserId = useCurrentUserId();
  const activityFeed = useTripActivityFeed(validTripId);
  const collaboratorsQuery = useTripCollaborators(validTripId);

  const { data: trip, error: tripError, isConnected, isLoading } = useTrip(validTripId);

  const ownerIdFromTrip =
    typeof trip?.userId === "string" && trip.userId.length > 0 ? trip.userId : null;

  const ownerId = collaboratorsQuery.data?.ownerId ?? ownerIdFromTrip ?? "";
  const collaborators = collaboratorsQuery.data?.collaborators ?? [];
  const isOwner =
    collaboratorsQuery.data?.isOwner ??
    (ownerId.length > 0 && currentUserId ? ownerId === currentUserId : false);

  const permissions = getTripEditPermission({
    collaborators,
    currentUserId,
    ownerId,
  });

  if (isLoading && !trip) {
    return (
      <div className="container mx-auto py-8">
        <Card>
          <CardContent className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
            <Loader2Icon className="h-5 w-5 animate-spin" />
            Loading trip collaboration...
          </CardContent>
        </Card>
      </div>
    );
  }

  if (tripError) {
    return (
      <div className="container mx-auto py-8">
        <Card>
          <CardContent className="text-center py-12">
            <h2 className="text-xl font-semibold mb-2">Unable to load trip</h2>
            <p className="text-muted-foreground">{tripError.message}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!trip) {
    return (
      <div className="container mx-auto py-8">
        <Card>
          <CardContent className="text-center py-12">
            <h2 className="text-xl font-semibold mb-2">Trip not found</h2>
            <p className="text-muted-foreground">
              The trip you're looking for doesn't exist or you don't have access to it.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-bold">
              Collaborate on {trip.title ?? "this trip"}
            </h1>
            {permissions.role !== "unknown" && (
              <Badge variant="outline" className="border-dashed">
                {permissions.role === "owner"
                  ? "Owner"
                  : permissions.role === "admin"
                    ? "Admin"
                    : permissions.role === "editor"
                      ? "Editor"
                      : "Viewer"}
              </Badge>
            )}
          </div>
          <p className="text-muted-foreground">
            Manage collaborators and real-time editing
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <ConnectionStatusMonitor />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <EditIcon className="h-5 w-5" />
                <span>Live Trip Editing</span>
              </CardTitle>
              <CardDescription>
                Edit trip details with real-time collaboration
              </CardDescription>
            </CardHeader>
            <CardContent>
              {Number.isNaN(tripIdNumber) ? null : (
                <OptimisticTripUpdates
                  tripId={tripIdNumber}
                  canEdit={permissions.canEdit}
                  onActivity={(input) => {
                    activityFeed.emit(input).catch(() => undefined);
                  }}
                />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <UsersIcon className="h-5 w-5" />
                <span>Collaborators</span>
                <Badge variant="secondary">
                  {collaboratorsQuery.isLoading
                    ? "Loading..."
                    : `${collaborators.length} collaborator${collaborators.length === 1 ? "" : "s"}`}
                </Badge>
              </CardTitle>
              <CardDescription>
                Invite others and manage access to this trip
              </CardDescription>
            </CardHeader>

            <CardContent>
              {Number.isNaN(tripIdNumber) ? null : collaboratorsQuery.isLoading ? (
                <div className="rounded-lg border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
                  Loading collaborators...
                </div>
              ) : collaboratorsQuery.error ? (
                <div className="rounded-lg border bg-muted/30 px-4 py-3 text-sm text-muted-foreground">
                  Unable to load collaborators. Please refresh and try again.
                </div>
              ) : (
                <TripCollaboratorsPanel
                  tripId={tripIdNumber}
                  ownerId={ownerId}
                  currentUserId={currentUserId}
                  collaborators={collaborators}
                  isOwner={isOwner}
                  onActivity={(input) => {
                    activityFeed.emit(input).catch(() => undefined);
                  }}
                />
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {Number.isNaN(tripIdNumber) ? null : (
            <CollaborationIndicator tripId={tripIdNumber} />
          )}

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <ClockIcon className="h-5 w-5" />
                <span>Recent Activity</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <TripActivityFeed
                events={activityFeed.events}
                connectionStatus={activityFeed.connectionStatus}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Share2Icon className="h-5 w-5" />
                <span>Sharing Settings</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Visibility</Label>
                <Badge variant="secondary">{trip.visibility ?? "private"}</Badge>
                <p className="text-xs text-muted-foreground">
                  {trip.visibility === "public"
                    ? "Anyone can view this trip"
                    : trip.visibility === "shared"
                      ? "Only invited collaborators can view"
                      : "Only you can view this trip"}
                </p>
              </div>

              <div className="space-y-2">
                <Label>Real-time Updates</Label>
                <Badge variant={isConnected ? "default" : "destructive"}>
                  {isConnected ? "Connected" : "Disconnected"}
                </Badge>
                <p className="text-xs text-muted-foreground">
                  Changes are synced automatically when connected
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
