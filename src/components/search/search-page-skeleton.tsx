/**
 * @fileoverview Shared loading skeleton for search result pages.
 */

"use client";

import { Skeleton } from "@/components/ui/skeleton";

/**
 * Skeleton UI for search pages.
 *
 * @returns {JSX.Element} Placeholder content while search pages load.
 */
export function SearchPageSkeleton() {
  return (
    <div className="space-y-6 p-6">
      <Skeleton className="h-10 w-64" />
      <Skeleton className="h-48 w-full" />
      <Skeleton className="h-48 w-full" />
    </div>
  );
}
