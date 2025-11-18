# Code Metrics

TripSage code metrics and analysis reports.

## Current Metrics

### API Routes

| Metric | Value | Notes |
|--------|-------|-------|
| Total routes | 38 | All route.ts files in src/app/api/ |
| Factory adoption | 35/38 (92%) | Routes using withApiGuards |
| Inline auth patterns | 4 routes | Routes with supabase.auth.getUser |
| Inline rate limiting | 1 route | Routes with new Ratelimit |

### Code Volume

| Component | Lines of Code | Files | Notes |
|-----------|---------------|-------|-------|
| API routes | 3,969 | 38 | Total in route.ts files |
| Store files | 10,046 | 15 | All .ts files in `src/stores/` |
| Factory implementation | 221 | 1 | `src/lib/api/factory.ts` |

### Test Status

| Suite | Status | Notes |
|-------|--------|-------|
| Unit + integration | Failing | 2,526 tests currently failing |
| API route tests | Failing | Environment issues and assertion mismatches |
| Store tests | Failing | Environment issues and assertion mismatches |

## Quality Gates

- `pnpm type-check`
- `pnpm biome:check`
- `pnpm test:run` (currently failing)
- `pnpm test:coverage` (blocked by failures)

## Architecture Metrics

### Factory Pattern Adoption

- **Target**: 100% of standard routes
- **Current**: 92% (35/38 routes)
- **Exceptions**: 3 routes (webhooks, background jobs)

### Store Composition

- **Slices**: 8 store modules split into slices
- **Pattern**: Core/feature separation
- **Testing**: Centralized utilities in src/test/

### Code Organization

- **Imports**: Direct from slice modules
- **Barrels**: No export * patterns
- **Dependencies**: Minimal custom code, prefer libraries
