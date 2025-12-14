/**
 * @fileoverview Server page for unified search experience (RSC shell).
 */

import dynamic from "next/dynamic";
import { SearchPageSkeleton } from "@/components/search/search-page-skeleton";
import { searchHotelsAction } from "./actions";

const UNIFIED_SEARCH_CLIENT = dynamic(() => import("./unified-search-client"), {
  loading: () => <SearchPageSkeleton />,
});

/** Server page for unified search experience (RSC shell). */
export default function UnifiedSearchPage() {
  return <UNIFIED_SEARCH_CLIENT onSearchHotels={searchHotelsAction} />;
}
