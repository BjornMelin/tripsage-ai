# SPEC-0109: Testing, quality, and CI

**Version**: 1.1.0  
**Status**: Final  
**Date**: 2026-01-19

## Test pyramid

- Unit: Vitest for pure functions, schemas, server helpers.
- Integration: route handlers and server actions (Node runtime).
- E2E: Playwright for critical user journeys.

Coverage:

- Maintain ≥85% overall coverage (enforced via Vitest thresholds).

## Test sharding (local)

- `pnpm test:unit` — pure functions and utilities
- `pnpm test:schemas` — schema validation
- `pnpm test:api` — Route Handlers and server endpoints
- `pnpm test:components` — React components (jsdom)
- `pnpm test:integration` — cross-module integration tests
- `pnpm test:e2e:chromium` — Chromium-only E2E (fast path)
- `pnpm test:affected` — only changed/related tests (PR workflow)

## CI requirements

- PR CI runs Biome, TypeScript, architecture guardrails, secrets checks, build,
  affected Vitest coverage, and critical Playwright E2E when UI/runtime files
  change.
- Production deploy validation runs separately through the Vercel CLI deploy
  workflow and `scripts/vercel-deploy-smoke.mjs`.
- Release automation runs only after CI succeeds for a push to `main`; its
  generated changelog commit must then receive its own successful push CI run.
- The active workflows are:
  - CI (`.github/workflows/ci.yml`)
  - Deploy (`.github/workflows/deploy.yml`)
  - Release (`.github/workflows/release.yml`)

## Dependency hygiene (Knip)

TripSage enforces unused dependency hygiene with Knip:

- `pnpm deps:report` — non-failing report
- `pnpm deps:audit` — failing gate (unused dependencies)

Notes:

- Some tooling loads plugins by string (e.g., release tooling); these may require explicit Knip ignores in `knip.json` to avoid false positives.
- `pnpm-workspace.yaml` excludes vendored source under `opensrc/` so workspace-wide tooling (`pnpm -r …`) does not recurse into unrelated package trees.

Recommended stages:

- Local before pushing:
  - `pnpm biome:fix`
  - `pnpm type-check`
  - `pnpm test:affected`
  - `pnpm test:e2e:critical` when changing user-visible flows
  - `pnpm check:zod-v4`
  - `pnpm check:api-route-errors`
  - `pnpm deps:audit`
- PR CI:
  - run `pnpm biome:fix` and fail if it introduces diffs (`git diff --exit-code`)
  - run `pnpm type-check`
  - run `pnpm test:affected`
  - run `pnpm test:e2e:critical` for app/runtime changes
  - run `pnpm check:zod-v4` (diff-based)
  - run `pnpm check:api-route-errors` (diff-based)
  - run `pnpm deps:audit`
- Main branch / merge CI (runs for every push so release eligibility never
  depends on a path filter):
  - run the full suite (`pnpm test:ci`) + E2E (`pnpm test:e2e` or `pnpm test:e2e:chromium`)
- Deployment smoke:
  - run `pnpm deploy:check-env`
  - run `pnpm deploy:smoke -- --url "$DEPLOYMENT_URL"`
  - run `pnpm test:smoke:live -- --url "$DEPLOYMENT_URL"` for operator live-smoke lanes

## References

```text
Next.js testing guide: https://nextjs.org/docs/app/guides/testing
Vitest: https://vitest.dev/guide/
Playwright: https://playwright.dev/docs/intro
```
