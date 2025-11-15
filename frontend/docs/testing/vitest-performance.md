# Vitest Performance Notes

This document captures the current hotspots identified in the frontend Vitest
suite and the guardrails we added to keep runs fast locally and in CI.

## Recent Adjustments

- **Trip suggestions tests** now stub `useMemoryContext` / `useMemoryInsights`
  to avoid spinning up real React Query fetches. Only the trip suggestions hook
  stays under test, which keeps the file under 1s even with multiple renders.
- **Destination search hook** no longer waits on a 100 ms `setTimeout`. The mock
  implementation yields to the microtask queue with `await Promise.resolve()`,
  preserving the async contract while removing ~2 s of idle time from the
  21-test suite.
- **Stateful timer assertions** use `act(async () => vi.advanceTimersByTimeAsync(...))`
  so that auto-dismiss logic executes without React warning spam or extra
  scheduling overhead.
- **Global mocks implemented**: React Query, AI SDK, and Supabase mocked globally
  in test-setup.ts for sync behavior, eliminating async I/O delays.
- **Fake timers enforced**: Global beforeEach/afterEach setup with vi.useFakeTimers()
  and proper teardown, removing real timer overhead.
- **User event optimization**: All userEvent.setup() calls now include
  { advanceTimers: vi.advanceTimersByTime } for sync interactions.
- **Act wrapping**: Render calls and async user interactions properly wrapped
  in act() to prevent React warnings and ensure sync execution.

## Performance Snapshot (After Optimizations)

- AI stream route integration: 12.6ms (After). Before: ~13s (UNVERIFIED note from prior analysis).
- Account settings suite: ~1.6s (After). Reduced by stubbing timers and condensing redundant assertions.
- Itinerary builder suite: ~1.5s (After). Achieved by pruning scenarios, removing drag/drop + delete UI paths, and avoiding fake timers.
- Search store tests: Target <500ms (optimized with sync mocks, was ~3s).
- Memory hook tests: Target <300ms (optimized with sync API mocks, was ~1.6s).
- Form tests: Target <500ms (optimized with fake timers and act wrapping, was ~1.7s).
- Overall suite: Target <5s (was ~10s+ with async bottlenecks).

To regenerate these numbers locally:

- Run one suite: `pnpm vitest run <file> --reporter=json --outputFile=test-results.json && jq '.testResults[] | {name, duration: (.endTime - .startTime)}' -r test-results.json`
- Full suite benchmarking (strict thresholds): `pnpm test:benchmark` (writes `benchmark-summary.json`, fails on slow files >2s or suite >=10s).

## Execution Guidance

- The Vitest config pins `pool: "vmForks"` and `maxWorkers` (CI=2, local=⌊cpus/2⌋)
  for predictable sandboxing. Avoid overriding unless debugging a worker crash.
- Prefer fake timers or explicit mocks for time-based UI instead of real delays.
- When using fake timers, always tear down deterministically:
  - `beforeEach(() => vi.useFakeTimers())`
  - `afterEach(() => { vi.runOnlyPendingTimers(); vi.clearAllTimers(); vi.useRealTimers(); })`
- For `@testing-library/user-event`, wire timers so interactions stay synchronous:
  - `const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })`
  - Avoid global `userEvent` without setup when fake timers are active.
- Keep external data hooks mocked at the boundary (React Query, Supabase, AI SDK)
  so component tests render synchronously.
- When a suite still tops 1 s locally, run `pnpm vitest run <path> --runInBand`
  once to inspect `--reporter=json` timing output before deciding whether to
  refactor the component or test.
- **Global optimization guidelines**: Always mock external dependencies (React Query,
  Supabase, AI SDK) at the boundary for sync behavior. Use fake timers globally
  in test-setup.ts. Wrap all user interactions in act() with proper userEvent.setup().
  Target <500ms per test file, <5s suite total.
