import { PageLoading } from "@/components/ui/loading";
import { MAIN_CONTENT_ID } from "@/lib/a11y/landmarks";

/**
 * Root loading component for Next.js App Router
 * Shown when navigating between pages or during Suspense boundaries
 */
export default function Loading() {
  return (
    <main id={MAIN_CONTENT_ID} className="flex-1" tabIndex={-1}>
      <PageLoading message="Loading TripSage…" />
    </main>
  );
}
