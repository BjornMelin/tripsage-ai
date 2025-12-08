/**
 * @fileoverview Trip details dashboard page that renders itinerary, budget,
 * and export actions for a specific trip id sourced from the store.
 */

"use client";

import {
  ArrowLeftIcon,
  CalendarIcon,
  DollarSignIcon,
  DownloadIcon,
  EditIcon,
  MapPinIcon,
  SettingsIcon,
  Share2Icon,
  UsersIcon,
} from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BudgetTracker,
  ItineraryBuilder,
  TripTimeline,
} from "@/components/features/trips";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { exportTripToIcs } from "@/lib/calendar/trip-export";
import { DateUtils } from "@/lib/dates/unified-date-utils";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";
import { statusVariants } from "@/lib/variants/status";
import { useTripStore } from "@/stores/trip-store";

const MAX_FILENAME_LENGTH = 80;

const sanitizeTripTitleForFilename = (title?: string) => {
  const base = (title ?? "").trim();
  const replaced =
    base.length === 0
      ? "trip"
      : base
          .replace(/[\\/]/g, "-")
          .replace(/[^a-zA-Z0-9 _.-]/g, "-")
          .replace(/\s+/g, " ")
          .trim();
  const normalized = replaced.replace(/\s+/g, "-").replace(/-+/g, "-");
  const limited = normalized
    .slice(0, MAX_FILENAME_LENGTH)
    .replace(/^[-.]+|[-.]+$/g, "");
  return limited || "trip";
};

/**
 * Renders the trip dashboard for the requested trip id sourced from the URL.
 *
 * @returns Structured trip overview including itinerary views and calendar
 * export controls.
 */
export default function TripDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const { trips, currentTrip, setCurrentTrip } = useTripStore();
  const [isLoading, setIsLoading] = useState(true);

  const tripId = params.id as string;

  useEffect(() => {
    const trip = trips.find((t) => t.id === tripId);
    if (trip) {
      setCurrentTrip(trip);
      setIsLoading(false);
    } else {
      // Trip not found, redirect to trips page
      router.push("/dashboard/trips");
    }
  }, [tripId, trips, setCurrentTrip, router]);

  const handleBackToTrips = () => {
    router.push("/dashboard/trips");
  };

  const getTripStatus = () => {
    if (!currentTrip?.startDate || !currentTrip?.endDate) return "draft";
    const now = new Date();
    const startDate = DateUtils.parse(currentTrip.startDate);
    const endDate = DateUtils.parse(currentTrip.endDate);

    if (DateUtils.isBefore(now, startDate)) return "upcoming";
    if (DateUtils.isAfter(now, endDate)) return "completed";
    return "active";
  };

  const getTripDuration = () => {
    if (!currentTrip?.startDate || !currentTrip?.endDate) return null;
    const startDate = DateUtils.parse(currentTrip.startDate);
    const endDate = DateUtils.parse(currentTrip.endDate);
    return DateUtils.difference(endDate, startDate, "days") + 1;
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "Not set";
    return DateUtils.format(DateUtils.parse(dateString), "MMMM dd, yyyy");
  };

  /**
   * Maps trip status to statusVariants with fallback for neutral states.
   * Active/upcoming use statusVariants; draft/completed use neutral gray.
   */
  type TripStatus = ReturnType<typeof getTripStatus>;

  const assertNever = (value: never): never => {
    throw new Error(`Unhandled trip status: ${value satisfies TripStatus}`);
  };

  const getStatusClassName = (status: TripStatus) => {
    switch (status) {
      case "active":
        return statusVariants({ status: "active" });
      case "upcoming":
        return statusVariants({ status: "info" });
      case "completed":
      case "draft":
        return "bg-gray-100 text-gray-500 ring-1 ring-inset ring-gray-500/20";
      default:
        return assertNever(status);
    }
  };

  if (isLoading || !currentTrip) {
    return (
      <div className="container mx-auto py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4" />
          <div className="h-4 bg-gray-200 rounded w-1/2" />
          <div className="h-64 bg-gray-200 rounded" />
        </div>
      </div>
    );
  }

  const status = getTripStatus();
  const duration = getTripDuration();

  return (
    <div className="container mx-auto py-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" size="sm" onClick={handleBackToTrips} className="p-2">
          <ArrowLeftIcon className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold">{currentTrip.title}</h1>
            <Badge className={getStatusClassName(status)}>
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </Badge>
            {currentTrip.visibility === "public" && (
              <Badge variant="outline">Public</Badge>
            )}
          </div>
          {currentTrip.description && (
            <p className="text-muted-foreground mt-1">{currentTrip.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <EditIcon className="h-4 w-4 mr-2" />
            Edit
          </Button>
          <Button variant="outline" size="sm">
            <Share2Icon className="h-4 w-4 mr-2" />
            Share
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              const trip = currentTrip;
              if (!trip) return;
              try {
                const icsContent = await exportTripToIcs(trip);
                const blob = new Blob([icsContent], { type: "text/calendar" });
                const url = URL.createObjectURL(blob);
                try {
                  const a = document.createElement("a");
                  a.href = url;
                  const sanitizedFilename = `${sanitizeTripTitleForFilename(
                    trip.title
                  )}.ics`;
                  a.download = sanitizedFilename;
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                } finally {
                  URL.revokeObjectURL(url);
                }
              } catch (error) {
                if (process.env.NODE_ENV === "development") {
                  console.error("Failed to export trip:", error);
                }
                const normalizedError =
                  error instanceof Error ? error : new Error(String(error));
                recordClientErrorOnActiveSpan(normalizedError, {
                  action: "exportTripToIcs",
                  context: "TripDetailsPage",
                  tripId: trip.id,
                  tripTitle: trip.title,
                });
                alert("Failed to export trip to calendar");
              }
            }}
          >
            <DownloadIcon className="h-4 w-4 mr-2" />
            Export to Calendar
          </Button>
        </div>
      </div>

      {/* Trip Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <CalendarIcon className="h-4 w-4" />
              Duration
            </div>
            <div className="font-semibold">
              {duration ? `${duration} days` : "Not set"}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              {formatDate(currentTrip.startDate)} - {formatDate(currentTrip.endDate)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <MapPinIcon className="h-4 w-4" />
              Destinations
            </div>
            <div className="font-semibold">{currentTrip.destinations.length}</div>
            <div className="text-xs text-muted-foreground mt-1">
              {currentTrip.destinations.length > 0
                ? currentTrip.destinations.map((d) => d.name).join(", ")
                : "None planned"}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <DollarSignIcon className="h-4 w-4" />
              Budget
            </div>
            <div className="font-semibold">
              {currentTrip.budget
                ? new Intl.NumberFormat("en-US", {
                    currency: currentTrip.currency || "USD",
                    style: "currency",
                  }).format(currentTrip.budget)
                : "Not set"}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              {currentTrip.currency || "USD"}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <UsersIcon className="h-4 w-4" />
              Travelers
            </div>
            <div className="font-semibold">1</div>
            <div className="text-xs text-muted-foreground mt-1">Just you</div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="itinerary">Itinerary</TabsTrigger>
          <TabsTrigger value="budget">Budget</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Timeline */}
            <TripTimeline trip={currentTrip} showActions={true} />

            {/* Budget Tracker */}
            <BudgetTracker tripId={currentTrip.id} showActions={true} />
          </div>

          {/* Quick Stats */}
          <Card>
            <CardHeader>
              <CardTitle>Trip Summary</CardTitle>
              <CardDescription>Key information about your trip</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <h4 className="font-semibold mb-2">Estimated Costs</h4>
                  <div className="space-y-1 text-sm">
                    {currentTrip.destinations.map((dest, _index) => (
                      <div key={dest.id} className="flex justify-between">
                        <span>{dest.name}</span>
                        <span>${dest.estimatedCost || 0}</span>
                      </div>
                    ))}
                    <Separator />
                    <div className="flex justify-between font-semibold">
                      <span>Total</span>
                      <span>
                        $
                        {currentTrip.destinations.reduce(
                          (sum, dest) => sum + (dest.estimatedCost || 0),
                          0
                        )}
                      </span>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Accommodations</h4>
                  <div className="space-y-1 text-sm">
                    {currentTrip.destinations
                      .filter((dest) => dest.accommodation)
                      .map((dest) => (
                        <div key={dest.id}>
                          <div className="font-medium">{dest.name}</div>
                          <div className="text-muted-foreground">
                            {dest.accommodation?.name}
                          </div>
                        </div>
                      ))}
                    {currentTrip.destinations.filter((dest) => dest.accommodation)
                      .length === 0 && (
                      <div className="text-muted-foreground">
                        No accommodations booked
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Transportation</h4>
                  <div className="space-y-1 text-sm">
                    {currentTrip.destinations
                      .filter((dest) => dest.transportation)
                      .map((dest) => (
                        <div key={dest.id}>
                          <div className="font-medium">To {dest.name}</div>
                          <div className="text-muted-foreground">
                            {dest.transportation?.type} - {dest.transportation?.details}
                          </div>
                        </div>
                      ))}
                    {currentTrip.destinations.filter((dest) => dest.transportation)
                      .length === 0 && (
                      <div className="text-muted-foreground">
                        No transportation planned
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="itinerary">
          <ItineraryBuilder trip={currentTrip} />
        </TabsContent>

        <TabsContent value="budget">
          <div className="space-y-6">
            <BudgetTracker
              tripId={currentTrip.id}
              showActions={true}
              className="max-w-2xl"
            />

            {/* Additional budget features would go here */}
            <Card>
              <CardHeader>
                <CardTitle>Budget Planning</CardTitle>
                <CardDescription>
                  Detailed budget breakdown and expense tracking
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">
                  Additional budget features coming soon...
                </p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="settings">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <SettingsIcon className="h-5 w-5" />
                Trip Settings
              </CardTitle>
              <CardDescription>
                Manage your trip preferences and sharing options
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">
                Trip settings panel coming soon...
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
