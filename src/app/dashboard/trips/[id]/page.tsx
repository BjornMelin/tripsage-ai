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
import { useEffect, useMemo, useRef } from "react";
import { BudgetTracker } from "@/components/features/trips/budget-tracker";
import { ItineraryBuilder } from "@/components/features/trips/itinerary-builder";
import { TripTimeline } from "@/components/features/trips/trip-timeline";
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
import { useToast } from "@/components/ui/use-toast";
import { useTrip } from "@/hooks/use-trips";
import { ApiError } from "@/lib/api/error-types";
import { exportTripToIcs } from "@/lib/calendar/trip-export";
import { DateUtils } from "@/lib/dates/unified-date-utils";
import { ROUTES } from "@/lib/routes";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";
import { parseTripDate } from "@/lib/trips/parse-trip-date";
import { statusVariants } from "@/lib/variants/status";
import { useTripItineraryStore } from "@/stores/trip-itinerary-store";

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
  const { toast } = useToast();

  const tripIdParam = params.id as string;
  const tripIdNumber = Number.parseInt(tripIdParam, 10);
  // Pass null to useTrip when tripId is invalid to prevent requests to /api/trips/NaN
  const validTripId = Number.isNaN(tripIdNumber) ? null : tripIdNumber;
  const { data: trip, error, isLoading } = useTrip(validTripId);
  const destinations =
    useTripItineraryStore((state) => state.destinationsByTripId[tripIdParam]) ?? [];

  // Track handled errors to prevent duplicate toasts/redirects
  const handledErrorRef = useRef<string | null>(null);

  useEffect(() => {
    if (!error) {
      handledErrorRef.current = null;
      return;
    }

    // Generate error key for deduplication
    const errorKey =
      error instanceof ApiError
        ? `${error.status}-${error.message}`
        : error instanceof Error
          ? error.message
          : String(error);

    // Skip if already handled this exact error
    if (handledErrorRef.current === errorKey) return;
    handledErrorRef.current = errorKey;

    // Handle ApiError cases
    if (error instanceof ApiError) {
      const { status } = error;

      // 401/403: Authentication or authorization error
      if (status === 401) {
        toast({
          description: "Please sign in to view this trip.",
          title: "Authentication required",
          variant: "destructive",
        });
        router.push(ROUTES.login);
        return;
      }

      if (status === 403) {
        toast({
          description: "You don't have permission to view this trip.",
          title: "Access denied",
          variant: "destructive",
        });
        router.push(ROUTES.dashboard.trips);
        return;
      }

      // 404: Not found
      if (status === 404) {
        toast({
          description: "This trip no longer exists or you don't have access to it.",
          title: "Trip not found",
          variant: "destructive",
        });
        router.push(ROUTES.dashboard.trips);
        return;
      }

      // 5xx: Server error
      if (status >= 500 && status < 600) {
        toast({
          description: "The server encountered an error. Please try again later.",
          title: "Server error",
          variant: "destructive",
        });
        return;
      }

      // Other API errors
      toast({
        description: error.message || "An unexpected error occurred.",
        title: "Error loading trip",
        variant: "destructive",
      });
      return;
    }

    // Network error detection
    const isNetworkError =
      error instanceof Error &&
      (error.name === "TypeError" ||
        error.message.includes("fetch") ||
        error.message.includes("network") ||
        (typeof navigator !== "undefined" && !navigator.onLine));

    if (isNetworkError) {
      toast({
        description:
          "Unable to connect to the server. Check your internet connection and try again.",
        title: "Network error",
        variant: "destructive",
      });
      return;
    }

    // Generic error fallback
    toast({
      description:
        error instanceof Error ? error.message : "An unexpected error occurred.",
      title: "Error loading trip",
      variant: "destructive",
    });
  }, [error, router, toast]);

  const handleBackToTrips = () => {
    router.push(ROUTES.dashboard.trips);
  };

  // Merge trip with destinations first so helpers can reference it
  const mergedTrip = trip ? { ...trip, destinations } : null;

  // Parse start/end dates once to avoid duplicate telemetry/errors
  const parsedDates = useMemo(() => {
    if (!mergedTrip?.startDate || !mergedTrip?.endDate) {
      return { endDate: null, startDate: null };
    }
    return {
      endDate: parseTripDate(mergedTrip.endDate, { context: "TripDetailsPage" }),
      startDate: parseTripDate(mergedTrip.startDate, { context: "TripDetailsPage" }),
    };
  }, [mergedTrip?.startDate, mergedTrip?.endDate]);

  const getTripStatus = () => {
    const { startDate, endDate } = parsedDates;
    if (!startDate || !endDate) return "draft";

    const now = new Date();
    if (DateUtils.isBefore(now, startDate)) return "upcoming";
    if (DateUtils.isAfter(now, endDate)) return "completed";
    return "active";
  };

  const getTripDuration = () => {
    const { startDate, endDate } = parsedDates;
    if (!startDate || !endDate) return null;
    return DateUtils.difference(endDate, startDate, "days") + 1;
  };

  const formatParsedDate = (date: Date | null) => {
    if (!date) return "Not set";
    return DateUtils.format(date, "MMMM dd, yyyy");
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

  if (isLoading) {
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

  if (!mergedTrip) {
    return (
      <div className="container mx-auto py-8">
        <Card>
          <CardHeader>
            <CardTitle>Trip unavailable</CardTitle>
            <CardDescription>
              We couldn't load this trip. It may have been deleted or you may not have
              access.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={handleBackToTrips}>Back to trips</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const status = getTripStatus();
  const duration = getTripDuration();
  const accommodations = mergedTrip.destinations.filter((dest) => dest.accommodation);
  const transportations = mergedTrip.destinations.filter((dest) => dest.transportation);

  const handleExportToCalendar = async (): Promise<void> => {
    try {
      const icsContent = await exportTripToIcs(mergedTrip);
      const blob = new Blob([icsContent], { type: "text/calendar" });
      const url = URL.createObjectURL(blob);
      try {
        const a = document.createElement("a");
        a.href = url;
        a.download = `${sanitizeTripTitleForFilename(mergedTrip.title)}.ics`;
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
      const normalizedError = error instanceof Error ? error : new Error(String(error));
      recordClientErrorOnActiveSpan(normalizedError, {
        action: "exportTripToIcs",
        context: "TripDetailsPage",
        tripId: mergedTrip.id,
      });
      toast({
        description: "Failed to export trip to calendar. Please try again.",
        title: "Export failed",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="container mx-auto py-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Button variant="ghost" size="sm" onClick={handleBackToTrips} className="p-2">
          <ArrowLeftIcon className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold">{mergedTrip.title}</h1>
            <Badge className={getStatusClassName(status)}>
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </Badge>
            {mergedTrip.visibility === "public" && (
              <Badge variant="outline">Public</Badge>
            )}
          </div>
          {mergedTrip.description && (
            <p className="text-muted-foreground mt-1">{mergedTrip.description}</p>
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
          <Button variant="outline" size="sm" onClick={handleExportToCalendar}>
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
              {formatParsedDate(parsedDates.startDate)} -{" "}
              {formatParsedDate(parsedDates.endDate)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <MapPinIcon className="h-4 w-4" />
              Destinations
            </div>
            <div className="font-semibold">{mergedTrip.destinations.length}</div>
            <div className="text-xs text-muted-foreground mt-1">
              {mergedTrip.destinations.length > 0
                ? mergedTrip.destinations.map((d) => d.name).join(", ")
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
              {mergedTrip.budget
                ? new Intl.NumberFormat("en-US", {
                    currency: mergedTrip.currency || "USD",
                    style: "currency",
                  }).format(mergedTrip.budget)
                : "Not set"}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              {mergedTrip.currency || "USD"}
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
            <TripTimeline trip={mergedTrip} showActions={true} />

            {/* Budget Tracker */}
            <BudgetTracker tripId={mergedTrip.id} showActions={true} />
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
                    {mergedTrip.destinations.map((dest) => (
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
                        {mergedTrip.destinations.reduce(
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
                    {accommodations.map((dest) => (
                      <div key={dest.id}>
                        <div className="font-medium">{dest.name}</div>
                        <div className="text-muted-foreground">
                          {dest.accommodation?.name}
                        </div>
                      </div>
                    ))}
                    {accommodations.length === 0 && (
                      <div className="text-muted-foreground">
                        No accommodations booked
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold mb-2">Transportation</h4>
                  <div className="space-y-1 text-sm">
                    {transportations.map((dest) => (
                      <div key={dest.id}>
                        <div className="font-medium">To {dest.name}</div>
                        <div className="text-muted-foreground">
                          {dest.transportation?.type} - {dest.transportation?.details}
                        </div>
                      </div>
                    ))}
                    {transportations.length === 0 && (
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
          <ItineraryBuilder trip={mergedTrip} />
        </TabsContent>

        <TabsContent value="budget">
          <div className="space-y-6">
            <BudgetTracker
              tripId={mergedTrip.id}
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
                <BudgetPlanningPlaceholder />
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
              <TripSettingsPlaceholder />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function BudgetPlanningPlaceholder() {
  return (
    <div className="space-y-3">
      <p className="text-muted-foreground">
        Detailed budget planning is not yet available.
      </p>
      <div className="text-sm text-muted-foreground">
        Planned additions:
        <ul className="list-disc pl-5 pt-2 space-y-1">
          <li>Per-destination breakdowns</li>
          <li>Category budgets (lodging, flights, activities)</li>
          <li>Alerts when spending exceeds budget</li>
        </ul>
      </div>
    </div>
  );
}

function TripSettingsPlaceholder() {
  return (
    <div className="space-y-3">
      <p className="text-muted-foreground">Trip settings are not yet available.</p>
      <div className="text-sm text-muted-foreground">
        Planned additions:
        <ul className="list-disc pl-5 pt-2 space-y-1">
          <li>Sharing and collaboration controls</li>
          <li>Default currency and budget preferences</li>
          <li>Notification settings</li>
        </ul>
      </div>
    </div>
  );
}
