# TripSage AI — v1.0.0 Release Goals

Owner: Release Orchestrator

## Objective

Ship a **v1.0.0** that is stable, secure, and verifiably working in a real browser.

## In Scope (v1.0.0)

- App starts in dev and builds in CI-like mode.
- Core user journey works end-to-end in browser automation (Playwright):
  - Landing → Sign in / Sign up (or auth-less demo mode if explicitly supported) → Primary workflow → Settings → Logout.
- API routes and Server Actions validate inputs and handle errors consistently.
- Supabase auth + RLS align with product intent (least privilege; no insecure defaults).
- Rate limiting on externally reachable routes that can be abused (auth, AI, webhooks).
- No secrets exposed to client bundles.
- Test strategy in place (unit + component + API + e2e) with runnable commands.
- Deployment runbook for Vercel + Supabase + Upstash (free-tier friendly).

## Explicit Non-Goals

- Large refactors for style/architecture unless required to ship.
- New major product features beyond wiring and finishing “already intended” flows.
- Paid vendors beyond Vercel/Supabase/Upstash unless explicitly documented and justified.
- Over-abstracted frameworks, wrappers, or feature-flag systems.

## Definition of Done (Release)

- `pnpm install` succeeds.
- `pnpm build` succeeds.
- `pnpm type-check` succeeds.
- `pnpm test:affected` succeeds.
- Playwright automation can complete the v1 critical journey without manual intervention.
- `/docs/release/*` is complete and current for this release cut.

## Current Blockers

- `T-002` (P0): Chromium E2E dashboard failures (see `docs/tasks/T-002-dashboard-e2e-chromium.md`).
- `T-003` (P1): E2E runnable defaults (see `docs/tasks/T-003-playwright-e2e-runnable.md`).

## Evidence Sources

- Command outputs: `docs/release/01-current-state-audit.md`
- Gap list: `docs/release/02-gap-analysis.md`
- Task graph: `docs/tasks/INDEX.md`
