import {
  QuickActions,
  RecentTrips,
  TripSuggestions,
  UpcomingFlights,
} from "@/components/features/dashboard";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          Welcome to TripSage AI. Plan your next adventure.
        </p>
      </div>

      {/* Top Row - Quick Actions */}
      <QuickActions compact />

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
        {/* Recent Trips */}
        <RecentTrips limit={5} />

        {/* Upcoming Flights */}
        <UpcomingFlights limit={3} />

        {/* Trip Suggestions - Takes up remaining space */}
        <div className="lg:col-span-2 xl:col-span-1">
          <TripSuggestions limit={3} />
        </div>
      </div>
    </div>
  );
}
