# Coverage Milestones

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
|---|---:|---:|---:|---:|
| Global (repo-wide) | 69.64% | 55.46% | 69.04% | 71.27% |

### Critical surfaces (2025-12-22)

Measured + enforced by `scripts/check-coverage-critical.mjs`.
This check also fails if any file in the critical-surface scopes is missing from
coverage output (prevents “unmeasured” critical modules).

| Surface | Statements | Branches | Functions | Lines |
|---|---:|---:|---:|---:|
| Auth (`src/app/auth/**`, `src/lib/auth/**`) | 80.00% | 54.55% | 91.67% | 81.45% |
| Payments (`src/lib/payments/**`) | 100.00% | 100.00% | 100.00% | 100.00% |
| Keys (`src/app/api/keys/**`) | 78.67% | 67.11% | 77.78% | 79.86% |
| Webhooks (`src/lib/webhooks/**`, `src/app/api/hooks/**`, `src/lib/qstash/**`) | 75.98% | 60.47% | 75.44% | 76.80% |
| AI tool routing (`src/ai/{lib,tools}/**`, `src/app/api/chat/**`) | 55.53% | 39.58% | 60.50% | 57.47% |

## Enforced thresholds (current)

### Global baseline thresholds

Enforced by Vitest via `vitest.config.ts`:

- Statements: **45%**
- Branches: **35%**
- Functions: **50%**
- Lines: **45%**

### Critical-surface thresholds

Enforced by `scripts/check-coverage-critical.mjs`:

- Auth: statements ≥ **80%**, branches ≥ **50%**, functions ≥ **85%**, lines ≥ **80%**
- Payments: statements/branches/functions/lines ≥ **95%**
- Keys: statements ≥ **75%**, branches ≥ **60%**, functions ≥ **70%**, lines ≥ **75%**
- Webhooks: statements ≥ **70%**, branches ≥ **55%**, functions ≥ **70%**, lines ≥ **70%**
- AI tool routing: statements ≥ **53%**, branches ≥ **37%**, functions ≥ **58%**, lines ≥ **55%**

## Raise plan

1. **Keep global thresholds close to baseline** to prevent regressions while avoiding broad merge blocks.
2. **Raise critical surfaces first** (auth, keys, webhooks, payments, AI tool routing).
3. **Raise global thresholds** only after critical surfaces are stable and regressions are rare.

When raising thresholds:

- Update `vitest.config.ts` and/or `scripts/check-coverage-critical.mjs`.
- Update the “Enforced thresholds” section above.
- Run `pnpm test:coverage` to verify the new numbers.
