/**
 * @fileoverview Server page for flight search (RSC shell).
 */

import { submitFlightSearch } from "./actions";
import FlightsSearchClient from "./flights-search-client";

/** Flight search page that renders the client component and handles server submission. */
export default function FlightSearchPage() {
  return <FlightsSearchClient onSubmitServer={submitFlightSearch} />;
}
