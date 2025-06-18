import { Skeleton } from "@/components/ui/skeleton";

export default function TripsLoading() {
  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Skeleton className="h-10 w-32 rounded-md" />
      </div>

      {/* Filters bar */}
      <div className="flex items-center space-x-4 py-4 border-b">
        <Skeleton className="h-9 w-48 rounded-md" />
        <Skeleton className="h-9 w-32 rounded-md" />
        <Skeleton className="h-9 w-28 rounded-md" />
        <div className="ml-auto">
          <Skeleton className="h-9 w-24 rounded-md" />
        </div>
      </div>

      {/* Trips grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {[
          "trip-1",
          "trip-2",
          "trip-3",
          "trip-4",
          "trip-5",
          "trip-6",
          "trip-7",
          "trip-8",
          "trip-9",
        ].map((key) => (
          <div key={key} className="border rounded-lg overflow-hidden">
            {/* Trip image */}
            <Skeleton className="h-48 w-full" />

            {/* Trip content */}
            <div className="p-4 space-y-3">
              <div className="space-y-2">
                <Skeleton className="h-5 w-3/4" />
                <div className="flex items-center space-x-2">
                  <Skeleton variant="rounded" className="h-4 w-4" />
                  <Skeleton className="h-4 w-24" />
                </div>
              </div>

              {/* Trip dates */}
              <div className="flex items-center space-x-4">
                <div className="space-y-1">
                  <Skeleton className="h-3 w-12" />
                  <Skeleton className="h-4 w-16" />
                </div>
                <Skeleton className="h-4 w-6" />
                <div className="space-y-1">
                  <Skeleton className="h-3 w-12" />
                  <Skeleton className="h-4 w-16" />
                </div>
              </div>

              {/* Trip details */}
              <div className="flex items-center justify-between pt-2">
                <div className="space-y-1">
                  <Skeleton className="h-3 w-16" />
                  <Skeleton className="h-4 w-20" />
                </div>
                <Skeleton className="h-6 w-16 rounded-full" />
              </div>

              {/* Action buttons */}
              <div className="flex items-center space-x-2 pt-3">
                <Skeleton className="h-8 w-20 rounded-md" />
                <Skeleton className="h-8 w-16 rounded-md" />
                <div className="ml-auto">
                  <Skeleton variant="rounded" className="h-8 w-8" />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-center pt-8">
        <div className="flex items-center space-x-2">
          <Skeleton className="h-9 w-9 rounded-md" />
          <Skeleton className="h-9 w-9 rounded-md" />
          <Skeleton className="h-9 w-9 rounded-md" />
          <Skeleton className="h-9 w-12 rounded-md" />
          <Skeleton className="h-9 w-9 rounded-md" />
          <Skeleton className="h-9 w-9 rounded-md" />
          <Skeleton className="h-9 w-9 rounded-md" />
        </div>
      </div>
    </div>
  );
}
