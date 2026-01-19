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

- Typecheck, lint (Biome), unit tests, e2e smoke.
- Separate workflows:
  - CI (PR)
  - Security (scheduled + PR)
  - Vercel Preview (PR)

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
  - `pnpm deps:audit`
- PR CI:
  - run `pnpm biome:fix` and fail if it introduces diffs (`git diff --exit-code`)
  - run `pnpm type-check`
  - run `pnpm test:affected`
  - run `pnpm deps:audit`
- Main branch / merge CI:
  - run the full suite (`pnpm test:ci`) + E2E (`pnpm test:e2e` or `pnpm test:e2e:chromium`)

## References

```text
Next.js testing guide: https://nextjs.org/docs/app/guides/testing
Vitest: https://vitest.dev/guide/
Playwright: https://playwright.dev/docs/intro
```
