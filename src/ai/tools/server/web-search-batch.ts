/**
 * @fileoverview Batch web search tool with bounded concurrency and optional top-level rate limiting.
 */

import "server-only";

import { createAiTool } from "@ai/lib/tool-factory";
import {
  WEB_SEARCH_BATCH_OUTPUT_SCHEMA,
  WEB_SEARCH_OUTPUT_SCHEMA,
  webSearchInputSchema,
} from "@ai/tools/schemas/web-search";
import {
  type WebSearchBatchModelOutput,
  webSearchBatchInputSchema,
} from "@ai/tools/schemas/web-search-batch";
import { createToolError, TOOL_ERROR_CODES } from "@ai/tools/server/errors";
import { normalizeWebSearchResults } from "@ai/tools/server/web-search-normalize";
import { Ratelimit } from "@upstash/ratelimit";
import type { ToolExecutionOptions } from "ai";
import { z } from "zod";
import { hashInputForCache } from "@/lib/cache/hash";
import { hashIdentifier, normalizeIdentifier } from "@/lib/ratelimit/identifier";
import { getRedis } from "@/lib/redis";
import { createServerLogger } from "@/lib/telemetry/logger";
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
export const webSearchBatch = createAiTool({
  description:
    "Run multiple web searches in a single call, reusing per-query cache and rate limits.",
  execute: async ({ queries, userId, ...rest }, callOptions: ToolExecutionOptions) => {
    const started = Date.now();
    // Optional top-level rate limiting (in addition to per-query limits)
    try {
      const rl = buildToolRateLimiter();
      if (rl && userId) {
        const identifier = `user:${hashIdentifier(normalizeIdentifier(userId))}`;
        const rr = await rl.limit(identifier);
        if (!rr.success) {
          throw createToolError(TOOL_ERROR_CODES.webSearchRateLimited, undefined, rr);
        }
      }
    } catch (e) {
      if (
        e instanceof Error &&
        (e as { code?: unknown }).code === TOOL_ERROR_CODES.webSearchRateLimited
      )
        throw e;
      webSearchBatchLogger.error("rate_limiter_error", {
        error: e instanceof Error ? e.message : String(e),
      });
    }

    // Bounded concurrency runner with pool size 5
    const poolSize = 5;
    const results: Array<
      z.infer<typeof WEB_SEARCH_BATCH_OUTPUT_SCHEMA>["results"][number]
    > = [];
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
        const raw = await resolveToolResult(webSearch.execute?.(params, callOptions));
        const parsed = WEB_SEARCH_OUTPUT_SCHEMA.parse(raw);
        const validatedValue = {
          ...parsed,
          results: normalizeWebSearchResults(parsed.results),
        };
        results.push({ ok: true, query: q, value: validatedValue });
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        // Check for typed error with code property first, then fall back to message parsing
        const hasCode = (e: unknown): e is { code: string } =>
          typeof e === "object" &&
          e !== null &&
          "code" in e &&
          typeof (e as { code?: unknown }).code === "string";
        const knownCodes = new Set<string>([
          TOOL_ERROR_CODES.webSearchRateLimited,
          TOOL_ERROR_CODES.webSearchUnauthorized,
          TOOL_ERROR_CODES.webSearchPaymentRequired,
          TOOL_ERROR_CODES.webSearchFailed,
        ]);
        let code: string;
        if (hasCode(err) && knownCodes.has(err.code)) {
          code = err.code;
        } else if (message.includes(TOOL_ERROR_CODES.webSearchRateLimited)) {
          code = TOOL_ERROR_CODES.webSearchRateLimited;
        } else if (message.includes(TOOL_ERROR_CODES.webSearchUnauthorized)) {
          code = TOOL_ERROR_CODES.webSearchUnauthorized;
        } else if (message.includes(TOOL_ERROR_CODES.webSearchPaymentRequired)) {
          code = TOOL_ERROR_CODES.webSearchPaymentRequired;
        } else if (message.includes(TOOL_ERROR_CODES.webSearchFailed)) {
          code = TOOL_ERROR_CODES.webSearchFailed;
        } else {
          code = TOOL_ERROR_CODES.webSearchError;
        }
        // Fallback to direct HTTP for unexpected errors (not rate/auth/payment)
        if (code === TOOL_ERROR_CODES.webSearchError) {
          try {
            // Proper env access via validated server env helpers
            const { getServerEnvVar, getServerEnvVarWithFallback } = await import(
              "@/lib/env/server"
            );
            let apiKey: string;
            try {
              apiKey = getServerEnvVar("FIRECRAWL_API_KEY");
            } catch {
              throw createToolError(TOOL_ERROR_CODES.webSearchNotConfigured);
            }
            const baseUrl = getServerEnvVarWithFallback(
              "FIRECRAWL_BASE_URL",
              "https://api.firecrawl.dev/v2"
            );
            const url = `${baseUrl}/search`;
            // Build body with only defined fields to avoid API rejection
            const body: Record<string, unknown> = {
              limit: rest.limit ?? 5,
              query: q,
            };
            if (rest.categories != null) body.categories = rest.categories;
            if (rest.location != null) body.location = rest.location;
            if (rest.scrapeOptions != null) body.scrapeOptions = rest.scrapeOptions;
            if (rest.sources != null) body.sources = rest.sources;
            if (rest.tbs != null) body.tbs = rest.tbs;
            const startedAt = Date.now();
            // Clamp timeouts to safe bounds to avoid too-short/unbounded requests and align with provider expectations.
            const timeoutMs = Math.min(20000, Math.max(5000, rest.timeoutMs ?? 12000));
            body.timeout = timeoutMs;
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
            let res: Response;
            try {
              res = await fetch(url, {
                body: JSON.stringify(body),
                headers: {
                  authorization: `Bearer ${apiKey}`,
                  "content-type": "application/json",
                },
                method: "POST",
                signal: controller.signal,
              });
            } catch (fetchError) {
              if (fetchError instanceof Error && fetchError.name === "AbortError") {
                throw createToolError(
                  TOOL_ERROR_CODES.webSearchFailed,
                  "web_search_timeout",
                  {
                    timeoutMs,
                  }
                );
              }
              throw fetchError;
            } finally {
              clearTimeout(timeoutId);
            }
            if (!res.ok) {
              const text = await res.text();
              throw createToolError(
                TOOL_ERROR_CODES.webSearchFailed,
                `web search failed with status ${res.status}`,
                {
                  bodyHash: hashInputForCache(text),
                  bodyLength: text.length,
                  status: res.status,
                }
              );
            }
            const firecrawlResponseSchema = z.object({
              results: z
                .array(
                  z.object({
                    publishedAt: z.string().optional(),
                    snippet: z.string().optional(),
                    title: z.string().optional(),
                    url: z.string(),
                  })
                )
                .optional(),
            });
            const parsedResponse = firecrawlResponseSchema.safeParse(await res.json());
            if (!parsedResponse.success) {
              webSearchBatchLogger.error("fallback_response_invalid", {
                error: parsedResponse.error.message,
                queryLength: q.length,
              });
            }
            const data = parsedResponse.success ? parsedResponse.data : { results: [] };
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
            // Debug aid with safe context (no sensitive data)
            webSearchBatchLogger.error("fallback_error", {
              code,
              errorSnippet: msg2.slice(0, 100),
              queryLength: q.length,
              sanitizedQuery: q.slice(0, 50).trim(),
            });
            results.push({ error: { code, message: msg2 }, ok: false, query: q });
          }
        } else {
          // Debug aid with safe context (no sensitive data)
          webSearchBatchLogger.error("primary_error", {
            code,
            errorSnippet: message.slice(0, 100),
            queryLength: q.length,
            sanitizedQuery: q.slice(0, 50).trim(),
          });
          results.push({ error: { code, message }, ok: false, query: q });
        }
      }
    };

    // Sequential index allocation (safe due to JS single-threaded event loop)
    let index = 0;
    const getNextIndex = (): number => index++;
    const workers: Promise<void>[] = [];
    for (let i = 0; i < Math.min(poolSize, queries.length); i++) {
      workers.push(
        (async function worker() {
          while (true) {
            const currentIndex = getNextIndex();
            if (currentIndex >= queries.length) break;
            const current = queries[currentIndex];
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
    return WEB_SEARCH_BATCH_OUTPUT_SCHEMA.parse(rawOut);
  },
  guardrails: {
    telemetry: {
      attributes: (params) => ({
        count: params.queries.length,
        fresh: Boolean(params.fresh),
      }),
    },
  },
  inputSchema: webSearchBatchInputSchema,
  name: "webSearchBatch",
  outputSchema: WEB_SEARCH_BATCH_OUTPUT_SCHEMA,
  /**
   * Simplifies batch search results for model consumption to reduce token usage.
   * Strips snippets, publishedAt dates, and limits results per query.
   */
  toModelOutput: (result): WebSearchBatchModelOutput => ({
    queryCount: result.results.length,
    results: result.results.map((r) => ({
      error: !r.ok && r.error ? r.error.code : undefined,
      ok: r.ok,
      query: r.query,
      value:
        r.ok && r.value
          ? {
              resultCount: r.value.results.length,
              // Cap to 5 results per query to fit token budgets; raise/make configurable if higher recall is needed.
              results: r.value.results.slice(0, 5).map((res) => ({
                title: res.title,
                url: res.url,
              })),
            }
          : undefined,
    })),
    tookMs: result.tookMs,
  }),
  validateOutput: true,
});
