/**
 * @fileoverview Server wrapper for the trip creation flow (parses searchParams).
 */

import CreateTripClient from "./create-trip-client";

type PageSearchParams = Record<string, string | string[] | undefined>;

const DEFAULT_SUGGESTION_LIMIT = 6;

/**
 * Extracts the first string value from a search param entry.
 */
function getFirstParam(value: PageSearchParams[string]): string | null {
  if (Array.isArray(value)) return value[0] ?? null;
  return typeof value === "string" ? value : null;
}

/**
 * Parses a string as a positive integer, returning null if invalid.
 */
function parsePositiveInt(value: string | null): number | null {
  if (!value) return null;
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return null;
  return parsed;
}

/**
 * Parses a string as a positive float, returning null if invalid.
 */
function parsePositiveNumber(value: string | null): number | null {
  if (!value) return null;
  const parsed = Number.parseFloat(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return null;
  return parsed;
}

/**
 * Server wrapper for the trip creation flow (parses searchParams).
 * @param searchParams - The search params from the URL.
 * @returns The trip creation form UI with prefilled values from URL params.
 */
export default async function CreateTripPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const params = await searchParams;

  const suggestionId = getFirstParam(params.suggestion) ?? undefined;

  const suggestionLimit =
    parsePositiveInt(getFirstParam(params.limit)) ?? DEFAULT_SUGGESTION_LIMIT;

  const budgetMax = parsePositiveNumber(getFirstParam(params.budget_max)) ?? undefined;

  return (
    <CreateTripClient
      initialBudgetMax={budgetMax}
      initialSuggestionId={suggestionId}
      initialSuggestionLimit={suggestionLimit}
    />
  );
}
