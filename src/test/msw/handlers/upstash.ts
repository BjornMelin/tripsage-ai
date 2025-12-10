/**
 * @fileoverview MSW handlers for Upstash REST endpoints used in tests.
 * Provides deterministic in-memory behavior backed by the shared Upstash
 * store used by redis mocks. Keeps tests thread-safe under `--pool=threads`.
 */

import type { HttpHandler } from "msw";
import { HttpResponse, http } from "msw";
import { createRatelimitMock } from "@/test/upstash/ratelimit-mock";
import {
  resetRedisStore,
  runUpstashPipeline,
  sharedUpstashStore,
} from "@/test/upstash/redis-mock";

const pipelineMatcher = /https?:\/\/[^/]*upstash\.io\/pipeline/;
const ratelimitMatcher = /https?:\/\/[^/]*upstash\.io\/ratelimit.*/;
const qstashMatcher = /https?:\/\/qstash\.upstash\.io\/.*/;
const anyUpstash = /https?:\/\/[^/]*upstash\.io\/.*/;

// Create mock module and limiter instance
const ratelimitMock = createRatelimitMock();
const ratelimit = new ratelimitMock.Ratelimit({
  limiter: ratelimitMock.Ratelimit.slidingWindow(10, "1 m"),
});

export const upstashHandlers: HttpHandler[] = [
  http.post(pipelineMatcher, async ({ request }) => {
    const commands = await request.json();
    const result = await runUpstashPipeline(sharedUpstashStore, commands);
    return HttpResponse.json({ result, success: true });
  }),
  http.all(ratelimitMatcher, async ({ request }) => {
    const identifier = request.headers.get("x-forwarded-for") ?? "anonymous";
    const outcome = await ratelimit.limit(identifier);
    const headers = new Headers();
    headers.set("x-ratelimit-limit", String(outcome.limit));
    headers.set("x-ratelimit-remaining", String(outcome.remaining));
    headers.set("x-ratelimit-reset", String(outcome.reset));
    headers.set("retry-after", String(outcome.retryAfter));
    return HttpResponse.json(
      { result: outcome.success ? "OK" : "RATE_LIMITED" },
      {
        headers,
        status: outcome.success ? 200 : 429,
      }
    );
  }),
  http.post(qstashMatcher, async () =>
    HttpResponse.json(
      { messageId: "qstash-test-id", status: "enqueued" },
      { status: 200 }
    )
  ),
  http.all(anyUpstash, () => HttpResponse.json({ result: "OK", success: true })),
];

export function resetUpstashHandlers(): void {
  resetRedisStore(sharedUpstashStore);
  ratelimitMock.__reset();
}
