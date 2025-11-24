/**
 * @fileoverview MSW handlers for Upstash REST endpoints used in tests.
 * Provides deterministic in-memory behavior backed by the shared Upstash
 * store used by redis mocks. Keeps tests thread-safe under `--pool=threads`.
 */

import type { HttpHandler } from "msw";
import { HttpResponse, http } from "msw";
import {
  resetRedisStore,
  runUpstashPipeline,
  sharedUpstashStore,
} from "@/test/upstash/redis-mock";

const pipelineMatcher = /https?:\/\/[^/]*upstash\.io\/pipeline/;
const anyUpstash = /https?:\/\/[^/]*upstash\.io\/.*/;

export const upstashHandlers: HttpHandler[] = [
  http.post(pipelineMatcher, async ({ request }) => {
    const commands = await request.json();
    const result = await runUpstashPipeline(sharedUpstashStore, commands);
    return HttpResponse.json({ result, success: true });
  }),
  http.all(anyUpstash, () => HttpResponse.json({ result: "OK", success: true })),
];

export function resetUpstashHandlers(): void {
  resetRedisStore(sharedUpstashStore);
}
