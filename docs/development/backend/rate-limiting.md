# Rate limiting

TripSage uses Upstash Redis + `@upstash/ratelimit` for server-side throttling:

- **HTTP API routes**: enforced in `src/lib/api/factory.ts` (`withApiGuards({ rateLimit: ... })`).
- **Webhooks**: enforced in `src/lib/webhooks/rate-limit.ts` and applied by `src/lib/webhooks/handler.ts`.
- **AI tools**: enforced in `src/ai/lib/tool-factory.ts` (`createAiTool({ guardrails: { rateLimit: ... } })`).

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
