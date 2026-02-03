/**
 * @fileoverview Server page for flight search (RSC shell).
 */

import { submitFlightSearch } from "./actions";
import FlightsSearchClient from "./flights-search-client";

/** URL search params resolved for the flight search page. */
type SearchParams = Record<string, string | string[] | undefined>;

function getFirstParam(value: SearchParams[string]): string | undefined {
  if (Array.isArray(value)) return value[0];
  return typeof value === "string" ? value : undefined;
}

/**
 * Server page for flight search (RSC shell).
 * @param searchParams - The search params from the URL.
 * @returns The flight search client.
 */
export default async function FlightSearchPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;

  return (
    <FlightsSearchClient
      initialUrlParams={{
        class: getFirstParam(params.class),
        departDate: getFirstParam(params.departDate),
        destination: getFirstParam(params.destination),
        origin: getFirstParam(params.origin),
        passengers: getFirstParam(params.passengers),
        returnDate: getFirstParam(params.returnDate),
      }}
      onSubmitServer={submitFlightSearch}
    />
  );
}
