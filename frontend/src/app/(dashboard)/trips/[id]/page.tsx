"use client";

import { differenceInDays, format } from "date-fns";
import {
  ArrowLeft,
  Calendar,
  DollarSign,
  Download,
  Edit,
  MapPin,
  Settings,
  Share2,
  Users,
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
import { useTripStore } from "@/stores/trip-store";

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
    const startDate = new Date(currentTrip.startDate);
    const endDate = new Date(currentTrip.endDate);

    if (now < startDate) return "upcoming";
    if (now > endDate) return "completed";
    return "active";
  };

  const getTripDuration = () => {
    if (!currentTrip?.startDate || !currentTrip?.endDate) return null;
    const startDate = new Date(currentTrip.startDate);
    const endDate = new Date(currentTrip.endDate);
    return differenceInDays(endDate, startDate) + 1;
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "Not set";
    return format(new Date(dateString), "MMMM dd, yyyy");
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "draft":
        return "bg-gray-100 text-gray-700";
      case "upcoming":
        return "bg-blue-100 text-blue-700";
      case "active":
        return "bg-green-100 text-green-700";
      case "completed":
        return "bg-gray-100 text-gray-500";
      default:
        return "bg-gray-100 text-gray-700";
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
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold">{currentTrip.name}</h1>
            <Badge className={getStatusColor(status)}>
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </Badge>
            {currentTrip.isPublic && <Badge variant="outline">Public</Badge>}
          </div>
          {currentTrip.description && (
            <p className="text-muted-foreground mt-1">{currentTrip.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm">
            <Edit className="h-4 w-4 mr-2" />
            Edit
          </Button>
          <Button variant="outline" size="sm">
            <Share2 className="h-4 w-4 mr-2" />
            Share
          </Button>
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Trip Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
              <Calendar className="h-4 w-4" />
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
              <MapPin className="h-4 w-4" />
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
              <DollarSign className="h-4 w-4" />
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
              <Users className="h-4 w-4" />
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
                <Settings className="h-5 w-5" />
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
