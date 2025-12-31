# TripSage AI — Execution Plan (v1.0.0)

This plan is designed for **parallel Codex sessions** with minimal merge conflicts.

## Current Status (from audit)

- Baseline is green: `pnpm install`, `pnpm build`, `pnpm type-check`, `pnpm test` passed (see `docs/release/01-current-state-audit.md`).
- Dev server previously failed fast due to optional env placeholders; fixed in `T-001`.
- Public-route navigation has been de-flaked:
  - `T-006` fixed marketing navbar “Sign up” pointing to `/signup` (404).
  - `T-007` added `/privacy`, `/terms`, `/contact` pages for onboarding + footer links.
  - `T-009` fixed `/reset-password` “Contact support” link pointing to `/support` (404).
- E2E currently not green:
  - Chromium: failures in dashboard navigation timing + theme toggle banner targeting (`T-002`).
  - Firefox/WebKit: missing local browser executables by default (`T-003`).

## Milestones

1. **Green baseline:** install + build + type-check + tests pass.
2. **Critical journey:** landing → auth → primary workflow → settings → logout passes via Playwright.
3. **Security hardening:** RLS, input validation, rate limiting, secret hygiene.
4. **Release readiness:** docs, deployment runbook, release notes.

## Task Graph (current)

```text
T-001 (DONE)  Dev server boots with placeholder env

T-006 (DONE)  Navbar “Sign up” → /register (remove /signup 404)
T-007 (DONE)  Add /privacy /terms /contact (remove legal 404s)
T-009 (DONE)  Reset password “Contact support” → /contact (remove /support 404)

T-002 (P0)  Chromium E2E: /dashboard load + theme toggle banner
  |
  +--> T-008 (P1)  Trip create flow: fix /dashboard/trips/create dead link

T-003 (P1)  E2E runnable defaults (browser installs/docs/config)
T-004 (P1)  Deployment readiness (env inventory + deploy strategy)
T-005 (P1)  Supabase RLS + Storage policy audit (least privilege)
```

## Parallel Lanes (recommended)

- Lane A — Runtime & routing (build errors, route wiring, navigation)
- Lane B — Supabase auth & RLS (policies, SSR auth flow, storage)
- Lane C — UI/UX & theming (accessibility, layout, component wiring)
- Lane D — Playwright E2E (critical journey automation + CI stability)
- Lane E — AI SDK wiring (models, tool routes, error handling, quotas)
- Lane F — Deployment/perf/cost (Vercel config, caching, budgets, observability)

## Lane Assignment Suggestions (v1.0.0)

- Lane D: `T-002` (P0)
- Lane D/F: `T-003` (P1)
- Lane F: `T-004` (P1)
- Lane B: `T-005` (P1)
- Lane A/C: `T-008` (P1)

## Ordering Constraints

- Fix **P0** first.
- Playwright flows should be updated after each P0 closes.
- Security changes (RLS, rate limiting) must be validated against the Playwright journey.

## Definition of Done (per task)

- Code quality gates (repo contract):
  - `pnpm biome:fix`
  - `pnpm type-check`
  - `pnpm test:affected`
- Browser verification:
  - Prefer Next DevTools `browser_eval` for deterministic navigate → snapshot → interact → snapshot validation.
  - If adding/changing E2E specs, ensure `pnpm test:e2e` and `pnpm exec playwright test --project=chromium` pass.

## Risks & Mitigations (ship-focused)

- Auth-dependent flows are hard to verify without a seeded Supabase dev project.
  - Mitigation: `T-004` must include a local/dev Supabase bootstrap + seed path; `T-005` must align RLS with that seed.
- Dashboard E2E failures may mask deeper route wiring issues.
  - Mitigation: Fix `T-002` first, then immediately validate the trip-create path (`T-008`) in a real browser.
- CI flakiness from Playwright browser installs.
  - Mitigation: `T-003` to standardize browser install steps and CI caching assumptions.

## Task Graph

See `docs/tasks/INDEX.md` for dependencies and ownership.
