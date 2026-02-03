/**
 * @fileoverview Server page for activity search (RSC shell).
 */

import { submitActivitySearch } from "./actions";
import ActivitiesSearchClient from "./activities-search-client";

type SearchParams = Record<string, string | string[] | undefined>;

function getFirstParam(value: SearchParams[string]): string | undefined {
  if (Array.isArray(value)) return value[0];
  return typeof value === "string" ? value : undefined;
}

/**
 * Server page for activity search (RSC shell).
 * @param searchParams - The search params from the URL.
 * @returns The activity search client.
 */
export default async function ActivitiesSearchPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;

  return (
    <ActivitiesSearchClient
      initialUrlParams={{
        category: getFirstParam(params.category),
        destination: getFirstParam(params.destination),
      }}
      onSubmitServer={submitActivitySearch}
    />
  );
}
