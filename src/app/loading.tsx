import { PageLoading } from "@/components/ui/loading";

/**
 * Root loading component for Next.js App Router
 * Shown when navigating between pages or during Suspense boundaries
 */
export default function Loading() {
  return <PageLoading message="Loading TripSage..." />;
}
