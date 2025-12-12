/**
 * @fileoverview Server page for flight search (RSC shell).
 */

import { submitFlightSearch } from "./actions";
import FlightsSearchClient from "./flights-search-client";

export default function FlightSearchPage() {
  return <FlightsSearchClient onSubmitServer={submitFlightSearch} />;
}
