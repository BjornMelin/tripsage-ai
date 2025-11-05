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

## Execution Guidance

- The Vitest config pins `pool: "vmForks"` and `maxWorkers` (CI=2, local=⌊cpus/2⌋)
  for predictable sandboxing. Avoid overriding unless debugging a worker crash.
- Prefer fake timers or explicit mocks for time-based UI instead of real delays.
- Keep external data hooks mocked at the boundary (React Query, Supabase, AI SDK)
  so component tests render synchronously.
- When a suite still tops 1 s locally, run `pnpm vitest run <path> --runInBand`
  once to inspect `--reporter=json` timing output before deciding whether to
  refactor the component or test.
