/**
 * @fileoverview Loading UI for hotel search page route.
 */

import { SearchPageSkeleton } from "@/components/search/search-page-skeleton";

/**
 * Route-level loading component shown during page transitions.
 */
export default function Loading() {
  return <SearchPageSkeleton />;
}
