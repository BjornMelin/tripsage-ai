/**
 * @fileoverview Batch web search tool with bounded concurrency and optional top-level rate limiting.
 */

import "server-only";

import {
  WEB_SEARCH_BATCH_OUTPUT_SCHEMA,
  WEB_SEARCH_OUTPUT_SCHEMA,
  webSearchInputSchema,
} from "@ai/tools/schemas/web-search";
import { webSearchBatchInputSchema } from "@ai/tools/schemas/web-search-batch";
import { normalizeWebSearchResults } from "@ai/tools/server/web-search-normalize";
import { Ratelimit } from "@upstash/ratelimit";
import type { ToolCallOptions } from "ai";
import { tool } from "ai";
import type { z } from "zod";
import { hashInputForCache } from "@/lib/cache/hash";
import { hashIdentifier, normalizeIdentifier } from "@/lib/ratelimit/identifier";
import { getRedis } from "@/lib/redis";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { webSearch } from "./web-search";

const webSearchBatchLogger = createServerLogger("tools.web_search_batch");

function isAsyncIterable(value: unknown): value is AsyncIterable<unknown> {
  return (
    typeof value === "object" &&
    value !== null &&
    typeof (value as { [Symbol.asyncIterator]?: unknown })[Symbol.asyncIterator] ===
      "function"
  );
}

async function resolveToolResult(result: unknown): Promise<unknown> {
  if (isAsyncIterable(result)) {
    let last: unknown;
    for await (const chunk of result) {
      last = chunk;
    }
    return last;
  }
  return await Promise.resolve(result);
}

/**
 * Build Upstash rate limiter for batch web search tool.
 *
 * Returns undefined if Upstash env vars are missing. Uses sliding window:
 * 20 requests per minute per user.
 *
 * @returns Rate limiter instance or undefined if not configured.
 */

function buildToolRateLimiter(): InstanceType<typeof Ratelimit> | undefined {
  const redis = getRedis();
  if (!redis) return undefined;
  return new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(20, "1 m"),
    prefix: "ratelimit:tools:web-search-batch",
    redis,
  });
}

/**
 * Input schema for batch web search tool.
 *
 * Validates 1-10 queries and shared search parameters (sources, categories,
 * location, tbs, scrapeOptions). All queries use the same configuration.
 */

/**
 * Batch web search tool using Firecrawl v2.5 API.
 *
 * Executes multiple queries concurrently (pool size 5). Reuses webSearch tool per
 * query, inheriting caching and rate limiting. All queries share the same search
 * configuration. Falls back to direct HTTP only for unexpected internal errors.
 *
 * @returns Batch results with array of query results and total execution time.
 * @throws {Error} Error with code:
 *   - "web_search_rate_limited": Top-level rate limit exceeded (429)
 *   - Query errors are returned in results array, not thrown
 */
export const webSearchBatch = tool({
  description:
    "Run multiple web searches in a single call, reusing per-query cache and rate limits.",
  execute: ({ queries, userId, ...rest }, callOptions: ToolCallOptions) => {
    const started = Date.now();

    return withTelemetrySpan(
      "tool.web_search_batch",
      {
        attributes: {
          count: queries.length,
          fresh: Boolean(rest.fresh),
          "tool.name": "webSearchBatch",
        },
      },
      async (span) => {
        // Optional top-level rate limiting (in addition to per-query limits)
        try {
          const rl = buildToolRateLimiter();
          if (rl && userId) {
            const identifier = `user:${hashIdentifier(normalizeIdentifier(userId))}`;
            const rr = await rl.limit(identifier);
            if (!rr.success) {
              span.addEvent("rate_limited", { "ratelimit.subject_type": "user" });
              const err = new Error("web_search_rate_limited");
              (err as Error & { meta?: unknown }).meta = rr;
              throw err;
            }
          }
        } catch (e) {
          if ((e as Error).message?.startsWith?.("web_search_rate_limited")) throw e;
        }

        // Bounded concurrency runner with pool size 5
        const poolSize = 5;
        const results: Array<
          z.infer<typeof WEB_SEARCH_BATCH_OUTPUT_SCHEMA>["results"][number]
        > = [];
        let index = 0;
        const runOne = async (q: string) => {
          try {
            const params = webSearchInputSchema.parse({
              categories: rest.categories ?? null,
              fresh: rest.fresh ?? false,
              freshness: null,
              limit: rest.limit ?? 5,
              location: rest.location ?? null,
              query: q,
              region: null,
              scrapeOptions: rest.scrapeOptions ?? null,
              sources: rest.sources ?? null,
              tbs: rest.tbs ?? null,
              timeoutMs: rest.timeoutMs ?? null,
              userId: userId ?? null,
            });
            const raw = await resolveToolResult(
              webSearch.execute?.(params, callOptions)
            );
            const parsed = WEB_SEARCH_OUTPUT_SCHEMA.parse(raw);
            const validatedValue = {
              ...parsed,
              results: normalizeWebSearchResults(parsed.results),
            };
            results.push({ ok: true, query: q, value: validatedValue });
          } catch (err) {
            const message = err instanceof Error ? err.message : String(err);
            const code = message.includes("web_search_rate_limited")
              ? "web_search_rate_limited"
              : message.includes("web_search_unauthorized")
                ? "web_search_unauthorized"
                : message.includes("web_search_payment_required")
                  ? "web_search_payment_required"
                  : message.includes("web_search_failed")
                    ? "web_search_failed"
                    : "web_search_error";
            // Fallback to direct HTTP for unexpected errors (not rate/auth/payment)
            if (code === "web_search_error") {
              try {
                // Proper env access via validated server env helpers
                const { getServerEnvVar, getServerEnvVarWithFallback } = await import(
                  "@/lib/env/server"
                );
                let apiKey: string;
                try {
                  apiKey = getServerEnvVar("FIRECRAWL_API_KEY");
                } catch {
                  throw new Error("web_search_not_configured");
                }
                if (!apiKey) throw new Error("web_search_not_configured");
                const baseUrl = getServerEnvVarWithFallback(
                  "FIRECRAWL_BASE_URL",
                  "https://api.firecrawl.dev/v2"
                );
                const url = `${baseUrl}/search`;
                const body = {
                  categories: rest.categories,
                  limit: rest.limit ?? 5,
                  location: rest.location,
                  query: q,
                  scrapeOptions: rest.scrapeOptions,
                  sources: rest.sources,
                  tbs: rest.tbs,
                  timeout: rest.timeoutMs,
                } as Record<string, unknown>;
                const startedAt = Date.now();
                span.addEvent("http_fallback_post", { queryLength: q.length });
                const res = await fetch(url, {
                  body: JSON.stringify(body),
                  headers: {
                    authorization: `Bearer ${apiKey}`,
                    "content-type": "application/json",
                  },
                  method: "POST",
                });
                if (!res.ok) {
                  const text = await res.text();
                  throw new Error(
                    `web_search_failed:${res.status}:body_hash=${hashInputForCache(text)}:body_length=${text.length}`
                  );
                }
                const data = (await res.json()) as {
                  results?: {
                    url: string;
                    title?: string;
                    snippet?: string;
                    publishedAt?: string;
                  }[];
                };
                // Normalize fallback HTTP response to ensure strict schema compliance
                const rawResults = Array.isArray(data.results) ? data.results : [];
                const normalizedResults = normalizeWebSearchResults(rawResults);
                const validatedValue = {
                  fromCache: false,
                  results: normalizedResults,
                  tookMs: Date.now() - startedAt,
                };
                results.push({
                  ok: true,
                  query: q,
                  value: validatedValue,
                });
              } catch (e2) {
                const msg2 = e2 instanceof Error ? e2.message : String(e2);
                span.addEvent("http_fallback_error", {
                  code,
                  queryLength: q.length,
                });
                // Debug aid for tests
                webSearchBatchLogger.error("fallback_error", {
                  code,
                  queryLength: q.length,
                });
                results.push({ error: { code, message: msg2 }, ok: false, query: q });
              }
            } else {
              span.addEvent("primary_error", {
                code,
                queryLength: q.length,
              });
              // Debug aid for tests
              webSearchBatchLogger.error("primary_error", {
                code,
                queryLength: q.length,
              });
              results.push({ error: { code, message }, ok: false, query: q });
            }
          }
        };

        const workers: Promise<void>[] = [];
        for (let i = 0; i < Math.min(poolSize, queries.length); i++) {
          workers.push(
            (async function worker() {
              while (index < queries.length) {
                const current = queries[index++];
                await runOne(current);
              }
            })()
          );
        }
        await Promise.all(workers);
        // Validate final output against strict schema
        const rawOut = {
          results,
          tookMs: Date.now() - started,
        };
        const validated = WEB_SEARCH_BATCH_OUTPUT_SCHEMA.parse(rawOut);
        return validated;
      }
    );
  },
  inputSchema: webSearchBatchInputSchema,
});
