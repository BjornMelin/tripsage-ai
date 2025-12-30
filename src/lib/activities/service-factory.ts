/**
 * @fileoverview Shared factories for wiring up ActivitiesService and related adapters.
 */

import "server-only";

import type { ActivitiesCache, WebSearchFn } from "@domain/activities/service";
import { ActivitiesService } from "@domain/activities/service";
import type { ToolExecutionOptions } from "ai";
import { hashInputForCache } from "@/lib/cache/hash";
import {
  buildActivitySearchQuery,
  getActivityDetailsFromPlaces,
  searchActivitiesWithPlaces,
} from "@/lib/google/places-activities";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";

type WebSearchToolInput = {
  categories: string[] | null;
  fresh: boolean;
  freshness: string | null;
  limit: number;
  location: string | null;
  query: string;
  region: string | null;
  scrapeOptions: {
    formats: Array<"markdown" | "html" | "links" | "screenshot"> | null;
    parsers: string[] | null;
    proxy: "basic" | "stealth" | null;
  } | null;
  sources: Array<"web" | "news" | "images"> | null;
  tbs: string | null;
  timeoutMs: number | null;
  userId: string | null;
};

type WebSearchToolOutput = {
  results: Array<{
    url: string;
    title?: string;
    snippet?: string;
    publishedAt?: string;
  }>;
};

type ToolExecuteResult<T> = AsyncIterable<T> | PromiseLike<T> | T;

function isAsyncIterable<T>(value: ToolExecuteResult<T>): value is AsyncIterable<T> {
  return (
    value != null &&
    typeof (value as { [Symbol.asyncIterator]?: unknown })[Symbol.asyncIterator] ===
      "function"
  );
}

/**
 * Resolves AI SDK tool execute results that may be PromiseLike or AsyncIterable.
 * For async iterables, returns the final yielded value.
 * @throws Error if async iterable yields no values.
 */
export async function resolveExecuteResult<T>(value: ToolExecuteResult<T>): Promise<T> {
  if (isAsyncIterable(value)) {
    let last: T | undefined;
    for await (const chunk of value) {
      last = chunk;
    }
    if (last === undefined) {
      throw new Error("Tool returned no output");
    }
    return last;
  }

  return await value;
}

type WebSearchExecute = (
  input: WebSearchToolInput,
  options: ToolExecutionOptions
) => ToolExecuteResult<WebSearchToolOutput> | undefined;

export function createWebSearchFallback(
  execute?: WebSearchExecute
): WebSearchFn | undefined {
  if (!execute) return undefined;

  return async ({ limit, query, toolCallId, userId }) => {
    const callOptions = { messages: [], toolCallId } satisfies ToolExecutionOptions;
    const executed = execute(
      {
        categories: null,
        fresh: false,
        freshness: null,
        limit,
        location: null,
        query,
        region: null,
        scrapeOptions: null,
        sources: ["web"],
        tbs: null,
        timeoutMs: null,
        userId: userId ?? null,
      },
      callOptions
    );

    if (!executed) return null;

    const result = await resolveExecuteResult<WebSearchToolOutput>(executed);
    return { results: result.results };
  };
}

export function createActivitiesService(input: {
  cache?: ActivitiesCache;
  webSearch?: WebSearchFn;
}): ActivitiesService {
  return new ActivitiesService({
    cache: input.cache,
    hashInput: hashInputForCache,
    logger: createServerLogger("activities.service"),
    places: {
      buildSearchQuery: buildActivitySearchQuery,
      getDetails: getActivityDetailsFromPlaces,
      search: searchActivitiesWithPlaces,
    },
    telemetry: {
      withSpan: (name, options, fn) =>
        withTelemetrySpan(name, options, async (span) => await fn(span)),
    },
    webSearch: input.webSearch,
  });
}
