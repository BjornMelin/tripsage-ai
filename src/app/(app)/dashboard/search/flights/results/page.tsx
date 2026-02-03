/**
 * @fileoverview Flight search results server wrapper (parses searchParams).
 */

import FlightResultsClient from "./flight-results-client";

type SearchParams = Record<string, string | string[] | undefined>;

function getFirstParam(value: SearchParams[string]): string | null {
  if (Array.isArray(value)) return value[0] ?? null;
  return typeof value === "string" ? value : null;
}

/**
 * Server page for flight search results (RSC shell).
 * @param searchParams - The search params from the URL.
 * @returns The flight search results client.
 */
export default async function FlightResultsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const searchId = getFirstParam(params.searchId);

  return <FlightResultsClient searchId={searchId} />;
}
