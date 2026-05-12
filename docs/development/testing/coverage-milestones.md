# Coverage Milestones

This document defines the **current coverage baseline**, what is **enforced in CI**, and how we
intend to **raise thresholds over time** without blocking merges on unrelated work.

## How coverage is enforced

Coverage enforcement happens in two layers:

1. **Global baseline thresholds** (repo-wide) in `vitest.config.ts`.
2. **Critical-surface thresholds** in `scripts/check-coverage-critical.mjs` (run by `pnpm test:coverage`).

Push CI uses Vitest blob-report sharding for coverage. Shards skip threshold enforcement because
each shard only sees a partial test subset; the merge job enforces thresholds against the aggregate
coverage report.

Run locally:

- `pnpm test:coverage` (runs all tests with coverage + critical-surface threshold check)

## Current baseline (2026-05-12)

Computed from `coverage/coverage-final.json` emitted by `pnpm test:coverage`.

| Scope | Statements | Branches | Functions | Lines |
| --- | ---: | ---: | ---: | ---: |
| Global (`src/**`, excluding tests) | 40.14% | 28.91% | 48.28% | 41.78% |

### Critical surfaces (2026-05-12)

Measured + enforced by `scripts/check-coverage-critical.mjs`.
This check also fails if any file in the critical-surface scopes is missing from
coverage output (prevents “unmeasured” critical modules).

| Surface | Statements | Branches | Functions | Lines |
| --- | ---: | ---: | ---: | ---: |
| Auth (`src/app/auth/**`, `src/lib/auth/**`) | 77.92% | 53.11% | 88.46% | 79.24% |
| Payments (`src/lib/payments/**`) | 81.91% | 57.50% | 94.12% | 81.72% |
| Keys (`src/app/api/keys/**`) | 85.03% | 69.64% | 87.50% | 88.24% |
| Webhooks (`src/lib/webhooks/**`, `src/app/api/hooks/**`, `src/lib/qstash/**`) | 84.52% | 72.05% | 85.45% | 84.80% |
| AI agents (`src/ai/agents/**`) | 65.99% | 52.79% | 67.69% | 67.78% |
| AI tool routing (`src/ai/{lib,tools}/**`, `src/app/api/chat/**`) | 62.20% | 45.76% | 63.20% | 65.05% |

## Enforced thresholds (current)

### Global baseline thresholds

Enforced by Vitest via `vitest.config.ts`:

- Statements: **40%**
- Branches: **28%**
- Functions: **48%**
- Lines: **40%**

### Critical-surface thresholds

Enforced by `scripts/check-coverage-critical.mjs`:

- Auth: statements ≥ **77%**, branches ≥ **50%**, functions ≥ **85%**, lines ≥ **79%**
- Payments: statements ≥ **81%**, branches ≥ **57%**, functions ≥ **94%**, lines ≥ **81%**
- Keys: statements ≥ **75%**, branches ≥ **60%**, functions ≥ **70%**, lines ≥ **75%**
- Webhooks: statements ≥ **70%**, branches ≥ **55%**, functions ≥ **70%**, lines ≥ **70%**
- AI agents: statements ≥ **58%**, branches ≥ **50%**, functions ≥ **57%**, lines ≥ **59%**
- AI tool routing: statements ≥ **62%**, branches ≥ **45%**, functions ≥ **63%**, lines ≥ **65%**

## Raise plan

1. **Keep global thresholds close to baseline** to prevent regressions while avoiding broad merge blocks.
2. **Raise critical surfaces first** (auth, keys, webhooks, payments, AI tool routing).
3. **Raise global thresholds** only after critical surfaces are stable and regressions are rare.

When raising thresholds:

- Update `vitest.config.ts` and/or `scripts/check-coverage-critical.mjs`.
- Update the “Enforced thresholds” section above.
- Run `pnpm test:coverage` to verify the new numbers.
