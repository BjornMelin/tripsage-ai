/**
 * @fileoverview Shared loading skeleton for search result pages.
 */

import { Skeleton } from "@/components/ui/skeleton";

/**
 * Skeleton UI for search pages.
 *
 * @returns {JSX.Element} Placeholder content while search pages load.
 */
export function SearchPageSkeleton() {
  return (
    // biome-ignore lint/a11y/useSemanticElements: Loading skeleton uses role="status" live region; no semantic element fits this container.
    <div role="status" className="space-y-6 p-6">
      <span className="sr-only">Loading search results</span>
      <Skeleton aria-hidden="true" className="h-10 w-64" />
      <Skeleton aria-hidden="true" className="h-48 w-full" />
      <Skeleton aria-hidden="true" className="h-48 w-full" />
    </div>
  );
}
