/**
 * @fileoverview Server page for destination search (RSC shell).
 */

import dynamic from "next/dynamic";
import { SearchPageSkeleton } from "@/components/search/search-page-skeleton";
import { submitDestinationSearch } from "./actions";

const DESTINATIONS_SEARCH_CLIENT = dynamic(
  () => import("./destinations-search-client"),
  {
    loading: () => <SearchPageSkeleton />,
  }
);

/**
 * Destination search page that renders the client component and handles server submission.
 *
 * @returns {JSX.Element} The destination search page.
 */
export default function DestinationsSearchPage() {
  return <DESTINATIONS_SEARCH_CLIENT onSubmitServer={submitDestinationSearch} />;
}
