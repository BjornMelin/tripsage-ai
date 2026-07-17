# Validate performance

TripSage treats performance claims as measured evidence, not fixed repository constants. Results vary with the runner, cache state, dataset, and deployment.

## Monitor performance

Measure application behavior and development workflow costs under controlled conditions.

### Key indicators

- Build and type-check duration
- Route and upstream API latency
- Client bundle size and Core Web Vitals
- Search, streaming, and vector-query throughput

### Measure locally

```bash
# Build performance
time pnpm build

# Type checking
time pnpm type-check

# Bundle analysis
pnpm build:analyze
```

Record the commit, command, environment, dataset, cache state, and raw output with every result. Do not compare measurements collected under different conditions as if they shared a baseline.

## Regression prevention

Use CI for deterministic quality checks. Use controlled workloads for application performance measurements.

### Current quality gates

- Production build and type checking
- Affected tests on pull requests
- Full sharded coverage on `main`
- Critical browser and Content Security Policy smoke tests when relevant
- Operation-level schema performance assertions in `pnpm test:schemas`

CI does not currently enforce a synthetic application-performance budget. The test-suite wall clock is not an application performance metric and is not used as one. Add a blocking budget only after a purpose-built workload establishes a stable baseline. Collect enough comparable samples to measure variance first.

Publish runtime performance claims only with a dated, reproducible environment, dataset, command, and raw result artifact.
