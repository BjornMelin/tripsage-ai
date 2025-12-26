# Verification Report (Review 2025-12-15)

This report provides repo-local traceability from each finding in `docs/review/2025-12-15/review-log.md` to:

- code locations (paths),
- tests/evidence,
- exact commands executed to verify closure.

> Source of truth: `docs/review/2025-12-15/implementation-guide.md` and `docs/review/2025-12-15/review-log.md`.

## Repo + toolchain snapshot

- Branch: `chore/review-2025-12-15-finalize`
- Commit (verified): `110d8e356355c59ee323bdcd9acee54158235548`
- Node: `v24.11.0`
- pnpm: `10.26.0`

## Commands executed (all must pass)

> Append-only log. Keep newest at bottom.

- `pnpm biome:fix`
- `pnpm biome:check`
- `pnpm type-check`
- `pnpm boundary:check`
- `pnpm deps:cycles`
- `pnpm ai-tools:check`
- `pnpm check:no-unknown-casts`
- `pnpm check:no-new-unknown-casts`
- `pnpm check:fileoverviews`
- `pnpm test:affected`
- `pnpm test:coverage`
- `node -e "require.resolve('import-in-the-middle'); require.resolve('require-in-the-middle')"`
- `NEXT_PUBLIC_SITE_URL='https://example.com' NEXT_PUBLIC_SUPABASE_URL='https://abcd1234.supabase.co' NEXT_PUBLIC_SUPABASE_ANON_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjaV9idWlsZF9vbmx5IiwiaWF0IjoxNjAwMDAwMDAwfQ.dummysignature' pnpm build`
- `PORT=3102 NEXT_PUBLIC_SITE_URL='https://example.com' NEXT_PUBLIC_SUPABASE_URL='https://abcd1234.supabase.co' NEXT_PUBLIC_SUPABASE_ANON_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjaV9idWlsZF9vbmx5IiwiaWF0IjoxNjAwMDAwMDAwfQ.dummysignature' SUPABASE_JWT_SECRET='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' TELEMETRY_HASH_SECRET='bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb' timeout 15s pnpm start; test $? -eq 124`
- `pnpm check:fileoverviews:full`
- `pnpm check:no-secrets`
- `pnpm check:no-secrets:full`
- `pnpm vitest run src/lib/qstash/__tests__/receiver.test.ts`
- `node scripts/check-coverage-critical.mjs`
- `pnpm check:no-new-domain-infra-imports`
- `pnpm vitest run src/lib/telemetry/__tests__/redis.test.ts src/lib/security/__tests__/botid.test.ts src/lib/agents/__tests__/config-resolver.test.ts src/ai/services/__tests__/hotel-personalization.test.ts`
- `pnpm vitest run src/ai/tools/server/__tests__/web-crawl.test.ts src/ai/tools/server/__tests__/weather.test.ts`
- `pnpm add -D simple-git-hooks`
- `pnpm run prepare`
- `pnpm biome:fix`
- `pnpm type-check`
- `pnpm test:affected`
- `NEXT_PUBLIC_SITE_URL='https://example.com' NEXT_PUBLIC_SUPABASE_URL='https://abcd1234.supabase.co' NEXT_PUBLIC_SUPABASE_ANON_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjaV9idWlsZF9vbmx5IiwiaWF0IjoxNjAwMDAwMDAwfQ.dummysignature' pnpm build`
- `pnpm boundary:check`
- `pnpm deps:cycles`
- `pnpm ai-tools:check`
- `pnpm check:no-unknown-casts`
- `pnpm check:no-new-unknown-casts`
- `pnpm check:fileoverviews`
- `pnpm check:fileoverviews:full`
- `pnpm check:no-secrets`
- `pnpm check:no-secrets:full`
- `pnpm check:no-secrets:staged`
- `pnpm check:no-new-domain-infra-imports`
- `pnpm check:no-new-unknown-casts`
- `pnpm test:coverage`
- `pnpm lint`
- `pnpm biome:fix`
- `pnpm type-check`
- `pnpm test:affected`
- `NEXT_PUBLIC_SITE_URL='https://example.com' NEXT_PUBLIC_SUPABASE_URL='https://abcd1234.supabase.co' NEXT_PUBLIC_SUPABASE_ANON_KEY='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjaV9idWlsZF9vbmx5IiwiaWF0IjoxNjAwMDAwMDAwfQ.dummysignature' pnpm build`
- `pnpm biome:fix`
- `pnpm type-check`
- `pnpm boundary:check`
- `pnpm deps:cycles`
- `pnpm ai-tools:check`
- `pnpm check:no-unknown-casts`
- `pnpm check:no-new-unknown-casts`
- `pnpm check:fileoverviews`
- `pnpm check:no-secrets:full`
- `pnpm test:pr`
- `pnpm lint`
- `NEXT_PUBLIC_SITE_URL='https://example.com' NEXT_PUBLIC_SUPABASE_URL='https://abcd1234.supabase.co' NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY='sb_publishable_dummy' pnpm build`

## Decision records (required where options existed)

### SEC-006 — embeddings boundary

| Option | Leverage(35) | Value(30) | Maintain(25) | Adapt(10) | Weighted Total |
|---|---:|---:|---:|---:|---:|
| A — per-user auth + no admin writes | 6 | 8 | 5 | 6 | 6.35 |
| B — mandatory internal key + admin writes only under key | 8 | 9 | 9 | 7 | 8.45 |

- Chosen: **Option B**
- Rationale: `/api/embeddings` is an internal cost-bearing surface; a mandatory internal key is the simplest fail-closed boundary while preserving existing admin writes for internal indexing.

### REL-003 — attachments `url` contract

| Option | Leverage(35) | Value(30) | Maintain(25) | Adapt(10) | Weighted Total |
|---|---:|---:|---:|---:|---:|
| A — `url` nullable | 5 | 6 | 5 | 6 | 5.40 |
| B — route fails if any URL missing | 7 | 4 | 7 | 5 | 5.90 |
| C — filter out missing URLs | 8 | 8 | 8 | 7 | 7.90 |

- Chosen: **Option C**
- Rationale: Keep the schema strict (`url: z.url()`), avoid null-handling everywhere, and degrade gracefully by dropping items whose signed URL generation fails.

### TEST-001 — coverage enforcement strategy

| Option | Leverage(35) | Value(30) | Maintain(25) | Adapt(10) | Weighted Total |
|---|---:|---:|---:|---:|---:|
| A — global thresholds (repo-wide) | 7 | 6 | 6 | 6 | 6.35 |
| B — per-directory thresholds (“critical surfaces”) | 8 | 9 | 8 | 8 | 8.30 |
| C — no thresholds; coverage reporting only | 9 | 2 | 9 | 4 | 6.40 |

- Chosen: **Option B** (with a minimal global baseline)
- Rationale: Enforce meaningful targets where it matters most (auth/payments/keys/webhooks/AI tool routing) without blocking unrelated work on repo-wide thresholds; keep a low global baseline to prevent regressions elsewhere.

### AI-002 (Zen) — full-repo `@fileoverview` scan

| Option | Leverage(35) | Value(30) | Maintain(25) | Adapt(10) | Weighted Total |
|---|---:|---:|---:|---:|---:|
| A — report-only full scan | 6 | 3 | 5 | 6 | 4.85 |
| B — strict full scan + one-time cleanup | 8 | 8 | 9 | 7 | 8.15 |
| C — strict full scan + allowlists/exclusions | 7 | 6 | 6 | 6 | 6.35 |

- Chosen: **Option B**
- Rationale: Keep one invariant repo-wide (single-line `@fileoverview` blocks) without permanent exception machinery; full scan is available via `pnpm check:fileoverviews:full` while CI stays diff-based for speed.

## Traceability matrix

Each entry links back to a finding ID in `docs/review/2025-12-15/review-log.md`.

### REL-001 — Server Actions build blocker

- Code: `src/app/dashboard/search/activities/actions.ts`
- Tests/evidence: `pnpm build` passes; server action module exports comply with `"use server"` rules.
- Verification command(s): `NEXT_PUBLIC_* pnpm build`, `pnpm type-check`, `pnpm test:affected`

### DX-001 — OTEL externals + pnpm runtime resolution

- Code: `src/instrumentation.ts`, `package.json`, `next.config.ts`
- Tests/evidence: `node -e "require.resolve(...)"`; standalone production start smoke after build.
- Verification command(s): `node -e "require.resolve(...)"`, `NEXT_PUBLIC_* pnpm build`, `PORT=... timeout 15s pnpm start; test $? -eq 124`

### TEST-001 — Coverage thresholds enforcement

- Code: `vitest.config.ts`, `package.json`, `scripts/check-coverage-critical.mjs`
- Tests/evidence: critical-surface tests added to remove “missing file” gaps; coverage policy docs under `docs/development/testing/`.
- Verification command(s): `pnpm test:coverage`

### DX-002 — CI build gating

- Code: `.github/workflows/ci.yml`, `src/app/dashboard/admin/configuration/page.tsx`
- Tests/evidence: CI includes a `Production build` step on PRs touching build-affecting paths; `/dashboard/admin/configuration` forces runtime rendering via `await connection()` to avoid Cache Components build-time `Date.now()` restrictions.
- Verification command(s): `NEXT_PUBLIC_* pnpm build` (local parity)

### ARCH-001 — Layering boundaries

- Code: `docs/development/architecture/layering.md`, `scripts/check-boundaries.mjs`, `scripts/check-no-new-domain-infra-imports.mjs`
- Tests/evidence: boundary checker enforced in CI and passes locally (including a leaf rule for `src/domain/schemas/**`). Diff-based guard blocks new Domain → Lib/Infra imports.
- Verification command(s): `pnpm boundary:check`, `pnpm check:no-new-domain-infra-imports`

### AI-001 — Supabase factory doc drift / naming collision

- Code: `src/lib/supabase/factory.ts`, `src/lib/supabase/server.ts`
- Tests/evidence: `src/lib/supabase/__tests__/factory.spec.ts`
- Verification command(s): `pnpm type-check`, `pnpm test:affected`

### SEC-001 — Bounded request parsing

- Code: `src/lib/http/body.ts`, `src/lib/api/route-helpers.ts`, `src/lib/webhooks/payload.ts`, `src/lib/qstash/receiver.ts`
- Tests/evidence: `src/lib/http/body.formdata.test.ts`, `src/app/auth/register/__tests__/route.test.ts`, `src/app/api/chat/attachments/__tests__/route.test.ts`
- Verification command(s): `pnpm test:affected`

### SEC-002 — Explicit fail-open/fail-closed policy

- Code: `src/lib/api/factory.ts`, `src/lib/webhooks/rate-limit.ts`, `src/lib/idempotency/redis.ts`, `src/lib/telemetry/degraded-mode.ts`
- Tests/evidence: `src/lib/api/__tests__/factory.degraded-mode.test.ts`
- Verification command(s): `pnpm test:affected`

### SEC-003 — QStash secrets in logs

- Code: `src/lib/qstash/receiver.ts`
- Tests/evidence: `src/lib/qstash/__tests__/receiver.test.ts`
- Verification command(s): `pnpm test:affected`

### SEC-004 — Telemetry identifier safety

- Code: `src/lib/telemetry/identifiers.ts`, `docs/development/security/telemetry-data-classification.md`
- Tests/evidence: `src/app/api/jobs/memory-sync/__tests__/route.test.ts` (and related unit coverage)
- Verification command(s): `pnpm test:affected`

### DX-003 — Turbopack root inference warning

- Code: `next.config.ts`
- Tests/evidence: Next config no longer sets invalid `turbopack.root`; build is warning-free.
- Verification command(s): `NEXT_PUBLIC_* pnpm build`

### ARCH-002 — `createAiTool` guardrails enforcement

- Code: `src/ai/lib/tool-factory.ts`, `scripts/check-ai-tools.mjs`
- Tests/evidence: tool guardrails unit tests + CI check.
- Verification command(s): `pnpm ai-tools:check`, `pnpm test:affected`

### REL-002 — ICS generation loopback fetch removal

- Code: `src/lib/calendar/ics.ts`, `src/app/api/calendar/ics/export/route.ts`, `src/ai/tools/server/calendar.ts`
- Tests/evidence: `src/lib/calendar/__tests__/ics.test.ts`
- Verification command(s): `pnpm test:affected`

### SEC-005 — Open redirect in auth confirm

- Code: `src/app/auth/confirm/route.ts`, `src/lib/auth/confirm-next.ts`
- Tests/evidence: `src/app/auth/confirm/__tests__/route.test.ts`
- Verification command(s): `pnpm test:affected`

### SEC-006 — Embeddings endpoint fail-closed

- Code: `src/app/api/embeddings/route.ts`, `src/lib/api/factory.ts`
- Tests/evidence: `src/app/api/embeddings/__tests__/route.test.ts`
- Verification command(s): `pnpm test:affected`

### SEC-007 — AI demo streaming route hard gate

- Code: `src/app/api/ai/stream/route.ts`
- Tests/evidence: `src/app/api/ai/stream/__tests__/route.integration.test.ts`
- Verification command(s): `pnpm test:affected`

### SEC-008 — `dangerouslyAllowSVG` disabled

- Code: `next.config.ts`
- Tests/evidence: `images.dangerouslyAllowSVG` set to `false`.
- Verification command(s): `NEXT_PUBLIC_* pnpm build`

### SEC-009 — Telemetry demo endpoint auth + abuse caps

- Code: `src/app/api/telemetry/ai-demo/route.ts`
- Tests/evidence: `src/app/api/telemetry/ai-demo/__tests__/route.test.ts`
- Verification command(s): `pnpm test:affected`

### REL-003 — Attachments URL contract mismatch

- Code: `src/app/api/attachments/files/route.ts`, `src/app/api/attachments/files/__tests__/route.test.ts`, `@schemas/attachments`
- Tests/evidence: `src/app/api/attachments/files/__tests__/route.test.ts`
- Verification command(s): `pnpm test:affected`

### ARCH-003 — AI core circular dependency

- Code: `src/ai/agents/instructions.ts`, `src/ai/agents/agent-factory.ts`
- Tests/evidence: `pnpm deps:cycles` passes; agents remain test-covered.
- Verification command(s): `pnpm deps:cycles`, `pnpm test:affected`, `pnpm type-check`

### AI-004 — No `as unknown as` in production code

- Code: `scripts/check-no-unknown-casts.mjs`, `scripts/check-no-new-unknown-casts.mjs`
- Tests/evidence: CI enforces `as unknown as` ban in non-test `src/**`.
- Verification command(s): `pnpm check:no-unknown-casts`, `pnpm check:no-new-unknown-casts`

### AI-002 — File-level doc drift guardrails

- Code: `scripts/check-fileoverviews.mjs`, `.github/workflows/ci.yml`
- Tests/evidence: diff-based enforcement on changed files; full repo scan available; non-test `src/**` headers normalized to single-line blocks.
- Verification command(s): `pnpm check:fileoverviews`, `pnpm check:fileoverviews:full`

### AI-003 — Webhook error typing (no heuristics)

- Code: `src/lib/webhooks/handler.ts`, `src/lib/webhooks/errors.ts`
- Tests/evidence: `src/lib/webhooks/__tests__/handler.test.ts`
- Verification command(s): `pnpm test:affected`

## Primary references used (version-aligned)

> Add any additional links referenced during finalization.

- Next.js docs: <https://nextjs.org/docs/app>
- Next.js `use server` directive: <https://nextjs.org/docs/app/api-reference/directives/use-server>
- Next.js `redirect()`: <https://nextjs.org/docs/app/api-reference/functions/redirect>
- Next.js `connection()`: <https://nextjs.org/docs/app/api-reference/functions/connection>
- Next.js `serverExternalPackages`: <https://nextjs.org/docs/app/api-reference/config/next-config-js/serverExternalPackages>
- Next.js OpenTelemetry: <https://nextjs.org/docs/app/guides/open-telemetry>
- Next.js Instrumentation: <https://nextjs.org/docs/app/guides/instrumentation>
- Next.js CI build caching: <https://nextjs.org/docs/app/guides/ci-build-caching>
- Next.js Turbopack config: <https://nextjs.org/docs/app/api-reference/config/next-config-js/turbopack>
- Next.js Image SVG safety (`dangerouslyAllowSVG`): <https://nextjs.org/docs/app/api-reference/components/image#dangerouslyallowsvg>
- Vercel conformance (safe SVG images): <https://vercel.com/docs/conformance/rules/NEXTJS_SAFE_SVG_IMAGES>
- React `use server`: <https://react.dev/reference/rsc/use-server>
- AI SDK v6: <https://v6.ai-sdk.dev/llms.txt>
- AI SDK v6 MCP tools: <https://v6.ai-sdk.dev/docs/ai-sdk-core/mcp-tools>
- AI SDK v6 ToolLoopAgent: <https://v6.ai-sdk.dev/docs/reference/ai-sdk-core/tool-loop-agent>
- Supabase SSR client creation: <https://supabase.com/docs/guides/auth/server-side/creating-a-client>
- Supabase API keys: <https://supabase.com/docs/guides/api/api-keys>
- Supabase key changes announcement: <https://github.com/orgs/supabase/discussions/29260>
- Note: Supabase MCP docs search required auth in this environment; relied on Supabase official guide URL above.
- Upstash QStash signature verification: <https://upstash.com/docs/qstash/howto/signature>
- Upstash QStash signing key rotation: <https://upstash.com/docs/qstash/howto/roll-signing-keys>
- Note (2025-12-22): <https://upstash.com/docs/qstash/howto/signature-validation> returns 404; Upstash now documents signature verification under `/signature`.
- Upstash Ratelimit timeout behavior: <https://upstash.com/docs/redis/sdks/ratelimit-ts/features#timeout>
- Upstash Ratelimit `limit()` response: <https://upstash.com/docs/redis/sdks/ratelimit-ts/methods#limit>
- OWASP Unvalidated Redirects & Forwards: <https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html>
- OWASP SSRF Prevention: <https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html>
- OWASP API4:2023 Unrestricted Resource Consumption: <https://owasp.org/API-Security/editions/2023/en/0xa4-unrestricted-resource-consumption/>
- OWASP API2:2023 Broken Authentication: <https://owasp.org/API-Security/editions/2023/en/0xa2-broken-authentication/>
- Node.js cycles: <https://nodejs.org/api/modules.html#cycles>
- Zod v4: <https://zod.dev/v4>
- Vitest coverage: <https://vitest.dev/guide/coverage.html>
