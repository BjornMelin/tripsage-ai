/**
 * @fileoverview Batch web search tool that executes multiple queries concurrently.
 *
 * Uses bounded parallelism (pool size 5) and reuses webSearch tool per query.
 * Includes optional top-level rate limiting (20/min) in addition to per-query limits.
 */

import { Ratelimit } from "@upstash/ratelimit";
import { Redis } from "@upstash/redis";
import { tool } from "ai";
import { z } from "zod";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import { normalizeWebSearchResults } from "@/lib/tools/web-search-normalize";
import { WEB_SEARCH_BATCH_OUTPUT_SCHEMA } from "@/types/web-search";
import { webSearch } from "./web-search";

/**
 * Build Upstash rate limiter for batch web search tool.
 *
 * Returns undefined if Upstash env vars are missing. Uses sliding window:
 * 20 requests per minute per user.
 *
 * @returns Rate limiter instance or undefined if not configured.
 */
function buildToolRateLimiter(): InstanceType<typeof Ratelimit> | undefined {
  const url = process.env.UPSTASH_REDIS_REST_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN;
  if (!url || !token) return undefined;
  return new Ratelimit({
    analytics: true,
    limiter: Ratelimit.slidingWindow(20, "1 m"),
    prefix: "ratelimit:tools:web-search-batch",
    redis: Redis.fromEnv(),
  });
}

/**
 * Input schema for batch web search tool.
 *
 * Validates 1-10 queries and shared search parameters (sources, categories,
 * location, tbs, scrapeOptions). All queries use the same configuration.
 */
const batchInputSchema = z.object({
  categories: z.array(z.string()).optional(),
  fresh: z.boolean().default(false).optional(),
  limit: z.number().int().min(1).max(10).default(5).optional(),
  location: z.string().max(120).optional(),
  queries: z.array(z.string().min(2).max(256)).min(1).max(10),
  scrapeOptions: z
    .object({
      formats: z.array(z.enum(["markdown", "html", "links", "screenshot"])).optional(),
      parsers: z.array(z.string()).optional(),
      proxy: z.enum(["basic", "stealth"]).optional(),
    })
    .optional(),
  sources: z.array(z.enum(["web", "news", "images"])).optional(),
  tbs: z.string().optional(),
  timeoutMs: z.number().int().positive().optional(),
  userId: z.string().optional(),
});

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
  execute: ({ queries, userId, ...rest }, ctx) => {
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
      async () => {
        // Optional top-level rate limiting (in addition to per-query limits)
        try {
          const rl = buildToolRateLimiter();
          if (rl && userId) {
            const rr = await rl.limit(userId);
            if (!rr.success) {
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
            const exec = (
              webSearch as unknown as {
                execute: (a: unknown, b?: unknown) => Promise<unknown>;
              }
            ).execute;
            const value = (await exec(
              {
                ...rest,
                fresh: rest.fresh ?? false,
                limit: rest.limit ?? 5,
                query: q,
                userId,
              },
              ctx
            )) as unknown as {
              results: {
                url: string;
                title?: string;
                snippet?: string;
                publishedAt?: string;
              }[];
              fromCache: boolean;
              tookMs: number;
            };
            // Normalize results to ensure strict schema compliance
            const rawResults = Array.isArray(value.results) ? value.results : [];
            const normalizedResults = normalizeWebSearchResults(rawResults);
            const validatedValue = {
              fromCache: Boolean(value.fromCache),
              results: normalizedResults,
              tookMs: Number(value.tookMs),
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
                const apiKey = process.env.FIRECRAWL_API_KEY;
                if (!apiKey) throw new Error("web_search_not_configured");
                const baseUrl =
                  process.env.FIRECRAWL_BASE_URL ?? "https://api.firecrawl.dev/v2";
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
                  throw new Error(`web_search_failed:${res.status}:${text}`);
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
                results.push({ error: { code, message: msg2 }, ok: false, query: q });
              }
            } else {
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
                // eslint-disable-next-line no-await-in-loop
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
  inputSchema: batchInputSchema,
});
