# Coverage Milestones

<!-- TODO: Delete this document once we have time to ensure if there is
any value in it, to incorporate it into the testing docs and solidify and
future proof the testing coverage requirements. Owner: @bjornmelin | Target date: 2026-03-31
| Issue: https://github.com/BjornMelin/tripsage-ai/issues/649 -->

This document defines the **current coverage baseline**, what is **enforced in CI**, and how we
intend to **raise thresholds over time** without blocking merges on unrelated work.

## How coverage is enforced

Coverage enforcement happens in two layers:

1. **Global baseline thresholds** (repo-wide) in `vitest.config.ts`.
2. **Critical-surface thresholds** in `scripts/check-coverage-critical.mjs` (run by `pnpm test:coverage`).

Run locally:

- `pnpm test:coverage` (runs all tests with coverage + critical-surface threshold check)

## Current baseline (2025-12-22)

Computed from `coverage/coverage-final.json` emitted by `pnpm test:coverage`.

| Scope | Statements | Branches | Functions | Lines |
| --- | ---: | ---: | ---: | ---: |
| Global (`src/**`, excluding tests) | 71.51% | 57.78% | 71.32% | 73.22% |

### Critical surfaces (2025-12-22)

Measured + enforced by `scripts/check-coverage-critical.mjs`.
This check also fails if any file in the critical-surface scopes is missing from
coverage output (prevents “unmeasured” critical modules).

| Surface | Statements | Branches | Functions | Lines |
| --- | ---: | ---: | ---: | ---: |
| Auth (`src/app/auth/**`, `src/lib/auth/**`) | 80.00% | 54.55% | 91.67% | 81.45% |
| Payments (`src/lib/payments/**`) | 100.00% | 100.00% | 100.00% | 100.00% |
| Keys (`src/app/api/keys/**`) | 78.67% | 67.11% | 77.78% | 79.86% |
| Webhooks (`src/lib/webhooks/**`, `src/app/api/hooks/**`, `src/lib/qstash/**`) | 76.47% | 61.66% | 75.44% | 77.30% |
| AI agents (`src/ai/agents/**`) | 59.38% | 50.21% | 58.00% | 59.75% |
| AI tool routing (`src/ai/{lib,tools}/**`, `src/app/api/chat/**`) | 68.05% | 52.71% | 67.65% | 70.55% |

## Enforced thresholds (current)

### Global baseline thresholds

Enforced by Vitest via `vitest.config.ts`:

- Statements: **50%**
- Branches: **40%**
- Functions: **55%**
- Lines: **50%**

### Critical-surface thresholds

Enforced by `scripts/check-coverage-critical.mjs`:

- Auth: statements ≥ **80%**, branches ≥ **50%**, functions ≥ **85%**, lines ≥ **80%**
- Payments: statements/branches/functions/lines ≥ **95%**
- Keys: statements ≥ **75%**, branches ≥ **60%**, functions ≥ **70%**, lines ≥ **75%**
- Webhooks: statements ≥ **70%**, branches ≥ **55%**, functions ≥ **70%**, lines ≥ **70%**
- AI agents: statements ≥ **58%**, branches ≥ **50%**, functions ≥ **57%**, lines ≥ **59%**
- AI tool routing: statements ≥ **65%**, branches ≥ **50%**, functions ≥ **65%**, lines ≥ **65%**

## Raise plan

1. **Keep global thresholds close to baseline** to prevent regressions while avoiding broad merge blocks.
2. **Raise critical surfaces first** (auth, keys, webhooks, payments, AI tool routing).
3. **Raise global thresholds** only after critical surfaces are stable and regressions are rare.

When raising thresholds:

- Update `vitest.config.ts` and/or `scripts/check-coverage-critical.mjs`.
- Update the “Enforced thresholds” section above.
- Run `pnpm test:coverage` to verify the new numbers.
