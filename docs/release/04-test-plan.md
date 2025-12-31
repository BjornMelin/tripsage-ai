# TripSage AI — Test Plan (v1.0.0)

## Goals

- Fast confidence for core behaviors.
- Minimal flakiness in CI.

## Commands

- Format/lint: `pnpm biome:fix`
- Typecheck: `pnpm type-check`
- Targeted tests: `pnpm test:affected`
- Full suite: `pnpm test`
- Browser automation (manual but deterministic): Next DevTools `browser_eval` (see task files for per-flow steps)
- E2E (all configured browsers): `pnpm test:e2e`
- E2E (Chromium-only): `pnpm exec playwright test --project=chromium`
- Install Playwright browsers: `pnpm exec playwright install`

## E2E Strategy (Playwright)

- Maintain one “critical journey” spec that mirrors `docs/release/00-release-goals.md`.
- Prefer accessibility-driven selectors (roles/names) over brittle CSS selectors.
- Record failures with:
  - deterministic steps
  - screenshots only when needed
  - console/network logs when relevant

## Next DevTools Browser Verification (preferred for tasks)

For user-facing changes, add an explicit verification section to the task file using Next DevTools `browser_eval`:

1. `browser_eval start` (headless)
2. Navigate to a full URL (example: `http://localhost:3000/register`)
3. Snapshot and assert key nodes (roles/names/urls)
4. Interact (click/type) only via accessible targets
5. Snapshot again and assert final state

### Local gotchas

- Don’t run `pnpm dev` at the same time as Playwright’s `webServer` (used by `pnpm test:e2e`). Next.js will fail with `.next/dev/lock` held by the other instance.

## Test Data

- Prefer local/dev Supabase project with minimal seed data.
- Never commit secrets; use `.env.local` and `.env.example` for names only.
