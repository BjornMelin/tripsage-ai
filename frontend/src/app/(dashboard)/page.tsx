import { Suspense } from "react";
import {
  QuickActions,
  RecentTrips,
  TripSuggestions,
  UpcomingFlights,
} from "@/components/features/dashboard";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

function DashboardSkeleton() {
  return (
    <div className="space-y-8">
      <div className="space-y-2">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-96" />
      </div>

      {/* Quick Actions Skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
            {[
              "action-1",
              "action-2",
              "action-3",
              "action-4",
              "action-5",
              "action-6",
            ].map((key) => (
              <Skeleton key={key} className="h-20 w-full rounded-lg" />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Main Content Grid Skeleton */}
      <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {["item-1", "item-2", "item-3"].map((key) => (
                <div key={key} className="flex items-center space-x-4">
                  <Skeleton className="h-12 w-12 rounded" />
                  <div className="space-y-2 flex-1">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-3 w-2/3" />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {["content-1", "content-2", "content-3"].map((key) => (
                <div key={key} className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-3 w-3/4" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <div className="lg:col-span-2 xl:col-span-1">
          <Card>
            <CardHeader>
              <Skeleton className="h-6 w-32" />
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {["grid-1", "grid-2", "grid-3"].map((key) => (
                  <div key={key} className="space-y-2">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-3 w-2/3" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          Welcome to TripSage AI. Plan your next adventure with our intelligent travel
          assistant.
        </p>
      </div>

      <Suspense fallback={<DashboardSkeleton />}>
        <DashboardContent />
      </Suspense>
    </div>
  );
}

async function DashboardContent() {
  // Simulate API delay for demonstration of streaming
  await new Promise((resolve) => setTimeout(resolve, 100));

  return (
    <>
      {/* Top Row - Quick Actions */}
      <QuickActions compact />

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
        {/* Recent Trips */}
        <Suspense
          fallback={
            <Card>
              <CardContent className="p-6">
                <Skeleton className="h-32 w-full" />
              </CardContent>
            </Card>
          }
        >
          <RecentTrips limit={5} />
        </Suspense>

        {/* Upcoming Flights */}
        <Suspense
          fallback={
            <Card>
              <CardContent className="p-6">
                <Skeleton className="h-32 w-full" />
              </CardContent>
            </Card>
          }
        >
          <UpcomingFlights limit={3} />
        </Suspense>

        {/* Trip Suggestions - Takes up remaining space */}
        <div className="lg:col-span-2 xl:col-span-1">
          <Suspense
            fallback={
              <Card>
                <CardContent className="p-6">
                  <Skeleton className="h-32 w-full" />
                </CardContent>
              </Card>
            }
          >
            <TripSuggestions limit={3} />
          </Suspense>
        </div>
      </div>
    </>
  );
}
