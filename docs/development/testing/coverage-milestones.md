# Coverage Milestones

Incremental test coverage targets for TripSage AI. Thresholds enforce minimum coverage in CI; goals drive team priority.

## Current Baseline (Actual)

As of Phase 0 (fix/build-ci-fix), measured against all test projects:

| Metric | Current | Threshold | Goal |
|--------|---------|-----------|------|
| Statements | ~49% | 45% | 85%+ |
| Lines | ~49% | 45% | 85%+ |
| Functions | ~55% | 50% | 85%+ |
| Branches | ~36% | 35% | 85%+ |

---

## Incremental Milestones

### Milestone 1: Stabilize (Phase 0–Phase 0.5)
**Target:** Statements 55%, Lines 55%, Functions 60%, Branches 40%

- Raise baseline thresholds in `vitest.config.ts`
- Add critical path tests for core schemas (`@schemas/trip`, `@schemas/auth`)
- Cover top 3 utilities in `@/lib` by call frequency

**Owner:** @BjornMelin | **Timeline:** By end of Phase 0.5 | **Trigger:** Merge fix/build-ci-fix, begin Phase 0.5

---

### Milestone 2: Core Paths (Phase 0.5–Phase 1)
**Target:** Statements 65%, Lines 65%, Functions 70%, Branches 50%

- API route handlers in `src/app/api/**` (post, get for key routes)
- Zustand stores in `src/stores/**` (selectors, actions)
- React Hook Form integration tests

**Owner:** @BjornMelin | **Timeline:** By start of Phase 1 | **Trigger:** Phase 0.5 completion

---

### Milestone 3: Broad Coverage (Phase 1–Phase 1.5)
**Target:** Statements 75%, Lines 75%, Functions 80%, Branches 65%

- Component tests for dashboard and core UI
- Server action tests (`src/app/*/actions.ts`)
- Upstash Redis/QStash integration

**Owner:** @BjornMelin | **Timeline:** By mid Phase 1 | **Trigger:** Phase 1 kickoff

---

### Milestone 4: High Coverage (Phase 1.5–Phase 2)
**Target:** Statements 82%, Lines 82%, Functions 85%, Branches 75%

- Edge cases and error paths for handlers
- Complex form wizards and conditional flows
- AI SDK integration (chat, tool execution)

**Owner:** @BjornMelin | **Timeline:** By Phase 1.5 | **Trigger:** Phase 1 mid-review

---

### Milestone 5: Aspirational (Phase 2+)
**Target:** Statements 85%+, Lines 85%+, Functions 90%, Branches 85%+

- Remaining edge cases and race conditions
- Error boundary and telemetry paths
- Full E2E flow coverage

**Owner:** @BjornMelin | **Timeline:** Ongoing | **Trigger:** Post Phase 2 planning

---

## How to Track Progress

1. **Local:** `pnpm test:coverage` to measure on your branch.
2. **CI:** GitHub Actions logs show coverage report after merge; compare against `vitest.config.ts` thresholds.
3. **Reference:** See `docs/development/testing/testing.md` for test structure and patterns.

## Updating This Plan

When a milestone is reached:
1. Update the threshold row in `vitest.config.ts` (lines 100–108).
2. Update the "Current Baseline" table above.
3. Add a comment in `vitest.config.ts` with the PR and date of the update.
4. Open a follow-up issue or PR to plan the next milestone.

---

See also: [Testing Guide](./testing.md), [Zod Schemas](./zod-schema-guide.md)
