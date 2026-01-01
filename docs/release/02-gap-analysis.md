# TripSage AI — Gap Analysis (v1.0.0)

This document lists **missing, broken, unwired, or incomplete** parts discovered via:

- Static scan (TODO/FIXME/stubs)
- Build/lint/typecheck/test outputs
- Dev server runtime logs
- Playwright browser automation

## Severity Definitions

- **P0 (Ship blocker):** prevents app from running/building, blocks critical journey, or security risk.
- **P1 (Must-have):** important correctness/UX/security but workaround exists.
- **P2 (Should-have):** polish, perf improvements, cleanup after ship.

## P0 — Ship Blockers

- **T-001 (DONE):** Dev server startup blocked by optional env validation (QStash + collaborator webhook placeholders) → fixed to allow non-production boot. See `docs/tasks/T-001-dev-server-env-validation.md`.
- **T-002 (OPEN):** Chromium E2E failures on `/dashboard` load timing + missing `banner` landmark for theme toggle targeting. See `docs/tasks/T-002-dashboard-e2e-chromium.md`.
- **T-006 (DONE):** Marketing navbar “Sign up” points to `/signup` (404) → fixed to point to `/register`. See `docs/tasks/T-006-fix-navbar-signup-link.md`.
- **T-007 (DONE):** `/privacy`, `/terms`, `/contact` were linked from marketing + register UI but returned 404 → added public marketing pages. See `docs/tasks/T-007-add-privacy-terms-contact-pages.md`.

## P1 — Must-haves

- **T-003 (DONE):** Added Chromium-only script alias + documented Playwright browser install requirements (incl pnpm arg-forwarding gotcha). See `docs/tasks/T-003-playwright-e2e-runnable.md`.
- **T-004 (OPEN):** Deployment readiness decision + consolidated env inventory/runbook. See `docs/tasks/T-004-deployment-readiness.md`.
- **T-005 (OPEN):** Supabase RLS + Storage policy audit for least privilege. See `docs/tasks/T-005-supabase-rls-storage-audit.md`.
- **T-008 (OPEN):** “Plan New Trip” links to `/dashboard/trips/create` but route is missing; implement create flow or reroute CTA. See `docs/tasks/T-008-trip-create-route-or-flow.md`.
- **T-009 (DONE):** `/reset-password` “Contact support” link pointed to `/support` (404) → fixed to `/contact`. See `docs/tasks/T-009-fix-reset-password-support-link.md`.

## P2 — Should-haves

- P2 items are tracked in `docs/tasks/INDEX.md` and may not get individual task files unless needed for parallel work.

## Evidence Log

- Baseline command outputs: `docs/release/01-current-state-audit.md`
- Browser repro steps/screens: linked from task files (Next DevTools `browser_eval`; full URLs only)
- E2E run output: `docs/release/_logs/pnpm-test-e2e.txt`
