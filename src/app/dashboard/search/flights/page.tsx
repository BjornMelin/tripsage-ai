/**
 * @fileoverview Server page for flight search (RSC shell).
 */

import dynamic from "next/dynamic";
import { SearchPageSkeleton } from "@/components/search/search-page-skeleton";
import { submitFlightSearch } from "./actions";

const FLIGHTS_SEARCH_CLIENT = dynamic(() => import("./flights-search-client"), {
  loading: () => <SearchPageSkeleton />,
});

/**
 * Flight search page that renders the client component and handles server submission.
 *
 * @returns {JSX.Element} The flight search page.
 */
export default function FlightSearchPage() {
  return <FLIGHTS_SEARCH_CLIENT onSubmitServer={submitFlightSearch} />;
}
