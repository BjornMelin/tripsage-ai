# T-004 — Deployment readiness (Vercel deploy strategy + env inventory)

## Meta

- ID: `T-004`
- Priority: `P1`
- Status: `UNCLAIMED`
- Owner: `-`
- Depends on: `-`

## Problem

Deployment is not “one click obvious” yet:

- `vercel.json` sets `"git.deploymentEnabled": false` (may be intentional, but must be decided for v1.0.0).
- Env var inventory is spread across `.env.example` and `@schemas/env`; we need a single, accurate runbook.

## Acceptance Criteria (black-box)

- [ ] `docs/release/07-deployment.md` lists:
  - minimum required env vars for a production deploy
  - optional integrations and their env var names
  - Supabase migration steps and webhook setup pointers
  - Upstash setup pointers
- [ ] Decision recorded for Git deployments:
  - either enable deployments (update `vercel.json`) or explicitly document manual deploy strategy

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

- Vercel env vars: https://vercel.com/docs/projects/environment-variables
- Next.js deploying: https://nextjs.org/docs/app/building-your-application/deploying

