# Rate limiting

TripSage uses Upstash Redis + `@upstash/ratelimit` for server-side throttling:

- **HTTP API routes**: enforced in `src/lib/api/factory.ts` (`withApiGuards({ rateLimit: ... })`).
- **Webhooks**: enforced in `src/lib/webhooks/rate-limit.ts` and applied by `src/lib/webhooks/handler.ts`.
- **AI tools**: enforced in `src/ai/lib/tool-factory.ts` (`createAiTool({ guardrails: { rateLimit: ... } })`).

## Degraded-mode policy (fail-open vs fail-closed)

Some endpoints are privileged or cost-bearing and must **fail closed** if rate limiting cannot be enforced (missing Redis config, Redis unavailable, enforcement errors).

- Route handlers (`withApiGuards`) support `degradedMode: "fail_closed" | "fail_open"`.
  - `fail_closed`: deny the request with `503 rate_limit_unavailable`
  - `fail_open`: allow the request, but emit a deduped operational alert (`ratelimit.degraded`)
- Default policy:
  - `fail_closed` for `embeddings`, `ai:stream`, `telemetry:ai-demo`, and `keys:*`
  - `fail_open` for non-privileged routes unless explicitly overridden
- Webhooks (`src/lib/webhooks/rate-limit.ts`) default to `fail_closed`.

### Upstash timeout behavior (important)

`@upstash/ratelimit` supports a `timeout` option (default: **5000ms**) where the request is allowed to pass on timeout (`success: true`, `reason: "timeout"`).

TripSage treats `reason: "timeout"` as **degraded infrastructure** and applies the same `degradedMode` policy:

- `fail_closed`: deny with `503 rate_limit_unavailable`
- `fail_open`: allow but emit `ratelimit.degraded` (deduped)

References:

- <https://upstash.com/docs/redis/sdks/ratelimit-ts/features#timeout>
- <https://upstash.com/docs/redis/sdks/ratelimit-ts/methods#limit>

## Dynamic limits (global)

TripSage enables Upstash “dynamic limits” support by setting `dynamicLimits: true` when constructing `Ratelimit` instances (API routes, webhooks, AI tools). This allows operators to set a global limit at runtime via Upstash dynamic limit APIs (`setDynamicLimit`, `getDynamicLimit`) and adds one Redis command per rate-limit check.

Note: When `dynamicLimits` is enabled on a `Ratelimit` instance, the default ephemeral cache can keep identifiers marked as blocked until their reset timestamp expires. Raising limits at runtime via `setDynamicLimit`/`getDynamicLimit` may not take immediate effect for those cached blocked identifiers; clear the ephemeral cache or wait for expiry if you need immediate impact.

References:

- <https://upstash.com/docs/redis/sdks/ratelimit-ts/methods>
- ADR-0032: `docs/architecture/decisions/adr-0032-centralized-rate-limiting.md`

## Redis access (canonical)

Always obtain Redis via `getRedis()`:

- `src/lib/redis.ts` exports `getRedis()` with a test injection hook.
- Do not call `Redis.fromEnv()` in application code.

## Client IP extraction (canonical)

Use `src/lib/http/ip.ts`:

- `getClientIpFromHeaders(headers)` accepts a header-only interface so it can be used from:
  - `NextRequest.headers` (route handlers)
  - `Request.headers` (webhooks/jobs)
  - `next/headers().get()` (server-only contexts)
- Header precedence:
  1) `x-real-ip`
  2) `x-forwarded-for` (first value)
  3) `cf-connecting-ip`
  4) `"unknown"`
- The extractor rejects invalid IP strings to reduce spoofing risks when running behind untrusted proxies.

## Identifier hashing policy

Never use raw IPs as Upstash identifiers. Hash IP-derived identifiers before passing them to `Ratelimit.limit()`:

- `src/lib/ratelimit/identifier.ts`
  - `hashIdentifier(raw)` → SHA-256 hex
  - `getTrustedRateLimitIdentifierFromHeaders(headers)` → stable hashed identifier derived from client IP headers

Patterns used in code:

- **Webhook IP buckets**: `ip:${hashIdentifier(ip)}` (or `ip:unknown` when IP is unavailable)
- **AI tools**:
  - Header-derived: `user:${sha256(userId)}` / `ip:${sha256(ip)}`
  - Tool-provided identifier: `id:${sha256(raw)}` (or `{prefix}:${sha256(value)}` if the tool explicitly returns `prefix:value`)
- **API routes (withApiGuards)**:
  - Authenticated routes use `user:${sha256(user.id)}`.
  - Unauthenticated routes use `ip:${sha256(ip)}` (or `ip:unknown` when no valid IP is available).

## Rate limit response headers

HTTP endpoints attach standard headers on 429 responses:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset` (Unix timestamp in **milliseconds**)
- `Retry-After` (seconds; derived from `reset` when blocked)

Shared helpers:

- `src/lib/ratelimit/headers.ts` provides `createRateLimitHeaders()` and `applyRateLimitHeaders()`.

## Testing and mocking

Prefer existing Upstash test harness utilities:

- Shared mocks/stubs: `src/test/upstash/*`
- MSW handlers: `src/test/msw/handlers/upstash.ts`
- API route rate limiting can be overridden via `setRateLimitFactoryForTests()` in `src/lib/api/factory.ts`.

See `docs/development/testing/testing.md` for the current test tiers and mock setup guidance.
