# T-004 — Deployment readiness (Vercel deploy strategy + env inventory)

## Meta

- ID: `T-004`
- Priority: `P1`
- Status: `DONE`
- Owner: `codex-session-t004-a`
- Depends on: `-`

## Problem

Deployment was not “one-click obvious” yet:

- Git deployments were disabled via `vercel.json` (`git.deploymentEnabled: false`) and needed a v1.0.0 decision.
- Env var inventory was spread across `.env.example` and `@schemas/env` without a single, accurate runbook.

## Acceptance Criteria (black-box)

- [x] `docs/release/07-deployment.md` lists:
  - minimum required env vars for a production deploy
  - optional integrations and their env var names
  - Supabase migration steps and webhook setup pointers
  - Upstash setup pointers
- [x] Decision recorded for Git deployments:
  - enable deployments (updated `vercel.json`)

## Likely Files

- `vercel.json`
- `docs/release/07-deployment.md`
- `.env.example`
- `src/domain/schemas/env.ts`

## Verification (commands)

- `pnpm build`
- `pnpm start` (serves `.next/standalone/server.js` after build)

## Playwright Verification Steps

1. Deploy to Vercel (manual steps per runbook)
2. Navigate to deployed URL
3. Verify landing loads and auth routes are reachable

## Notes / Links (full URLs only)

- [Vercel environment variables](https://vercel.com/docs/projects/environment-variables)
- [Next.js deploying](https://nextjs.org/docs/app/building-your-application/deploying)

## Evidence (commands, outputs, inspected files)

### Git deployments decision

- Decision: enable Git deployments for v1.0.0.
- Implemented in: `vercel.json` (`git.deploymentEnabled: true`).
- Reference: https://vercel.com/docs/project-configuration/git-configuration

### Runtime inventory (Phase A)

- Dev server: `pnpm dev` → `http://localhost:3000`
- Next DevTools MCP:
  - `next-devtools.init` (project root)
  - `next-devtools.nextjs_index` → discovered server on port `3000`
  - `nextjs_call:get_routes` → confirmed route surface includes (examples):
    - Pages: `/`, `/login`, `/register`
    - API: `/api/auth/login`, `/api/chat/attachments`, `/api/attachments/files`, `/api/hooks/{cache,files,trips}`, `/api/jobs/*`
  - `nextjs_call:get_errors` → `No errors detected in 1 browser session(s).`
  - `nextjs_call:get_logs` → `.next/dev/logs/next-development.log`
    - Log tail (2026-01-01): `✓ Ready in 891ms` (see file)
- Browser smoke (headless Chrome via `next-devtools.browser_eval`):
  - `GET http://localhost:3000/` OK
  - `GET http://localhost:3000/login` OK
  - No console errors/warnings observed during smoke

### Build/start checks (Phase B)

- `pnpm build` → ✅ succeeded.
- `pnpm start`:
  - ❌ fails with missing env validation when required vars are unset (expected; see `@schemas/env`).
  - ✅ boots when minimum production boot env vars are present (placeholder values used for test boot).

### Env inventory (source-of-truth reconciliation)

- Repo scan command (authoritative usage inventory):
  - `rg -n "process\\.env\\.|getServerEnv\\(|getClientEnv\\(|NEXT_PUBLIC_|SUPABASE|UPSTASH|QSTASH|AI_GATEWAY|BOTID|STRIPE|RESEND" src -S`
- Minimum production boot vars enforced by schema:
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY` (or mapped via `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`)
  - `SUPABASE_JWT_SECRET` (≥32 chars)
  - `TELEMETRY_HASH_SECRET` (≥32 chars)
- Production-functional requirements (documented in runbook):
  - Upstash Redis (`UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`) is operationally required for many API routes because rate limits default to fail-closed when Redis is unavailable.

### Quality gates (required after `vercel.json` change)

- `pnpm biome:fix` → `Checked 1070 files... No fixes applied.`
- `pnpm type-check` → ✅ exit code `0`
- `pnpm test:affected` → ✅ exit code `0` (no affected tests)

### Docs + configs delivered

- Runbook: `docs/release/07-deployment.md`
- Git deploy switch: `vercel.json`

### Files inspected (local source-of-truth)

- `docs/release/07-deployment.md`
- `docs/tasks/T-004-deployment-readiness.md`
- `vercel.json`
- `.env.example`
- `.env.test.example`
- `src/domain/schemas/env.ts`
- `src/lib/env/server.ts`
- `src/lib/env/client.ts`
- `playwright.config.ts`
- `.next/dev/logs/next-development.log`

### References used (full URLs)

- Next.js deploying: https://nextjs.org/docs/app/building-your-application/deploying
- Next.js env vars: https://nextjs.org/docs/app/guides/environment-variables
- Next.js output (standalone): https://nextjs.org/docs/app/api-reference/config/next-config-js/output
- Vercel env vars: https://vercel.com/docs/projects/environment-variables
- Vercel vercel.json: https://vercel.com/docs/project-configuration/vercel-json
- Vercel git config: https://vercel.com/docs/project-configuration/git-configuration
- Vercel Next.js: https://vercel.com/docs/frameworks/nextjs
- Vercel AI Gateway auth: https://vercel.com/docs/ai-gateway/authentication
- Vercel BotID: https://vercel.com/docs/botid/get-started
- Supabase SSR client: https://supabase.com/docs/guides/auth/server-side/creating-a-client
- Supabase API keys: https://supabase.com/docs/guides/api/api-keys
- Supabase auth redirect URLs: https://supabase.com/docs/guides/auth/redirect-urls
- Supabase RLS: https://supabase.com/docs/guides/database/postgres/row-level-security
- Supabase Storage access control: https://supabase.com/docs/guides/storage/security/access-control
- Supabase pg_net webhook debugging: https://supabase.com/docs/guides/troubleshooting/webhook-debugging-guide
- Upstash Redis connect: https://upstash.com/docs/redis/howto/connectwithupstashredis
- Upstash QStash signature verification: https://upstash.com/docs/qstash/howto/signature
- Upstash QStash key rotation: https://upstash.com/docs/qstash/howto/roll-signing-keys

### Skill usage

- Used: `ai-sdk-core` (AI Gateway env + provider notes), `supabase-ts` (SSR auth + RLS/storage deployment implications)
- Not used: `vitest-dev` (no test/config work beyond required gates)
