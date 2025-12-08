/**
 * @fileoverview Server page for flight search (RSC shell).
 */

import { submitFlightSearch } from "./actions";
import FlightsSearchClient from "./flights-search-client";

export const dynamic = "force-dynamic";

export default function FlightSearchPage() {
  return <FlightsSearchClient onSubmitServer={submitFlightSearch} />;
}
