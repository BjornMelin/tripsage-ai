# Codebase Review Log - 2025-12-15

## Repo snapshot

- Date (local): 2025-12-15
- Branch: main
- Commit: 3045db885a77976321410dd846502d480fa98372
- Reviewer model: GPT-5.2 x-high (Codex)
- Scope: whole repository
- Constraints: audit-only (no source changes)

## Executive summary (fill at end)

- Blockers: 1
- Critical: 2
- Major: 13
- Minor: 7
- Nits: 0
- Top risks (highest first):
  1) Production build is currently broken (REL-001) and CI doesn’t run `pnpm build` (DX-002) → easy to ship deploy-breaking changes.
  2) `/api/embeddings` can become fully public if `EMBEDDINGS_API_KEY` is unset and writes with admin Supabase (SEC-006) → cost + data poisoning.
  3) Public `/api/ai/stream` demo uses server OpenAI key (SEC-007) + rate limit can fail-open (SEC-002) → cost/abuse vector.
  4) Missing hard request body size limits before parsing (SEC-001) → trivial DoS via oversized JSON/webhook payloads.
  5) Open redirect in email confirm flow (`next` param) (SEC-005) → phishing amplification on a trust-heavy route.
  6) `dangerouslyAllowSVG: true` in `next/image` config (SEC-008) → XSS footgun if SVGs ever enter the pipeline.
  7) Rate limiting/idempotency defaults fail-open under Redis outage/misconfig (SEC-002) → abuse/cost spikes when infra is degraded.
  8) Schema contract mismatch: attachments list schema requires `url`, handler can return `null` (REL-003) → runtime/client breakage in error paths.
  9) AI core has a circular dependency (`chat-agent` ↔ `agent-factory`) (ARCH-003) → refactor hazard + potential init-order bugs.
  10) QStash signature header logged on verification failure (SEC-003) → secrets-in-logs boundary expansion.

## Inventory (fill during discovery)

- Languages: TypeScript, JavaScript (mjs), CSS (Tailwind), Markdown, YAML, SQL (Supabase), Shell/Make
- Frameworks: Next.js 16 (App Router), React 19, Tailwind CSS, Radix UI, Vercel AI SDK v6, Supabase SSR, Upstash
- Build/test tooling: pnpm, Biome, TypeScript (`tsc`), Vitest, Playwright, Next build, semantic-release
- Key domains (auth, payments, data ingestion, AI/ML, etc.): Auth/session (Supabase), AI chat/agents/tools, travel APIs (Amadeus), payments (Stripe), email (Resend), telemetry (OpenTelemetry/Vercel OTEL), rate limiting + background jobs (Upstash)
- High-risk surfaces: `src/app/api/**` route handlers, server actions (`src/**/actions.ts`), Supabase policies/migrations (`supabase/**`), webhook-like handlers (Stripe/Resend/QStash), file ingestion/upload endpoints, env/config handling
- Top-level layout: `src/` (Next app + core logic), `supabase/` (schema+migrations), `e2e/` (Playwright), `docs/` (product/engineering docs), `scripts/` (automation), `docker/` (containerization), `.github/` (CI)

## Findings index (keep updated)

| ID | Severity | Category | Title | Paths |
|---|---|---|---|---|
| REL-001 | Blocker | Reliability | `pnpm build` fails (Turbopack) on `activities/actions.ts` server-action module | `src/app/dashboard/search/activities/*` |
| DX-001 | Major | DX | Turbopack externalization warnings for OpenTelemetry deps with pnpm (missing root install) | `src/instrumentation.ts`, `package.json` |
| TEST-001 | Major | Testing | Coverage thresholds appear non-functional; actual global coverage ~49–55% | `vitest.config.ts` |
| DX-002 | Major | DX | CI doesn’t run `pnpm build`, so Next/Turbopack regressions can ship | `.github/workflows/ci.yml` |
| ARCH-001 | Major | Architecture | Layering is not enforced; `src/lib` is a coupling hotspot and “domain” depends heavily on infra | `src/lib/**`, `src/domain/**` |
| AI-001 | Minor | AI-Slop | Misleading docs + naming collisions in Supabase factory (“cookies optional” vs tests requiring adapter) | `src/lib/supabase/factory.ts`, `src/lib/supabase/server.ts` |
| SEC-001 | Critical | Security | No real request body size enforcement before JSON parsing (DoS risk) | `src/lib/api/*`, `src/app/api/*`, `src/lib/webhooks/*` |
| SEC-002 | Major | Security | Rate limiting + idempotency fail-open by default (abuse/DoS + duplicates) | `src/lib/api/factory.ts`, `src/lib/webhooks/rate-limit.ts`, `src/lib/idempotency/redis.ts` |
| SEC-003 | Major | Security | QStash signature header logged on verification failure | `src/lib/qstash/receiver.ts` |
| SEC-004 | Minor | Security | Raw user/session identifiers recorded in telemetry attributes | `src/app/api/jobs/memory-sync/route.ts` |
| AI-002 | Minor | AI-Slop | Template-style `@fileoverview` + doc bloat across most files (drift/noise) | `src/**` |
| AI-003 | Minor | AI-Slop | Heuristic error classification in webhook handler (message-based status mapping) | `src/lib/webhooks/handler.ts` |
| AI-004 | Major | AI-Slop | Excessive `as unknown as` casts in production code (type-safety bypass) | `src/**` |
| DX-003 | Minor | DX | `turbopack.root` configured as relative path (build warning noise) | `next.config.ts` |
| ARCH-002 | Minor | Architecture | AI tool guardrails bypassed: some tools use raw `tool()` instead of `createAiTool` | `src/ai/tools/server/travel-advisory.ts` |
| REL-002 | Major | Reliability | AI tool uses loopback fetch to authenticated ICS export route (likely 401) | `src/ai/tools/server/calendar.ts`, `src/app/api/calendar/ics/export/route.ts` |
| SEC-005 | Major | Security | Open redirect in auth confirm route via unvalidated `next` param | `src/app/auth/confirm/route.ts` |
| SEC-006 | Critical | Security | Embeddings endpoint can be public + writes via admin Supabase when internal key missing | `src/app/api/embeddings/route.ts` |
| SEC-007 | Major | Security | Public `/api/ai/stream` uses server OpenAI key (cost/abuse vector) | `src/app/api/ai/stream/route.ts` |
| SEC-008 | Major | Security | `images.dangerouslyAllowSVG: true` enabled (XSS footgun) | `next.config.ts` |
| SEC-009 | Minor | Security | Auth-less telemetry endpoint can spam operational alerts | `src/app/api/telemetry/ai-demo/route.ts` |
| REL-003 | Major | Correctness | Attachments list schema/handler mismatch: `url` is required by schema but can be `null` | `src/app/api/attachments/files/route.ts`, `src/domain/schemas/attachments.ts` |
| ARCH-003 | Major | Architecture | Circular dependency between `chat-agent` and `agent-factory` in core AI layer | `src/ai/agents/chat-agent.ts`, `src/ai/agents/agent-factory.ts` |

## Findings (append as you go)

### REL-001 - Blocker - Reliability - `pnpm build` fails (Turbopack) on `activities/actions.ts` server-action module

**Paths:**  

- `src/app/dashboard/search/activities/actions.ts`  
- `src/app/dashboard/search/activities/activities-search-client.tsx`  
- `src/app/dashboard/search/activities/page.tsx`

**AI-slop suspected:** No

**Evidence:**  

- Symbols: `ActivitySearchValidationError`, `submitActivitySearch`, `getPlanningTrips`, `addActivityToTrip`  
- What I observed: Running `pnpm build` fails with Turbopack reporting an error in `src/app/dashboard/search/activities/actions.ts` at `export class ActivitySearchValidationError extends Error`, followed by “module has no exports” / missing export errors for `getPlanningTrips` and `submitActivitySearch` when imported from Client/RSC modules.

**Impact / Risk:**  

- Production builds fail → deploy/release is blocked.  
- `pnpm type-check` and `pnpm test:quick` can still pass while `next build` fails, so CI can be green while deployment is broken (see DX-002).

**Recommendation (preferred order):**  

1) Delete/simplify: remove non-action exports from `"use server"` modules (start by moving `ActivitySearchValidationError` out of `actions.ts` or replacing it with a plain `Error`/structured return).  
2) Refactor: keep `actions.ts` as “server actions only” (exported async functions) and move shared types/errors/utilities to non-action modules imported by both server/client as needed.  
3) Replace with library-native approach: follow Next.js Server Actions module rules (documented in Next.js official docs; cite specific path in implementation guide).

**Acceptance criteria:**

- [x] `pnpm build` succeeds on a clean checkout without modifying lockfiles.
- [x] `pnpm type-check` succeeds.
- [x] `pnpm test:quick` (and ideally `pnpm test`) succeeds.

**References:**  

- <https://nextjs.org/docs/app/api-reference/directives/use-server>  
- <https://react.dev/reference/rsc/use-server>

### DX-001 - Major - DX - Turbopack externalization warnings for OpenTelemetry deps with pnpm (missing root install)

**Paths:**  

- `src/instrumentation.ts`  
- `package.json`

**AI-slop suspected:** No

**Evidence:**  

- Symbols: `registerOTel` (`src/instrumentation.ts`)  
- What I observed: `pnpm build` emits Turbopack warnings that `import-in-the-middle` and `require-in-the-middle` “match serverExternalPackages” but “could not be resolved by Node.js from the project directory,” recommending installing them at the project root. `@opentelemetry/instrumentation` declares both as dependencies, but pnpm doesn’t place transitive deps at `node_modules/<pkg>` unless they’re direct deps, so runtime resolution from `.next/server` can fail.

**Impact / Risk:**  

- Build output includes warnings that commonly correlate with runtime “Cannot find module …” crashes in server output (pnpm + externalized packages).  
- Telemetry/instrumentation becomes fragile: either broken at runtime or dependent on non-obvious deployment packaging behavior.

**Recommendation (preferred order):**  

1) Delete/simplify: don’t fight Turbopack’s externalization model with custom hacks; align deps with what the bundler expects.  
2) Refactor: add `import-in-the-middle` and `require-in-the-middle` as direct dependencies if you rely on `@vercel/otel`/OTEL instrumentation that pulls them in.  
3) Replace with library-native approach: follow Next.js + Vercel OTEL guidance for server externals / instrumentation on pnpm (cite docs/issue references in implementation guide).

**Acceptance criteria:**

- [x] `node -e \"require.resolve('import-in-the-middle'); require.resolve('require-in-the-middle')\"` succeeds from repo root.
- [x] `pnpm build` (after REL-001 is fixed) emits zero warnings about these packages not being resolvable.
- [ ] A production run (`pnpm start` after build) does not crash on module resolution during instrumentation init.

**References:**  

- <https://nextjs.org/docs/app/api-reference/config/next-config-js/serverExternalPackages>  
- <https://nextjs.org/docs/app/guides/open-telemetry>  
- <https://www.npmjs.com/package/@vercel/otel>

### TEST-001 - Major - Testing - Coverage thresholds appear non-functional; actual global coverage ~49–55%

**Paths:**  

- `vitest.config.ts`

**AI-slop suspected:** No

**Evidence:**  

- Symbols: `coverage.thresholds.global` in Vitest config  
- What I observed:
  - `vitest.config.ts` declares strict global coverage thresholds (branches 85%, functions/lines/statements 90%).  
  - Running `CI=1 pnpm exec vitest run --coverage.enabled --coverage.reporter=text-summary --coverage.provider=v8` reports global coverage far below the thresholds (Statements ~49%, Branches ~36%, Functions ~55%, Lines ~49%) **but exits 0**.  
  - Vitest v4 docs describe `coverage.thresholds.<lines|functions|branches|statements>` (no `global` nesting), suggesting this config shape is being ignored rather than enforced.

**Impact / Risk:**  

- Coverage gating is effectively off → you can merge large untested surfaces while believing you’re protected by thresholds.  
- The gap between “declared” (85–90%) and “actual” (~36–55%) is large enough that it will surprise maintainers the moment enforcement is fixed.

**Recommendation (preferred order):**  

1) Delete/simplify: remove misleading thresholds if you’re not prepared to enforce them soon (they create false confidence).  
2) Refactor: fix the Vitest v4 coverage configuration so thresholds are actually enforced (use the documented `coverage.thresholds.<...>` keys), then explicitly decide scope (global vs per-project vs “critical packages only”).  
3) Replace with library-native approach: follow Vitest v4 coverage threshold configuration exactly (cite official docs in implementation guide).

**Acceptance criteria:**

- [x] A deliberate "bad coverage" run fails: `pnpm test:coverage` (or equivalent) exits non-zero when coverage is below thresholds.
- [ ] The chosen enforcement strategy is documented (global/per-directory thresholds + excludes) and matches the actual numbers.
- [ ] Coverage on critical surfaces (auth, payments, keys, webhooks, AI tool routing) has explicit targets and is measured.

**References:**  

- <https://github.com/vitest-dev/vitest/blob/v4.0.7/docs/config/index.md>  
- <https://github.com/vitest-dev/vitest/blob/v4.0.7/docs/guide/coverage.md>

### DX-002 - Major - DX - CI doesn’t run `pnpm build`, so Next/Turbopack regressions can ship

**Paths:**  

- `.github/workflows/ci.yml`

**AI-slop suspected:** No

**Evidence:**  

- Symbols: `jobs.frontend.steps` in `.github/workflows/ci.yml`  
- What I observed: CI runs `pnpm biome:check`, `pnpm type-check`, and `pnpm test:quick` but does **not** run `pnpm build`/`next build`. This allows Next-specific build constraints to break production while CI stays green (REL-001 is a live example).

**Impact / Risk:**  

- Production-only failures slip through (Server Actions rules, RSC/client boundaries, Turbopack externals, Next build-time transforms).  
- Developers get a false “green” signal and only discover failures at deploy time.

**Recommendation (preferred order):**  

1) Delete/simplify: remove any “green CI == deploy-safe” assumptions if build isn’t checked.  
2) Refactor: add a CI step/job that runs `pnpm build` with production-equivalent config (same Node/pnpm versions, same Next config, same runtime flags).  
3) Replace with library-native approach: follow Next.js recommended CI checks for App Router + Turbopack (cite docs in implementation guide).

**Acceptance criteria:**

- [x] CI runs `pnpm build` on PRs that touch `src/**`, `next.config.ts`, or build-affecting config.
- [x] `pnpm build` failures (like REL-001) fail the CI workflow.
- [x] Any required env vars for build are stubbed safely (no secrets) and documented.

**References:**  

- <https://nextjs.org/docs/app/guides/ci-build-caching>

### ARCH-001 - Major - Architecture - Layering is not enforced; `src/lib` is a coupling hotspot and “domain” depends heavily on infra

**Paths:**  

- `src/lib/**`  
- `src/domain/**`

**AI-slop suspected:** Yes (Confidence: Med)

**Evidence:**  

- Symbols: multiple “platform” concerns live under `src/lib/*` (Supabase, Upstash, telemetry, env, payments, caching, security), and `src/domain/**` imports them directly.  
- What I observed:
  - `src/lib` contains ~188 TS/TSX files and spans infra + domain-adjacent logic.  
  - `src/domain/**` frequently imports `@/lib/*` (e.g., `src/domain/accommodations/service.ts` imports caching, Google enrichment, retry, payments, security random, Supabase, telemetry).  
  - The only automated boundary check is client/server (no `domain`/`app` layering enforcement).

**Impact / Risk:**  

- High coupling makes refactors expensive and increases blast radius of “small” changes.  
- “Where should this live?” decisions become arbitrary → duplication and wrapper sprawl (classic AI-slop attractor).  
- Future extraction (e.g., moving domain services into a separate package/worker) becomes harder.

**Recommendation (preferred order):**  

1) Delete/simplify: prune redundant pass-through helpers and “utility” layers that exist solely to wrap another helper; keep one canonical abstraction per concern.  
2) Refactor: define explicit dependency direction rules (e.g., domain → platform, app → domain/platform; never app imported by domain). Enforce with a lightweight boundary checker (extend `scripts/check-boundaries.mjs` or add a dedicated architecture boundary script).  
3) Replace with library-native approach: where wrappers duplicate upstream SDK features (retry, caching, request signing), prefer upstream defaults unless there’s a concrete need.

**Acceptance criteria:**  

- [ ] A documented layering policy exists (1 page) with allowed import directions and examples.  
- [ ] A CI boundary check fails on disallowed imports (at minimum: `src/domain/**` importing `src/app/**` or `next/*`, and client components importing server-only modules).  
- [ ] New code follows the boundary rules; legacy violations are tracked with explicit TODOs and a burn-down plan.

**References:**  

- <https://abseil.io/resources/swe-book/html/ch09.html>  
- <https://google.github.io/eng-practices/review/reviewer/standard.html>

### AI-001 - Minor - AI-Slop - Misleading docs + naming collisions in Supabase factory (“cookies optional” vs tests requiring adapter)

**Paths:**  

- `src/lib/supabase/factory.ts`  
- `src/lib/supabase/server.ts`  
- `src/lib/supabase/__tests__/factory.spec.ts`

**AI-slop suspected:** Yes (Confidence: High)

**Evidence:**  

- Symbols: `CreateServerSupabaseOptions` docs + `createServerSupabase()` in `src/lib/supabase/factory.ts`; `createServerSupabase()` in `src/lib/supabase/server.ts`  
- What I observed:
  - `CreateServerSupabaseOptions.cookies` is documented as optional (“If not provided, will use Next.js cookies() by default”), but `src/lib/supabase/__tests__/factory.spec.ts` explicitly asserts it throws when the adapter is not provided.  
  - Two different exports share the same name `createServerSupabase`: an async wrapper in `server.ts` and a sync factory in `factory.ts`, increasing the odds of importing the wrong one.  
  - The file is comment-heavy with tutorial-style docstrings that contradict runtime behavior (a common LLM-shaped smell: “docs first, behavior second”).

**Impact / Risk:**  

- Future maintainers can accidentally import the wrong `createServerSupabase` and trigger runtime failures that are hard to diagnose.  
- Documentation drift increases “cargo-cult” edits and makes auth/session flows riskier to change.

**Recommendation (preferred order):**  

1) Delete/simplify: delete misleading doc blocks and incorrect examples; keep only what’s true.  
2) Refactor: rename the lower-level factory export to avoid collision (e.g., `createServerSupabaseClient`), and make the async wrapper in `server.ts` the only “public” entrypoint used by app code.  
3) Replace with library-native approach: align with Supabase SSR guidance for Next.js (cite official docs in implementation guide).

**Acceptance criteria:**  

- [ ] There is exactly one recommended import path for server Supabase creation (documented in `docs/`).  
- [ ] Docs/tests agree on whether a cookie adapter is required.  
- [ ] “Wrong import” is prevented by lint rule or by removing/restricting the confusing export surface.

**References:**  

- <https://supabase.com/docs/guides/auth/server-side/creating-a-client>

### SEC-001 - Critical - Security - No real request body size enforcement before JSON parsing (DoS risk)

**Paths:**  

- `src/lib/api/route-helpers.ts`  
- `src/lib/api/factory.ts`  
- `src/app/api/keys/route.ts`  
- `src/lib/webhooks/handler.ts`  
- `src/lib/webhooks/payload.ts`

**AI-slop suspected:** Yes (Confidence: Med)

**Evidence:**  

- Symbols: `API_CONSTANTS.maxBodySizeBytes`, `parseJsonBody()`, `withApiGuards()`  
- What I observed:
  - `src/lib/api/route-helpers.ts` defines `API_CONSTANTS.maxBodySizeBytes` but `parseJsonBody()` calls `req.json()` with no size enforcement.  
  - `withApiGuards()` parses JSON when `schema` is provided; there’s no central max-size guard before parsing.  
  - `src/app/api/keys/route.ts` checks `Content-Length` **after** `withApiGuards` parsed JSON (explicitly noted in comments), so it can’t prevent memory exhaustion.  
  - `src/lib/webhooks/handler.ts` checks `Content-Length` before `parseAndVerify(req)`, but if the header is missing/incorrect, `parseAndVerify` still reads the full body via `req.text()`.

**Impact / Risk:**  

- Remote clients can send oversized JSON/webhook payloads and force full-body buffering, causing memory exhaustion / function crashes / latency spikes (DoS vector).  
- High-risk endpoints (keys/webhooks/jobs) are the most likely to be targeted.

**Recommendation (preferred order):**  

1) Delete/simplify: remove “defense-in-depth” size checks that run after parsing; they add code but don’t provide the intended protection.  
2) Refactor: enforce a hard maximum *before* reading/parsing bodies in `withApiGuards` (and in webhook signature verification) using a bounded reader; return `413 Payload Too Large` on exceed.  
3) Replace with library-native approach: use Next.js-supported patterns for raw body access + size limiting (cite docs in implementation guide).

**Acceptance criteria:**  

- [ ] Oversized JSON requests to guarded routes return `413` without fully buffering the payload.  
- [ ] Webhook signature verification reads the body with a hard limit (not just `Content-Length`), returning `413` when exceeded.  
- [ ] Tests cover the size limit behavior for at least one JSON route and one webhook route.

**References:**  

- <https://owasp.org/www-project-code-review-guide/assets/OWASP_Code_Review_Guide_v2.pdf>  
- <https://cheatsheetseries.owasp.org/cheatsheets/Secure_Code_Review_Cheat_Sheet.html>

### SEC-002 - Major - Security - Rate limiting + idempotency fail-open by default (abuse/DoS + duplicates)

**Paths:**  

- `src/lib/api/factory.ts`  
- `src/lib/webhooks/rate-limit.ts`  
- `src/lib/idempotency/redis.ts`

**AI-slop suspected:** No

**Evidence:**  

- Symbols: `enforceRateLimit()`, `checkWebhookRateLimit()`, `tryReserveKey()`  
- What I observed:
  - Route rate limiting disables itself when Redis is unavailable or limiter errors occur (`enforceRateLimit` returns `null` on failure).  
  - Webhook rate limiting explicitly “fails open” when Redis isn’t configured.  
  - Idempotency defaults to “fail open” unless `IDEMPOTENCY_FAIL_OPEN=false`.

**Impact / Risk:**  

- During Redis outages/misconfig, attacker traffic is effectively unlimited → higher DoS/cost risk.  
- Duplicate processing becomes likely for webhooks/jobs, which can amplify side effects (emails, writes, background jobs).

**Recommendation (preferred order):**  

1) Delete/simplify: stop treating fail-open as a silent default; make it an explicit policy decision per route class (public endpoints vs internal webhooks/jobs).  
2) Refactor: add per-route/per-handler configuration for fail-open vs fail-closed, and emit operational alerts when falling back to fail-open (not just logs).  
3) Replace with library-native approach: where possible, rely on upstream platform protections for public routes, and enforce strict signature-based auth + fail-closed for internal webhooks/jobs.

**Acceptance criteria:**  

- [ ] Critical endpoints (webhooks, jobs, keys) have an explicit fail-closed mode when Redis is unavailable.  
- [ ] Fail-open incidents emit an operational alert with route/feature context.  
- [ ] Tests cover both modes (redis available vs unavailable) for one representative route/handler.

**References:**  

- <https://owasp.org/www-project-code-review-guide/assets/OWASP_Code_Review_Guide_v2.pdf>  
- <https://cheatsheetseries.owasp.org/cheatsheets/Secure_Code_Review_Cheat_Sheet.html>

### SEC-003 - Major - Security - QStash signature header logged on verification failure

**Paths:**  

- `src/lib/qstash/receiver.ts`

**AI-slop suspected:** No

**Evidence:**  

- Symbols: `verifyQstashRequest()`  
- What I observed: On verification errors, the logger logs `{ signature, url }`. The signature header is security-sensitive and does not need to appear in logs for debugging.

**Impact / Risk:**  

- Log exposure becomes a security boundary: anyone with log access can see the raw signature value.  
- In incident response, logs are often broadly accessed and retained; sensitive headers should be treated as secrets.

**Recommendation (preferred order):**  

1) Delete/simplify: remove signature logging entirely.  
2) Refactor: if you need correlation, log a short fingerprint (e.g., first 8 chars of a hash) rather than the raw header value.  
3) Replace with library-native approach: follow Upstash signature verification guidance without logging secrets (cite docs in implementation guide).

**Acceptance criteria:**  

- [ ] No logs contain the raw QStash signature header.  
- [ ] A failing signature verification still produces enough context to debug (route + reason + request id).  
- [ ] Tests/linters prevent reintroducing raw secret logging.

**References:**  

- <https://upstash.com/docs/qstash/howto/signature-validation>

### SEC-004 - Minor - Security - Raw user/session identifiers recorded in telemetry attributes

**Paths:**  

- `src/app/api/jobs/memory-sync/route.ts`

**AI-slop suspected:** No

**Evidence:**  

- Symbols: `span.setAttribute(\"user.id\", payload.userId)`, `span.setAttribute(\"session.id\", payload.sessionId)`  
- What I observed: The memory sync job records user and session identifiers as raw telemetry attributes. In other parts of the codebase (e.g., Supabase factory), user ids are intentionally redacted.

**Impact / Risk:**  

- PII/identifier leakage to telemetry backends and third-party processors.  
- Inconsistent privacy posture → engineers won’t know what’s safe to log.

**Recommendation (preferred order):**  

1) Delete/simplify: avoid emitting raw identifiers by default.  
2) Refactor: centralize “telemetry-safe identifier” helpers (hashing/redaction) and apply consistently across spans/events.  
3) Replace with library-native approach: adopt a documented data classification policy for telemetry attributes (cite in implementation guide).

**Acceptance criteria:**  

- [ ] No new telemetry spans record raw user/session identifiers without explicit justification.  
- [ ] Existing span attributes are migrated to hashed/redacted forms.  
- [ ] A documented policy exists for what identifiers can be emitted (and where).

**References:**  

- <https://owasp.org/www-project-code-review-guide/assets/OWASP_Code_Review_Guide_v2.pdf>

### DX-003 - Minor - DX - `turbopack.root` configured as relative path (build warning noise)

**Paths:**  

- `next.config.ts`

**AI-slop suspected:** No

**Evidence:**  

- Symbols: `nextConfig.turbopack.root`  
- What I observed:
  - `next.config.ts` sets `turbopack: { root: "." }`.  
  - `pnpm build` prints: `turbopack.root should be absolute` and then falls back to an absolute path.  
  - Next.js docs explicitly state `turbopack.root` “should be an absolute path”.

**Impact / Risk:**  

- Adds persistent build noise, making it easier to miss real warnings/errors.  
- Encourages configuration drift: overriding defaults with a value that violates the documented contract.

**Recommendation (preferred order):**  

1) Delete/simplify: remove the `turbopack.root` override entirely (Next auto-detects project root via lockfiles for this repo layout).  
2) Refactor: if you truly need it (workspaces / linked deps), set it to an absolute path via `path.join(__dirname, ...)`.  
3) Replace with library-native approach: follow Next.js Turbopack config guidance for the `root` option.

**Acceptance criteria:**

- [x] `pnpm build` no longer emits the `turbopack.root should be absolute` warning.
- [x] Module resolution still works for any linked/workspace deps (if applicable).

**References:**

- <https://nextjs.org/docs/app/api-reference/config/next-config-js/turbopack>

### ARCH-002 - Minor - Architecture - AI tool guardrails bypassed: some tools use raw `tool()` instead of `createAiTool`

**Paths:**  

- `src/ai/tools/server/travel-advisory.ts`  
- `src/ai/lib/tool-factory.ts`

**AI-slop suspected:** Yes (Confidence: Low)

**Evidence:**  

- Symbols: `getTravelAdvisory` (`tool({ ... })`), `createAiTool()`  
- What I observed:
  - Most server tools use `createAiTool()` (centralized telemetry spans + rate limit + caching behavior).  
  - `src/ai/tools/server/travel-advisory.ts` exports `getTravelAdvisory = tool({ ... })` directly, bypassing the canonical wrapper and its standard semantics.

**Impact / Risk:**  

- Guardrails drift: tools behave differently depending on which constructor was used.  
- Reduced debuggability: telemetry/rate-limit conventions become inconsistent across tools.  
- Increases odds of future tools missing required guardrails.

**Recommendation (preferred order):**  

1) Delete/simplify: stop exporting raw `tool()` tools from `src/ai/tools/server/*` unless there is a documented exception.  
2) Refactor: migrate `getTravelAdvisory` to `createAiTool()` and encode its caching/telemetry/rate-limit behavior via guardrails config.  
3) Replace with library-native approach: align tool definitions with AI SDK tool-building conventions, but keep guardrails centralized in the wrapper (not per-tool ad-hoc).

**Acceptance criteria:**  

- [ ] `getTravelAdvisory` is created via `createAiTool()` with explicit guardrails (cache/rateLimit/telemetry).  
- [ ] Tool telemetry spans for all tools share a consistent naming + attribute strategy (spot-check via tests or logs).  
- [ ] A lint/CI rule or documented convention prevents new raw `tool()` usage under `src/ai/tools/server/*`.

**References:**  

- <https://github.com/vercel/ai/blob/ai@6.0.0-beta.128/content/docs/02-foundations/04-tools.mdx>

### REL-002 - Major - Reliability - AI tool uses loopback fetch to authenticated ICS export route (likely 401)

**Paths:**  

- `src/ai/tools/server/calendar.ts`  
- `src/app/api/calendar/ics/export/route.ts`

**AI-slop suspected:** Yes (Confidence: Med)

**Evidence:**  

- Symbols: `exportItineraryToIcs` tool, `/api/calendar/ics/export` route handler  
- What I observed:
  - The tool calls `fetch(\`\${NEXT_PUBLIC_SITE_URL}/api/calendar/ics/export\`)` with only `Content-Type: application/json` headers (no cookies, no user/session headers, no internal key).  
  - The route handler is protected with `withApiGuards({ auth: true, ... })`, meaning it requires an authenticated request context.  
  - This tool path is very likely to return `401` in real usage, and it adds a pointless HTTP hop even when it does work.

**Impact / Risk:**  

- Feature breakage: exporting an itinerary to ICS is unreliable or always fails outside of very specific local/auth contexts.  
- Extra failure modes: DNS/cert/origin misconfig, increased latency, and reduced debuggability.  
- Configuration footgun: using `NEXT_PUBLIC_SITE_URL` in server-only code increases misconfiguration risk; it can also become an SSRF primitive if attacker-controlled config ever enters the environment.

**Recommendation (preferred order):**  

1) Delete/simplify: stop doing loopback HTTP fetch inside the server; generate the ICS string directly.  
2) Refactor: extract ICS generation into a shared pure function used by both the route handler and the tool.  
3) Replace with library-native approach: if a route must remain the single entrypoint, authenticate the internal call explicitly (forward cookies/headers or require an internal service key) and apply SSRF defenses.

**Acceptance criteria:**  

- [ ] `exportItineraryToIcs` succeeds without making a network call to the same service.  
- [ ] Route handler and tool produce identical ICS output for the same input (golden-file style test).  
- [ ] No server-only code uses `NEXT_PUBLIC_*` env vars for internal routing without strong justification.

**References:**  

- <https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html>

### SEC-005 - Major - Security - Open redirect in auth confirm route via unvalidated `next` param

**Paths:**  

- `src/app/auth/confirm/route.ts`

**AI-slop suspected:** Yes (Confidence: Med)

**Evidence:**  

- Symbols: `next` query param handling, `redirect(next)`  
- What I observed:
  - The route uses `const next = searchParams.get("next") ?? "/";` and then calls `redirect(next)` without validation.  
  - Next.js `redirect()` accepts relative or absolute URLs and can redirect to external links.

**Impact / Risk:**  

- Phishing amplifier: confirmation links are delivered via email (high trust). An attacker can make the link land on a hostile domain after successful OTP verification.  
- Harder to detect/attribute: open redirects blur internal navigation telemetry and can hide malicious flows.

**Recommendation (preferred order):**  

1) Delete/simplify: ignore `next` entirely unless there is a product requirement; always redirect to a fixed internal destination.  
2) Refactor: if `next` is required, accept only app-internal relative paths (allow-list routes or enforce `next.startsWith("/")` and reject `//`/`\\`/encoded variants).  
3) Replace with library-native approach: follow OWASP guidance for avoiding unvalidated redirects; map short tokens to internal destinations rather than accepting full URLs.

**Acceptance criteria:**  

- [ ] `next=http://evil.example` does not redirect externally; route falls back to a safe internal default.  
- [ ] Unit test covers common bypass encodings (e.g., `//evil`, `%2F%2Fevil`, `\\evil`).  
- [ ] Documentation states the allowed redirect destinations and why.

**References:**  

- <https://nextjs.org/docs/app/api-reference/functions/redirect>  
- <https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html>

### SEC-006 - Critical - Security - Embeddings endpoint can be public + writes via admin Supabase when internal key missing

**Paths:**  

- `src/app/api/embeddings/route.ts`

**AI-slop suspected:** Yes (Confidence: High)

**Evidence:**  

- Symbols: `withApiGuards({ auth: false, ... })`, `getServerEnvVarWithFallback("EMBEDDINGS_API_KEY", undefined)`, `createAdminSupabase()`  
- What I observed:
  - The route is configured with `auth: false`.  
  - The “internal key” check is conditional: if `EMBEDDINGS_API_KEY` is unset, the handler skips authentication entirely (no header required).  
  - When `property.id` is supplied, the route persists embeddings via `createAdminSupabase()` to `accommodation_embeddings` using `upsert` (service-role / RLS bypass semantics).

**Impact / Risk:**  

- Cost exposure: unauthenticated callers can force OpenAI embedding generation on your server key (financial DoS).  
- Data poisoning: unauthenticated callers can upsert embeddings for arbitrary IDs using the admin client, degrading downstream search/retrieval quality and corrupting data.  
- Abuse amplification: rate limiting can fail-open when Redis is unavailable (SEC-002), making worst-case behavior unbounded.

**Recommendation (preferred order):**  

1) Delete/simplify: remove persistence from this endpoint unless it is strictly required; generation-only is a smaller attack surface.  
2) Refactor: make the endpoint fail-closed:
   - If `EMBEDDINGS_API_KEY` is missing, return `503` (feature disabled) instead of becoming public.  
   - Require either `auth: true` + authorization checks, or a mandatory internal key (no “optional auth”).  
3) Replace with library-native approach: align with OWASP API guidance for cost-bearing endpoints (resource consumption limits, auth boundaries, spending limits/alerts).

**Acceptance criteria:**  

- [ ] Requests without a valid internal key (or without user auth, depending on design) always return `401/403` even when `EMBEDDINGS_API_KEY` is unset.  
- [ ] Persistence (admin Supabase writes) is only possible from authenticated/authorized contexts with tests proving it.  
- [ ] A deliberate “abuse” test (looped requests) is blocked by fail-closed rate limiting or explicit disabled-state behavior.

**References:**  

- <https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/>  
- <https://owasp.org/API-Security/editions/2023/en/0xa2-broken-authentication/>

### SEC-007 - Major - Security - Public `/api/ai/stream` uses server OpenAI key (cost/abuse vector)

**Paths:**  

- `src/app/api/ai/stream/route.ts`

**AI-slop suspected:** Yes (Confidence: High)

**Evidence:**  

- Symbols: `withApiGuards({ auth: false, ... })`, `streamText({ model: openai(model), ... })`  
- What I observed:
  - This route is explicitly marked `auth: false` and streams completions using the server OpenAI provider.  
  - It’s labeled “Demo streaming route” but is implemented as a production route handler with rate limiting that can fail-open when Redis is unavailable (SEC-002).

**Impact / Risk:**  

- Financial DoS: attackers can script requests to incur LLM usage costs.  
- Abuse: the app becomes an unauthenticated proxy to your model provider.  
- Incident response complexity: “demo” routes tend to be forgotten until they’re exploited.

**Recommendation (preferred order):**  

1) Delete/simplify: remove the route entirely from production builds if it’s only for demos.  
2) Refactor: if it must exist, require auth and an explicit environment gate (e.g., `ENABLE_AI_DEMO=true`) and fail closed when the gate is not enabled.  
3) Replace with library-native approach: treat it like any other cost-bearing API: strict rate limits, quotas, and monitoring.

**Acceptance criteria:**  

- [ ] In production configuration, `/api/ai/stream` is unreachable (404) or requires auth + internal gating.  
- [ ] Rate limiting fails closed (or the route is disabled) when Redis is unavailable.  
- [ ] A test asserts the route is disabled unless explicitly enabled.

**References:**  

- <https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/>

### SEC-008 - Major - Security - `images.dangerouslyAllowSVG: true` enabled (XSS footgun)

**Paths:**  

- `next.config.ts`

**AI-slop suspected:** No

**Evidence:**  

- Symbols: `images.dangerouslyAllowSVG`  
- What I observed:
  - `next.config.ts` sets `images.dangerouslyAllowSVG: true`.  
  - Next.js docs strongly recommend pairing this with `contentDispositionType: 'attachment'` and a strict `contentSecurityPolicy`. The config sets a CSP, but does not set `contentDispositionType`.

**Impact / Risk:**  

- SVG is an active document format; enabling SVG serving through the Image Optimization pipeline is a known XSS footgun if untrusted SVGs can ever enter the system (user uploads, upstream images, compromised CDN).  
- Configuration drift risk: a future change to `remotePatterns` could silently inherit this footgun.

**Recommendation (preferred order):**  

1) Delete/simplify: disable `dangerouslyAllowSVG` unless there is a hard requirement.  
2) Refactor: if required, add `contentDispositionType: "attachment"` and keep a strict CSP; restrict remote sources aggressively.  
3) Replace with library-native approach: follow Next.js + Vercel conformance guidance for safe SVG handling.

**Acceptance criteria:**  

- [ ] `dangerouslyAllowSVG` is `false` OR config includes both strict CSP and `contentDispositionType: "attachment"`.  
- [ ] A security review documents where SVGs come from and why this is safe.  

**References:**  

- <https://nextjs.org/docs/app/api-reference/components/image#dangerouslyallowsvg>  
- <https://vercel.com/docs/conformance/rules/NEXTJS_SAFE_SVG_IMAGES>

### SEC-009 - Minor - Security - Auth-less telemetry endpoint can spam operational alerts

**Paths:**  

- `src/app/api/telemetry/ai-demo/route.ts`

**AI-slop suspected:** Yes (Confidence: Med)

**Evidence:**  

- Symbols: `withApiGuards({ auth: false, ... })`, `emitOperationalAlert("ai_demo.stream", ...)`  
- What I observed:
  - The telemetry endpoint is `auth: false` and emits operational alerts based on caller-provided payload.  
  - Under Redis misconfig/outage, rate limiting is skipped (SEC-002), so this can turn into an alert spam endpoint.

**Impact / Risk:**  

- Operational noise and alert fatigue, reducing signal during real incidents.  
- Unbounded log/event ingest cost in worst-case abuse scenarios.

**Recommendation (preferred order):**  

1) Delete/simplify: remove the endpoint if it’s demo-only and not needed in production.  
2) Refactor: require auth or an internal key; cap `detail` length; and fail closed when limiter infra is unavailable.  
3) Replace with library-native approach: treat operational alert emission as a privileged action, not a public endpoint.

**Acceptance criteria:**  

- [ ] Unauthenticated requests cannot trigger operational alerts.  
- [ ] Alerts have dedupe/limits to prevent a single key/user from spamming.  
- [ ] Tests cover “unauthenticated cannot emit alert” behavior.

**References:**  

- <https://cheatsheetseries.owasp.org/cheatsheets/Secure_Code_Review_Cheat_Sheet.html>

### REL-003 - Major - Correctness - Attachments list schema/handler mismatch: `url` is required by schema but can be `null`

**Paths:**  

- `src/app/api/attachments/files/route.ts`  
- `src/domain/schemas/attachments.ts`

**AI-slop suspected:** Yes (Confidence: Med)

**Evidence:**  

- Symbols: `attachmentFileSchema.url`, attachments list handler mapping  
- What I observed:
  - Schema contract: `attachmentFileSchema` defines `url: z.url()` (non-null).  
  - Handler behavior: the API maps `url` as `urlMap.get(file_path) ?? null`, returning `null` when signed URL generation fails or the path is missing.  
  - This creates a hard contract mismatch: either the schema is lying, or the handler is returning invalid responses.

**Impact / Risk:**  

- Clients that validate responses against the schema will fail in real-world error paths.  
- UI breakage: attachment lists can silently return items without URLs, which is a partial failure that must be modeled explicitly.

**Recommendation (preferred order):**  

1) Delete/simplify: pick one contract and enforce it — don’t “sometimes return null” without modeling it.  
2) Refactor: either:
   - Make `url` nullable in the schema (`z.url().nullable()`) and require UI handling, **or**  
   - Make the route fail the request (5xx) if it cannot produce URLs (strong contract), **or**  
   - Filter out items without a valid URL (explicitly documented behavior).  
3) Replace with library-native approach: use Zod contracts as the source of truth and test them at the boundary.

**Acceptance criteria:**  

- [ ] Schema and handler agree on the nullability of `url`.  
- [ ] A test covers the “signed URL generation fails” path and asserts the chosen behavior.  
- [ ] Cached payloads match the schema contract (no caching of invalid shapes).

**References:**  

- <https://zod.dev/v4>

### ARCH-003 - Major - Architecture - Circular dependency between `chat-agent` and `agent-factory` in core AI layer

**Paths:**  

- `src/ai/agents/chat-agent.ts`  
- `src/ai/agents/agent-factory.ts`

**AI-slop suspected:** Yes (Confidence: Low)

**Evidence:**  

- Symbols: `normalizeInstructions`, `createTripSageAgent`  
- What I observed:
  - `agent-factory.ts` imports `normalizeInstructions` from `chat-agent.ts`.  
  - `chat-agent.ts` imports `createTripSageAgent` from `agent-factory.ts`.  
  - This is a direct module cycle in the core AI orchestration layer.

**Impact / Risk:**  

- Refactor hazard: changes to either module require reasoning across a cycle, increasing the chance of subtle regressions.  
- Initialization-order risk: cyclic imports can expose partially-initialized exports depending on module evaluation order and bundler/runtime behavior.

**Recommendation (preferred order):**  

1) Delete/simplify: extract instruction normalization utilities (`extractTextFromContent`, `normalizeInstructions`) into a small leaf module and import it from both.  
2) Refactor: enforce a one-way dependency direction for core AI creation (factory is lower-level; chat-agent composes it).  
3) Replace with library-native approach: add a lightweight “no cycles” check in CI for `src/ai/agents/*`.

**Acceptance criteria:**  

- [ ] There is no import cycle between `chat-agent` and `agent-factory` after refactor.  
- [ ] `pnpm test:quick` and `pnpm type-check` remain green.  
- [ ] A CI check fails if a new cycle is introduced in `src/ai/agents/*`.

**References:**  

- <https://nodejs.org/api/modules.html#cycles>

### AI-004 - Major - AI-Slop - Excessive `as unknown as` casts in production code (type-safety bypass)

**Paths:**  

- `src/**` (multiple)

**AI-slop suspected:** Yes (Confidence: Med)

**Evidence:**  

- Symbols: widespread `as unknown as` assertions in non-test code  
- What I observed:
  - `rg "as unknown as" src --glob '!src/test/**' --glob '!src/**/__tests__/**' --glob '!src/**/*.test.*' --glob '!src/**/*.spec.*' --glob '!src/mocks/**'` returns **~71** hits in production code.  
  - Examples include casting DB/RPC payloads and SDK outputs into expected shapes rather than validating/typing at the boundary (e.g., `src/lib/supabase/rpc.ts`, `src/app/api/jobs/memory-sync/route.ts`, `src/lib/rag/*`).

**Impact / Risk:**  

- TypeScript’s safety net is being bypassed in many places, increasing the chance of runtime shape mismatches (especially at external boundaries: DB records, RPCs, API responses, tool outputs).  
- Refactors become riskier because the compiler can’t reliably detect breakage across these cast boundaries.

**Recommendation (preferred order):**  

1) Delete/simplify: remove casts that exist only to “make TS happy” and replace with real typing/validation at the boundary.  
2) Refactor: isolate unavoidable casts into small adapter modules, and validate inputs/outputs using existing Zod schemas (`@schemas/*`) before crossing into business logic.  
3) Replace with library-native approach: prefer generated/typed Supabase helpers and AI SDK typed outputs instead of `unknown` casting.

**Acceptance criteria:**  

- [ ] The count of `as unknown as` in non-test code decreases materially (track via a simple `rg` count in CI).  
- [ ] Boundary modules (RPC, DB row mapping, external API adapters) validate shapes before returning typed objects.  
- [ ] No new `as unknown as` is introduced without an explicit justification in code review.

**References:**  

- <https://google.github.io/eng-practices/review/reviewer/standard.html>

### AI-002 - Minor - AI-Slop - Template-style `@fileoverview` + doc bloat across most files (drift/noise)

**Paths:**  

- `src/**` (widespread)

**AI-slop suspected:** Yes (Confidence: High)

**Evidence:**  

- Symbols: `@fileoverview` headers throughout `src/**`  
- What I observed:
  - `rg "@fileoverview" src` returns **~627** hits (i.e., most TS/TSX files).  
  - Many file headers read like templates (“This file provides…”, “Key features…”, “See ADR…”) and are often redundant with types/names.  
  - At least one high-risk instance already drifted from reality (AI-001: Supabase factory docs contradict tests), showing the failure mode: comments become authoritative-looking lies.

**Impact / Risk:**  

- Review and maintenance cost increases: engineers must re-verify whether comments are true.  
- Drift hides real issues (security checks that are “documented” but not enforced; see SEC-001).  
- Large-scale comment templates are a known “LLM slop” signature: lots of text, low semantic density, high drift rate.

**Recommendation (preferred order):**  

1) Delete/simplify: remove file-level boilerplate headers where they add no information beyond the filename/exports.  
2) Refactor: keep documentation only where it encodes non-obvious invariants (security boundary, caching constraints, serialization contracts) and require tests to back those claims.  
3) Replace with library-native approach: put architecture references (ADR/SPEC links) in dedicated docs, not repeated per file.

**Acceptance criteria:**  

- [ ] File-level docs exist only when they add non-obvious, test-backed information.  
- [ ] “Template-y” file headers are reduced substantially in touched areas (measured by `rg "@fileoverview" src | wc -l`).  
- [ ] Any remaining file-level docs are kept in sync via tests or lint rules.

**References:**  

- <https://genai.owasp.org/llmrisk2023-24/llm09-overreliance/>  
- <https://cacm.acm.org/news/nonsense-and-malicious-packages-llm-hallucinations-in-code-generation/>  
- <https://simonwillison.net/2025/Mar/2/hallucinations-in-code/>

### AI-003 - Minor - AI-Slop - Heuristic error classification in webhook handler (message-based status mapping)

**Paths:**  

- `src/lib/webhooks/handler.ts`

**AI-slop suspected:** Yes (Confidence: Med)

**Evidence:**  

- Symbols: `classifyError()`  
- What I observed: `classifyError()` uses a long chain of message/name heuristics (string contains) to map arbitrary errors to HTTP status codes. The file itself acknowledges this can misclassify “localized/custom messages”.

**Impact / Risk:**  

- Incorrect status codes change retry behavior for webhook senders (e.g., returning 4xx when it should be 5xx can drop events; returning 5xx when it’s 4xx can amplify retries).  
- Heuristics accumulate entropy: every new error shape adds more “maybe match this substring” logic.

**Recommendation (preferred order):**  

1) Delete/simplify: remove message heuristics; keep only concrete error-class and explicit error-code handling.  
2) Refactor: define a small set of typed errors (`WebhookValidationError`, `WebhookConflictError`, etc.) and have handlers throw those explicitly.  
3) Replace with library-native approach: align webhook retry semantics with sender expectations (e.g., Supabase/QStash) and document them once.

**Acceptance criteria:**  

- [ ] Webhook handlers throw typed errors with explicit status mapping; no message substring heuristics remain.  
- [ ] Tests cover status mapping for each error type.  
- [ ] Retry semantics are documented for each webhook source.

**References:**  

- <https://owasp.org/www-project-code-review-guide/assets/OWASP_Code_Review_Guide_v2.pdf>
