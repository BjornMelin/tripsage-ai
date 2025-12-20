# Implementation Guide - Remediation Plan (2025-12-15)

## How to use this document

This file is both:

1) A detailed remediation guide.
2) A ready-to-run Codex execution prompt for the follow-up implementation run.

## Ground rules for the implementation run

- Work in small, reviewable commits.
- Add/adjust tests before refactors when risk is high.
- Prefer deleting code over adding code.
- Prefer built-in and library-native features over custom wrappers.
- No breaking API changes without a migration plan.
- Every checkbox must map to a concrete diff and a verification command.

## References (append throughout)

- Google Eng Practices – The Standard of Code Review: <https://google.github.io/eng-practices/review/reviewer/standard.html>
- Software Engineering at Google (Abseil) – Code Review: <https://abseil.io/resources/swe-book/html/ch09.html>
- OWASP Code Review Guide (PDF): <https://owasp.org/www-project-code-review-guide/assets/OWASP_Code_Review_Guide_v2.pdf>
- OWASP Secure Code Review Cheat Sheet: <https://cheatsheetseries.owasp.org/cheatsheets/Secure_Code_Review_Cheat_Sheet.html>
- OWASP GenAI LLM09 Overreliance: <https://genai.owasp.org/llmrisk2023-24/llm09-overreliance/>
- Measuring LLM Package Hallucination Vulnerabilities (arXiv HTML): <https://arxiv.org/html/2501.19012v1>
- CACM (hallucinated/malicious packages risk): <https://cacm.acm.org/news/nonsense-and-malicious-packages-llm-hallucinations-in-code-generation/>
- Simon Willison (hallucinations risk patterns): <https://simonwillison.net/2023/May/3/hallucinations-in-code/>
- Next.js `use server` directive: <https://nextjs.org/docs/app/api-reference/directives/use-server>
- React `use server` directive: <https://react.dev/reference/rsc/use-server>
- Next.js `serverExternalPackages`: <https://nextjs.org/docs/app/api-reference/config/next-config-js/serverExternalPackages>
- Next.js OpenTelemetry setup: <https://nextjs.org/docs/app/guides/open-telemetry>
- Next.js CI build caching: <https://nextjs.org/docs/app/guides/ci-build-caching>
- Next.js `redirect()`: <https://nextjs.org/docs/app/api-reference/functions/redirect>
- Next.js Turbopack config: <https://nextjs.org/docs/app/api-reference/config/next-config-js/turbopack>
- Next.js Image SVG safety: <https://nextjs.org/docs/app/api-reference/components/image#dangerouslyallowsvg>
- Vercel conformance rule (safe SVG images): <https://vercel.com/docs/conformance/rules/NEXTJS_SAFE_SVG_IMAGES>
- Supabase SSR client creation: <https://supabase.com/docs/guides/auth/server-side/creating-a-client>
- Upstash QStash signature validation (raw body required): <https://upstash.com/docs/qstash/howto/signature>
- Upstash Ratelimit timeout behavior (allow-by-default): <https://upstash.com/docs/redis/sdks/ratelimit-ts/features#timeout>
- Upstash Ratelimit `limit()` response (`reason: "timeout"`): <https://upstash.com/docs/redis/sdks/ratelimit-ts/methods#limit>
- OWASP Unvalidated Redirects & Forwards: <https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html>
- OWASP SSRF Prevention: <https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html>
- OWASP API4:2023 Unrestricted Resource Consumption: <https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/>
- OWASP API2:2023 Broken Authentication: <https://owasp.org/API-Security/editions/2023/en/0xa2-broken-authentication/>
- Node.js module cycles: <https://nodejs.org/api/modules.html#cycles>
- Zod v4 docs: <https://zod.dev/v4>
- Vitest coverage docs (v4): <https://vitest.dev/guide/coverage.html>

## Plan overview (fill after audit)

- Phase 0 (Safety + Baseline)
- Phase 1 (AI slop removal + simplification)
- Phase 2 (Correctness + security hardening)
- Phase 3 (Performance + reliability)
- Phase 4 (DX + tooling + long-term guardrails)

## Stop-the-line criteria (implementation run)

Stop and fix before doing any further refactors if any of these are true:

- `pnpm build` fails (REL-001 is currently blocking).
- Any cost-bearing or privileged endpoint is public or can become public via misconfig (SEC-006, SEC-007, SEC-009).
- Request parsing can be forced to buffer unbounded payloads (SEC-001).
- CI still allows merging without a successful production build (DX-002).

## Phase 0 - Safety + Baseline

Goal: restore “merge-safe” invariants (build passes, CI enforces build, baseline security gates exist) before touching architecture.

### 0.1 Fix the production build blocker in Server Actions

- [x] (REL-001) Remove non-action exports from `src/app/dashboard/search/activities/actions.ts`
  - Files:
    - `src/app/dashboard/search/activities/actions.ts`
    - `src/app/dashboard/search/activities/activities-search-client.tsx`
    - `src/app/dashboard/search/activities/page.tsx`
  - Steps:
    - Move `ActivitySearchValidationError` into a non-`"use server"` module (or replace with structured error returns).
    - Ensure the `"use server"` file exports only async server functions (no classes, no constants, no types relied on at runtime).
    - Re-run build to confirm Turbopack recognizes the module exports correctly.
  - Verify:
    - `pnpm build`
    - `pnpm type-check`
    - `pnpm test:affected`
  - References:
    - <https://nextjs.org/docs/app/api-reference/directives/use-server>
    - <https://react.dev/reference/rsc/use-server>

### 0.2 Make CI build-gated (no more "green CI, broken deploy")

- [x] (DX-002, REL-001) Add a CI job/step that runs `pnpm build`
  - Files:
    - `.github/workflows/ci.yml`
  - Steps:
    - Add `pnpm build` as a required step for PRs that touch `src/**`, `next.config.ts`, or other build-affecting files.
    - Add `.next/cache` caching per Next.js guidance to keep CI runtime sane.
  - Verify:
    - CI fails when `pnpm build` fails.
    - CI passes on a clean PR with no build errors.
  - References:
    - <https://nextjs.org/docs/app/guides/ci-build-caching>

### 0.3 Eliminate Turbopack externalization warnings for OTEL under pnpm

- [x] (DX-001) Install missing direct deps required for externalized OTEL packages
  - Files:
    - `package.json`
    - `pnpm-lock.yaml`
  - Steps:
    - Add `import-in-the-middle` and `require-in-the-middle` as direct dependencies (they are in Next’s `serverExternalPackages` list and must be resolvable from the output).
    - Confirm runtime resolution from project root.
  - Verify:
    - `node -e \"require.resolve('import-in-the-middle'); require.resolve('require-in-the-middle')\"`
    - `pnpm build` emits no warnings about these packages being unresolved.
  - References:
    - <https://nextjs.org/docs/app/api-reference/config/next-config-js/serverExternalPackages>
    - <https://nextjs.org/docs/app/guides/open-telemetry>

### 0.4 Remove invalid Turbopack config override

- [x] (DX-003) Remove or correct `turbopack.root` config
  - Files:
    - `next.config.ts`
  - Steps:
    - Delete `turbopack.root` entirely (preferred) unless you actually depend on linked/workspace resolution outside repo root, or Next is inferring the root from an unrelated lockfile in a parent directory.
    - If you keep it, set it to an absolute path. The build-time assertion in `next.config.ts` validates that `turbopack.root` is absolute and points to an existing directory (throws on failure).
  - Verify:
    - `pnpm build` succeeds; the programmatic assertion in `next.config.ts` enforces the absolute-path contract automatically.
  - References:
    - <https://nextjs.org/docs/pages/api-reference/config/next-config-js/turbopack>

### 0.5 Make coverage thresholds real (or remove the illusion)

- [x] (TEST-001) Fix Vitest coverage threshold configuration and enforcement
  - Files:
    - `vitest.config.ts`
    - Potentially new docs under `docs/development/testing/` (if policy changes)
  - Steps:
    - Align config shape to Vitest v4 docs (current `coverage.thresholds.global` appears ignored).
    - Decide enforcement strategy:
      - Either enforce realistic global thresholds immediately, or
      - Remove misleading thresholds and add a staged ramp plan with targeted thresholds for high-risk modules.
  - Verify:
    - `pnpm test:coverage` fails when coverage is below the configured thresholds.
  - References:
    - <https://vitest.dev/guide/coverage.html>

## Phase 1 - AI slop removal + simplification

Goal: delete misleading docs, reduce type escapes, and force a single “correct” way to do critical things (Supabase, tools, webhooks).

### 1.1 Fix Supabase SSR factory naming collision and doc drift

- [x] (AI-001) Remove misleading factory docs and eliminate `createServerSupabase` naming collision
  - Files:
    - `src/lib/supabase/factory.ts`
    - `src/lib/supabase/server.ts`
    - `src/lib/supabase/__tests__/factory.spec.ts`
  - Steps:
    - Choose one public entrypoint for server Supabase creation (recommended: the async wrapper in `server.ts`).
    - Rename/privatize the lower-level factory to avoid “wrong import” mistakes.
    - Delete/trim doc blocks that claim behavior the tests disprove.
  - Verify:
    - `pnpm type-check`
    - `pnpm test:affected`
  - References:
    - <https://supabase.com/docs/guides/auth/server-side/creating-a-client>

### 1.2 Reduce type-safety bypass via `as unknown as`

- [x] (AI-004) Burn down `as unknown as` in boundary modules first (DB/RPC/external API/tool adapters)
  - Files (starting targets from evidence):
    - `src/lib/supabase/rpc.ts`
    - `src/lib/rag/**`
    - `src/app/api/jobs/memory-sync/route.ts`
  - Steps:
    - Replace casts with Zod validation at boundaries using existing `@schemas/*` where available.
    - If a cast is unavoidable, isolate it to a tiny adapter with a single exported function and a test.
    - Add a CI check that flags new `as unknown as` in non-test code unless explicitly allowlisted.
    - Optional follow-up: remove `as unknown as` from `src/test/**` helpers/mocks; when a type is too large to model, centralize intentional test-only coercions in `src/test/helpers/unsafe-cast.ts`.
  - Verify:
    - `pnpm check:no-unknown-casts`
    - `rg \"as unknown as\" src | wc -l` is `0`.
    - `rg \"as unknown as\" src --glob '!src/test/**' --glob '!src/**/__tests__/**' --glob '!src/**/*.test.*' --glob '!src/**/*.spec.*' --glob '!src/mocks/**' | wc -l` is `0`.
    - `pnpm test:affected`

### 1.3 Remove boilerplate `@fileoverview` headers where they don’t encode invariants

- [x] (AI-002) Keep `@fileoverview` headers, but make them concise and accurate
  - Files:
    - Opportunistic: any files modified for Phase 0–2 fixes
  - Steps:
    - Keep `@fileoverview` in touched files for fast scanning.
    - Make it 1 sentence, technical, and consistent with exports (no "key features" lists).
    - Remove lists of features; reference a doc or test if detail is needed.
  - Verify:
    - Review touched files: `@fileoverview` is short and matches behavior.
  - References:
    - <https://genai.owasp.org/llmrisk2023-24/llm09-overreliance/>

### 1.4 Replace webhook error heuristics with typed errors

- [x] (AI-003) Remove `classifyError()` substring heuristics; switch to explicit typed errors
  - Files:
    - `src/lib/webhooks/handler.ts`
    - Related webhook entrypoints in `src/app/api/**` that depend on its behavior
  - Steps:
    - Define a minimal set of typed errors with explicit status mapping.
    - Ensure retry semantics are correct per sender (QStash, Stripe, etc.).
  - Verify:
    - `pnpm test:affected`
    - Add/extend unit tests that assert status codes for each error class.
  - References:
    - <https://owasp.org/www-project-code-review-guide/assets/OWASP_Code_Review_Guide_v2.pdf>

## Phase 2 - Correctness + security hardening

Goal: close high-blast-radius holes (public cost-bearing routes, open redirects, secrets-in-logs) and add real resource controls.

### 2.1 Lock down `/api/embeddings` (must fail closed)

- [x] (SEC-006, SEC-002) Make embeddings generation + persistence impossible without explicit auth
  - Files:
    - `src/app/api/embeddings/route.ts`
    - `src/lib/api/factory.ts` (if guardrails need new modes)
    - `src/lib/supabase/admin.ts` (if usage policy changes)
  - Steps:
    - Remove “optional auth”: if `EMBEDDINGS_API_KEY` is missing, return `503` (disabled), not “public mode”.
    - Decide the real boundary:
      - Option A: `auth: true` + per-user authorization, and remove admin writes.
      - Option B: keep internal-key auth, but make it mandatory and keep admin writes only under that key.
    - Add a test that asserts unauthenticated requests are rejected even when env is misconfigured.
  - Verify:
    - `pnpm test:affected`
    - Manual negative test: request without key returns `401/403` (or `503` when disabled).
  - Implementation notes (2025-12-17):
    - The route now returns `503` when `EMBEDDINGS_API_KEY` is missing (disabled state).
    - The route requires `x-internal-key` to match `EMBEDDINGS_API_KEY` before generating or persisting embeddings.
    - Rate limiting is configured `fail_closed` for `/api/embeddings`.
    - Tests: `src/app/api/embeddings/__tests__/route.test.ts`.
  - References:
    - <https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/>

### 2.2 Remove or hard-gate the demo LLM streaming route

- [x] (SEC-007, SEC-002) Disable `/api/ai/stream` in production, or require auth + explicit env gate
  - Files:
    - `src/app/api/ai/stream/route.ts`
  - Steps:
    - Preferred: delete the route if it’s only a demo.
    - Otherwise: require `auth: true` and an `ENABLE_AI_DEMO=true` gate; fail closed when disabled.
    - Ensure rate limiting cannot silently skip on Redis absence for this route.
  - Verify:
    - `pnpm test:affected`
    - Production config: route is unreachable unless explicitly enabled.
  - Implementation notes (2025-12-17):
    - `/api/ai/stream` now returns `404` unless `ENABLE_AI_DEMO === "true"`.
    - When enabled, it requires auth and uses fail-closed rate limiting.
    - Tests: `src/app/api/ai/stream/__tests__/route.integration.test.ts`.
  - References:
    - <https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/>

### 2.3 Protect the telemetry demo endpoint (alerts are privileged)

- [x] (SEC-009, SEC-002) Require auth/internal key for `/api/telemetry/ai-demo` and add abuse caps
  - Files:
    - `src/app/api/telemetry/ai-demo/route.ts`
  - Steps:
    - Require auth or internal key.
    - Cap `detail` length and reject oversized payloads (pair with SEC-001 fixes).
    - Ensure alert emission is deduped/rate-limited even when Redis is unavailable.
  - Verify:
    - `pnpm test:affected`
  - Implementation notes (2025-12-17):
    - `/api/telemetry/ai-demo` now returns `404` unless `ENABLE_AI_DEMO === "true"`.
    - It requires `TELEMETRY_AI_DEMO_KEY` to be configured (else `503`) and validates `x-internal-key`.
    - It enforces a small body limit (16KB) and caps `detail` length.
    - Operational alerts do **not** include raw `detail`; they emit only low-risk metadata (`has_detail`, `detail_length`).
    - `detail_hash` is an HMAC fingerprint (truncated) and is emitted only when `TELEMETRY_HASH_SECRET` is configured; otherwise it is omitted/null.
    - Rate limiting is configured `fail_closed` to prevent alert emission when limiter infra is degraded.
    - Tests: `src/app/api/telemetry/ai-demo/__tests__/route.test.ts`.

### 2.4 Fix open redirect in email confirm flow

- [x] (SEC-005) Validate/sanitize the `next` parameter in `src/app/auth/confirm/route.ts`
  - Files:
    - `src/app/auth/confirm/route.ts`
  - Steps:
    - Accept only internal relative paths; reject absolute URLs and “scheme-relative” paths.
    - Prefer allow-listing known destinations.
  - Verify:
    - `pnpm test:affected`
    - Add tests for bypass encodings: `//evil`, `%2F%2Fevil`, `\\evil`.
  - Implementation notes (2025-12-17):
    - `next` is decoded once and must be an internal path starting with `/` but not `//`; backslashes are rejected.
    - `next` is allowlisted to `/dashboard` and subpaths; other internal paths fall back to `/dashboard`.
    - Invalid `next` values fall back to `/dashboard`.
    - Tests: `src/app/auth/confirm/__tests__/route.test.ts`.
  - Follow-up (2025-12-18):
    - Centralized `next` sanitization in `src/lib/auth/confirm-next.ts` to keep allowlist policy in one place.
  - References:
    - <https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html>
    - <https://nextjs.org/docs/app/api-reference/functions/redirect>

### 2.5 Enforce hard request body limits before parsing

- [x] (SEC-001) Add bounded body readers for JSON and webhook verification
  - Files:
    - `src/lib/api/route-helpers.ts`
    - `src/lib/api/factory.ts`
    - `src/lib/webhooks/payload.ts`
    - `src/lib/webhooks/handler.ts`
  - Steps:
    - Implement a shared “read body with limit” helper used by both JSON routes and webhook verification.
    - Return `413 Payload Too Large` when exceeded, before attempting `req.json()` / `req.text()`.
    - Delete size checks that occur after parsing (they are placebo).
  - Verify:
    - `pnpm test:affected`
    - Add tests that simulate oversized payloads and assert 413 without buffering full body.
  - Implementation note (2025-12-17):
    - Added `readRequestBodyBytesWithLimit()` (`src/lib/http/body.ts`) and wired it into:
      - `parseJsonBody()` (`src/lib/api/route-helpers.ts`) for bounded JSON parsing (no `req.json()`/`req.text()`).
      - Webhook HMAC verification (`src/lib/webhooks/payload.ts`) and QStash verification (`src/lib/qstash/receiver.ts`) for raw-body validation.
      - Auth JSON routes under `src/app/auth/**` (email verify + password flows) now parse via the bounded reader and return `413` on exceed.
    - Removed redundant post-parse `Content-Length` checks where present (e.g., `/api/keys`) now that parsing is bounded pre-parse.
    - Representative tests cover 413 behavior for JSON parsing and webhook/QStash verification.
  - Follow-up (2025-12-18):
    - Added a clear `400 invalid_request` path when a request body is already consumed (prevents ambiguous second-read errors).
    - Refactored auth JSON routes to call `parseJsonBody()` directly to standardize bounded parsing behavior.
  - References:
    - <https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/>

### 2.6 Make rate limiting/idempotency policy explicit and safe under degraded infra

- [x] (SEC-002) Introduce explicit fail-open/fail-closed modes per endpoint class
  - Files:
    - `src/lib/api/factory.ts`
    - `src/lib/webhooks/rate-limit.ts`
    - `src/lib/idempotency/redis.ts`
  - Steps:
    - Make “fail open” an opt-in, not a silent default for privileged/cost-bearing endpoints.
    - Emit operational alerts when falling back to fail-open.
    - Apply fail-closed to at least: auth endpoints, key management, webhooks/jobs, embeddings/LLM routes.
  - Verify:
    - `pnpm test:affected`
  - Implementation notes (2025-12-17):
    - `withApiGuards` supports `degradedMode: "fail_closed" | "fail_open"`; privileged/cost-bearing routes default to `fail_closed`.
    - `fail_open` fallbacks emit a deduped operational alert (`ratelimit.degraded`, `idempotency.degraded`).
    - Degraded-mode alerts use low-cardinality attributes (no full request path) and the dedupe map is periodically cleaned up to avoid unbounded growth (`src/lib/telemetry/degraded-mode.ts`).
    - Tests: `src/lib/api/__tests__/factory.degraded-mode.test.ts`.
  - Follow-up (2025-12-18):
    - Added `maxBodyBytes` override to `withApiGuards` schema parsing to avoid bespoke parsing code for smaller body caps.
    - Added fail-closed rate limiting to `POST /auth/password/reset-request` to reduce password-reset email spam risk under normal and degraded conditions.

### 2.7 Remove secrets-in-logs for QStash

- [x] (SEC-003) Stop logging the raw QStash signature header
  - Files:
    - `src/lib/qstash/receiver.ts`
  - Steps:
    - Delete signature logging; optionally log a short hash prefix if correlation is required.
  - Verify:
    - `pnpm test:affected`
  - References:
    - <https://upstash.com/docs/qstash/howto/signature>

### 2.8 Stop emitting raw user/session identifiers into telemetry by default

- [x] (SEC-004) Add telemetry-safe identifier helpers and apply in memory-sync job
  - Files:
    - `src/app/api/jobs/memory-sync/route.ts`
    - `src/lib/telemetry/**` (new helper module if needed)
  - Steps:
    - Hash/redact identifiers at the edge; keep raw IDs out of spans/events by default.
    - Document a minimal “telemetry data classification” policy in `docs/`.
  - Verify:
    - `pnpm test:affected`
  - Implementation notes (2025-12-17):
    - Added `hashTelemetryIdentifier()` (`src/lib/telemetry/identifiers.ts`) using `TELEMETRY_HASH_SECRET`; safe default is to omit identifiers when unset.
    - Memory sync job now emits `user.id_hash` / `session.id_hash` only and avoids embedding raw identifiers in exception messages.
    - Additional spans emitting user/session identifiers were migrated to hashed/omitted forms:
      - `src/lib/supabase/factory.ts`
      - `src/app/api/keys/_telemetry.ts`
      - `src/lib/security/sessions.ts`
      - `src/app/api/security/sessions/_handlers.ts`
      - `src/app/api/itineraries/_handler.ts`
      - `src/lib/memory/orchestrator.ts`
      - `src/domain/accommodations/providers/amadeus-adapter.ts`
    - API factory now records a stable, low-cardinality `routeKey` for metrics/spans (telemetry name or rateLimit key, else sanitized path) to avoid emitting raw dynamic paths containing IDs.
    - Documented policy in `docs/development/security/telemetry-data-classification.md`.

### 2.9 Fix `dangerouslyAllowSVG` configuration

- [x] (SEC-008) Disable SVG serving through image optimization unless strictly required
  - Files:
    - `next.config.ts`
  - Steps:
    - Preferred: set `dangerouslyAllowSVG: false`.
    - If required: add `contentDispositionType: \"attachment\"` and keep strict CSP; also restrict sources.
  - Verify:
    - `pnpm build`
  - Implementation notes (2025-12-17):
    - `next.config.ts` now sets `images.dangerouslyAllowSVG = false`.
  - References:
    - <https://nextjs.org/docs/app/api-reference/components/image#dangerouslyallowsvg>
    - <https://vercel.com/docs/conformance/rules/NEXTJS_SAFE_SVG_IMAGES>

## Phase 3 - Performance + reliability

Goal: remove internal loopback calls, fix schema/runtime contract mismatches, and reduce pointless failure modes.

### 3.1 Remove loopback HTTP fetch for ICS generation

- [x] (REL-002) Extract a shared ICS generator and call it directly from both tool + route
  - Files:
    - `src/ai/tools/server/calendar.ts`
    - `src/app/api/calendar/ics/export/route.ts`
    - `src/lib/calendar/ics.ts` (new)
    - `src/lib/calendar/__tests__/ics.test.ts` (new)
  - Implementation notes:
    - Created `generateIcsFromEvents()` pure function in `src/lib/calendar/ics.ts`
    - Extracted `eventAttendeeStatusToIcal()` and `reminderMethodToIcal()` helpers
    - Route handler now imports and uses shared generator
    - AI tool now calls generator directly (removed `fetch()` and `NEXT_PUBLIC_SITE_URL` usage)
    - Added comprehensive unit tests (24 tests covering attendees, reminders, recurrence, metadata)
  - Verify:
    - `pnpm test:affected` ✓
    - `pnpm type-check` ✓
  - References:
    - <https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html>

### 3.2 Fix attachments list schema/handler contract mismatch

- [x] (REL-003) Decide and enforce the contract for attachment `url`
  - Files:
    - `src/app/api/attachments/files/route.ts`
    - `src/app/api/attachments/files/__tests__/route.test.ts`
    - `src/domain/schemas/attachments.ts` (unchanged - schema remains strict)
  - Decision: **Option C** - filter out items with missing URLs
  - Implementation notes:
    - Schema keeps `url: z.url()` as required (non-nullable)
    - Handler now filters out items where signed URL generation fails
    - Added warning log when items are dropped (logs count only, no PII)
    - Pagination `total` still reflects DB count for cursor math
    - Updated tests: complete URL generation failure → empty items array
    - Added new test for partial URL generation failure (one succeeds, one fails)
  - Verify:
    - `pnpm test:affected` ✓
    - `pnpm type-check` ✓
  - References:
    - <https://zod.dev/v4>

## Phase 4 - DX + tooling + long-term guardrails

Goal: enforce boundaries and conventions so the same classes of bugs don’t return.

### 4.1 Enforce layering boundaries (beyond client/server)

- [x] (ARCH-001) Define a 1-page layering policy and enforce it in CI
  - Files:
    - `docs/development/standards/standards.md` (or a new architecture policy doc)
    - `scripts/check-boundaries.mjs`
  - Steps:
    - Define allowed dependency directions (domain, lib/infra, app, ai).
    - Extend boundary checker to prevent the highest-risk import directions (domain → app/next, client → server-only).
    - Keep the initial rule-set small and high-signal; track legacy violations explicitly.
  - Verify:
    - `pnpm boundary:check`
  - Implementation notes (2025-12-19):
    - Added `docs/development/architecture/layering.md` and linked it from `standards.md` and `docs/development/README.md`.
    - Extended `scripts/check-boundaries.mjs` to block domain → app/next imports with an explicit allowlist.
    - Normalized allowlist path handling in `scripts/check-boundaries.mjs` for Windows compatibility.
    - CI now runs `pnpm boundary:check`.

### 4.2 Make `createAiTool` mandatory for server tools

- [x] (ARCH-002) Migrate `getTravelAdvisory` off raw `tool()` and onto `createAiTool`
  - Files:
    - `src/ai/tools/server/travel-advisory.ts`
    - `src/ai/lib/tool-factory.ts` (if guardrails need enhancements)
  - Steps:
    - Convert tool definition to `createAiTool` and encode caching/rateLimit/telemetry via guardrails.
    - Consider a lint rule or test that rejects raw `tool()` exports under `src/ai/tools/server/*`.
  - Verify:
    - `pnpm test:affected`
    - `pnpm ai-tools:check`
  - Implementation notes (2025-12-19):
    - Migrated `getTravelAdvisory` to `createAiTool` with cache + rate limit + telemetry guardrails.
    - Added `scripts/check-ai-tools.mjs` and CI step to block raw `tool()` usage in server tools.
    - Updated AI tools docs and frontend architecture docs to reflect the enforcement rule.
    - Migrated `web-crawl` and `web-search-batch` to `createAiTool`; removed allowlisted raw `tool()` exceptions.
    - Normalized allowlist path handling in `scripts/check-ai-tools.mjs` for Windows compatibility.
    - Avoided mutating cache-key inputs in `web-crawl` by sorting copies.
    - Updated Maps tools to drop legacy Distance Matrix output, added output schemas/validation, and added `maps` tool unit tests.
    - Added output schemas + validation across remaining server tools (calendar, memory, planning, rag, weather, flights, activities, google-places, web-crawl).
    - Updated travel advisory safety score schema to 0–100 and added tool output schema validation.
    - Removed unused `src/ai/tools/schemas/memory.ts` duplicate.
    - Added output validation for the memory-agent tool wrapper and tests covering `createAiTool` output schema enforcement.
  - References:
    - <https://github.com/vercel/ai/blob/ai@6.0.0-beta.128/content/docs/02-foundations/04-tools.mdx>

### 4.3 Break the AI core circular dependency

- [x] (ARCH-003) Extract instruction-normalization helpers into a leaf module
  - Files:
    - `src/ai/agents/chat-agent.ts`
    - `src/ai/agents/agent-factory.ts`
    - New helper module (suggested): `src/ai/agents/instructions.ts`
  - Steps:
    - Move `extractTextFromContent` and `normalizeInstructions` into the helper.
    - Make `agent-factory` import only the helper, not `chat-agent`.
    - Add a lightweight “no cycles” check (even a simple `madge`-style script or a local `node` graph walk) for `src/ai/agents/*`.
  - Verify:
    - `pnpm test:affected`
    - `pnpm type-check`
    - `pnpm deps:cycles`
  - Implementation notes (2025-12-19):
    - Extracted instruction helpers to `src/ai/agents/instructions.ts`.
    - Added `madge` + `pnpm deps:cycles` and wired it into CI.
    - Re-sanitized `prepareCall` instruction overrides in `agent-factory` to prevent prompt-injection bypass.
  - References:
    - <https://nodejs.org/api/modules.html#cycles>

### 4.4 Raise meaningful test coverage where it matters

- [x] (SEC-006, SEC-001, SEC-002, SEC-005, SEC-007, SEC-009) Add security regression tests for the highest-risk surfaces
  - Target behaviors to test (minimum set):
    - Embeddings route rejects unauthenticated/misconfigured access.
    - Body-size limiting returns 413 without buffering.
    - Rate limiting fail-closed for privileged/cost-bearing endpoints under Redis outage simulation.
    - Open redirect sanitization.
  - Verify:
    - `pnpm test:affected`
  - Implementation notes (2025-12-17):
    - Added/updated tests for embeddings gating, AI demo gating/auth, telemetry internal-key gating, bounded body reads, degraded-mode behavior, and open-redirect sanitization.
