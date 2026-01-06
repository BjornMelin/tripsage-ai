# SPEC-0109: Testing, quality, and CI

**Version**: 1.0.0  
**Status**: Final  
**Date**: 2026-01-05

## Test pyramid

- Unit: Vitest for pure functions, schemas, server helpers.
- Integration: route handlers and server actions (Node runtime).
- E2E: Playwright for critical user journeys.

## CI requirements

- Typecheck, lint (Biome), unit tests, e2e smoke.
- Separate workflows:
  - CI (PR)
  - Security (scheduled + PR)
  - Vercel Preview (PR)

## References

```text
Next.js testing guide: https://nextjs.org/docs/app/guides/testing
Vitest: https://vitest.dev/guide/
Playwright: https://playwright.dev/docs/intro
```
