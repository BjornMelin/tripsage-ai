import { LoadingContainer } from "@/components/ui/loading";
import { CardSkeleton } from "@/components/ui/loading";

/**
 * Dashboard loading component
 * Shows skeleton for dashboard layout while content loads
 */
export default function DashboardLoading() {
  return (
    <LoadingContainer
      isLoading={true}
      loadingMessage="Loading your dashboard..."
      minHeight="400px"
      className="p-6"
    >
      {/* Dashboard grid skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <CardSkeleton hasImage={false} titleLines={1} bodyLines={2} />
        <CardSkeleton hasImage={false} titleLines={1} bodyLines={2} />
        <CardSkeleton hasImage={false} titleLines={1} bodyLines={2} />
        <CardSkeleton hasImage={true} titleLines={2} bodyLines={1} />
        <CardSkeleton hasImage={true} titleLines={2} bodyLines={1} />
        <CardSkeleton hasImage={true} titleLines={2} bodyLines={1} />
      </div>
    </LoadingContainer>
  );
}
