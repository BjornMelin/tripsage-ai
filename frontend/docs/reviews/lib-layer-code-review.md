# `src/lib` Layer Code Review

**Date:** 2025-11-24  
**Reviewer Role:** Senior Staff Code Reviewer for Next.js 16 Lib Layer  
**Scope:** `frontend/src/lib/**`

---

## 1. High-Level Summary

### Letter Grades

| Category | Grade | Notes |
|----------|-------|-------|
| **Architecture** | B+ | Good separation of concerns, clear server/client boundaries, some redundancy |
| **Type Safety** | B | Strong Zod usage, but scattered `any` and `unknown` casts without validation |
| **Correctness & Safety** | B+ | Proper `server-only` guards, good error handling, some runtime edge cases |
| **Testability** | B- | DI patterns present in some modules, but singletons hinder isolation |

### Strongest Aspects

1. **Environment validation** (`src/lib/env/`) is exemplary—Zod schemas with server/client separation, `server-only` guards, lazy validation with caching. The proxy-based `env` export is elegant.

2. **Telemetry abstraction** (`src/lib/telemetry/`) correctly isolates OpenTelemetry details behind `withTelemetrySpan()`, `withTelemetrySpanSync()`, and `createServerLogger()`.

3. **Supabase SSR integration** (`src/lib/supabase/`) follows `@supabase/ssr` patterns correctly with proper server/client separation and factory pattern.

4. **Rate limiting registry** (`src/lib/ratelimit/routes.ts`) provides a single source of truth with proper typing via `satisfies`.

### Weakest Aspects

1. **Dual-format field naming** in `schema-adapters.ts` and `trips-repo.ts` maintains both `snake_case` and `camelCase` versions of every field, creating maintenance burden and type confusion.

2. **Query factories** (`query-factories.ts`) use `unknown` return types extensively with placeholder `{} as QueryClient` patterns that fail at runtime.

3. **Error service singleton** (`error-service.ts`) accesses browser globals that create SSR hydration risks.

4. **Inconsistent client/server boundaries**: `utils.ts` mixes browser-safe with browser-only utilities.

---

## 2. Directory-by-Directory Review

### `src/lib/env`

**Purpose:** Centralized environment variable validation with Zod schemas.

| File | Issue | Suggested Fix |
|------|-------|---------------|
| `server.ts:14-15` | Module-level mutable state hinders test isolation | Export `resetEnvCache()` for tests |
| `client.ts:34-43` | Silent fallback to empty strings masks errors | Log warning but still throw |
| `schema.ts:140-162` | Production validation loses granularity | Use `.superRefine()` with individual issues |

### `src/lib/supabase`

**Purpose:** Supabase client factories for SSR, browser, and middleware contexts.

| File | Issue | Suggested Fix |
|------|-------|---------------|
| `client.ts:31-35` | SSR returns `{} as TypedSupabaseClient` | Return `null` and handle explicitly |
| `client.ts:13` | Module-level singleton blocks test isolation | Use factory with optional singleton |
| `factory.ts:302-306` | Silent catch in cookie adapter | Log at debug level via telemetry |

### `src/lib/api`

**Purpose:** HTTP client with validation, route helpers, error types.

| File | Issue | Suggested Fix |
|------|-------|---------------|
| `api-client.ts:183-194` | Complex base URL with multiple fallbacks | Use only `getClientEnvVarWithFallback()` |
| `api-client.ts:808-823` | Module-level singleton with side effects | Export factory function |
| `route-helpers.ts:186-202` | `checkAuthentication()` uses `unknown` | Accept `TypedServerSupabase` |
| `error-types.ts:163-181` | Type guards use `instanceof` | Use discriminant property pattern |

### `src/lib/telemetry`

**Purpose:** OpenTelemetry integration for spans, events, logging.

| File | Issue | Suggested Fix |
|------|-------|---------------|
| `span.ts:55-62` | Module-level `tracerRef` singleton | Accept tracer as parameter |
| `alerts.ts:47-48` | Uses `console.*` directly | Route through OTel span events |

### `src/lib/cache`

**Purpose:** Upstash Redis caching utilities.

| File | Issue | Suggested Fix |
|------|-------|---------------|
| `upstash.ts:46-50` | Silent JSON.parse failure | Return discriminated union with status |
| `upstash.ts:39-50` | Generic `T` without runtime validation | Accept optional Zod schema |

### `src/lib/repositories`

**Purpose:** Data access layer with Zod validation.

| File | Issue | Suggested Fix |
|------|-------|---------------|
| `trips-repo.ts:71` | Uses browser client for server-side repo | Import from `@/lib/supabase/server` |
| `trips-repo.ts:97-100` | `any` cast for query builder | Use proper generic constraints |
| `trips-repo.ts:28-52` | Maintains dual field names | Pick single format |

### `src/lib/schema-adapters.ts`

| Issue | Suggested Fix |
|-------|---------------|
| Every field duplicated in both formats | Choose single format; transform at API boundary |
| Non-deterministic destination IDs | Use stable ID from backend or UUID |
| `validateTripForApi()` duplicates Zod validation | Use single Zod schema |

### `src/lib/query-factories.ts`

| Issue | Suggested Fix |
|-------|---------------|
| `apiCall` parameters typed as `unknown[]` | Use generics for type safety |
| `{} as QueryClient` placeholders | Require QueryClient injection |
| Mutation factories lack type inference | Define explicit types per mutation |

### `src/lib/error-service.ts`

| Issue | Suggested Fix |
|-------|---------------|
| Direct `localStorage` and `navigator` access | Add `"use client"` directive |
| Module-level singleton instantiation | Export factory function |

### `src/lib/utils.ts`

| Issue | Suggested Fix |
|-------|---------------|
| `getSessionId()` uses `sessionStorage` | Move to client-specific module |
| `fireAndForget()` uses `console.warn` | Accept logger parameter |

---

## 3. Cross-Cutting Issues

### 3.1 Dual-Format Field Naming

**Where:** `schema-adapters.ts`, `trips-repo.ts`, `trip-store.ts`

**Consequences:** Types have redundant fields (`startDate` + `start_date`), easy to read wrong field, maintenance burden.

**Pattern:** Transform at API boundary only; use single camelCase format internally.

### 3.2 Module-Level Singletons

**Where:** `redis.ts`, `supabase/client.ts`, `telemetry/span.ts`, `tokens/budget.ts`

**Consequences:** Tests cannot isolate state; race conditions in concurrent tests.

**Pattern:** Export reset functions or use factory pattern with optional caching.

### 3.3 Inconsistent Error Types

**Where:** `route-helpers.ts`, `error-types.ts`, various route handlers

**Consequences:** Different error shapes from different routes; type guards don't work after serialization.

**Pattern:** Define canonical `ApiErrorResponse` shape; use discriminant properties.

### 3.4 Browser Globals in Shared Utilities

**Where:** `error-service.ts`, `utils.ts:getSessionId`

**Consequences:** SSR crashes or hydration mismatches.

**Pattern:** Separate client utilities with `"use client"` or guard with `typeof window`.

---

## 4. Top Recommendations

| # | Title | Severity | Effort | Impact |
|---|-------|----------|--------|--------|
| 1 | Eliminate dual-format field naming | High | Large | Reduces type confusion, halves payload sizes |
| 2 | Fix query factory type safety | High | Medium | Compile-time catch of type mismatches |
| 3 | Add client-only guards to browser modules | High | Small | Prevents SSR crashes |
| 4 | Improve testability of singleton modules | Medium | Medium | Enables proper test isolation |
| 5 | Consolidate error handling patterns | Medium | Medium | Consistent error handling |
| 6 | Add runtime validation to cache operations | Medium | Small | Catches corrupted cache data |

---

## 5. Execution Checklist

### High Priority

- [ ] `schema-adapters.ts`: Remove dual-format fields; keep only camelCase
- [ ] `query-factories.ts`: Add generic type parameters; remove `unknown` returns
- [ ] `query-factories.ts`: Remove `{} as QueryClient` placeholders
- [x] `error-service.ts`: Add `"use client"` directive ✅
- [x] `utils.ts`: Move `getSessionId()` to client-specific module ✅
- [x] `trips-repo.ts`: Handle nullable browser client ✅

### Medium Priority

- [x] `cache/upstash.ts`: Add optional Zod schema parameter (`getCachedJsonSafe`) ✅
- [x] `env/server.ts`: Export `resetEnvCache()` for test isolation ✅
- [x] `supabase/client.ts`: Return `null` instead of empty object on SSR ✅
- [x] `telemetry/alerts.ts`: Route through OTel in addition to console ✅
- [ ] `route-helpers.ts`: Type `checkAuthentication()` as `TypedServerSupabase`
- [ ] `agents/config-resolver.ts`: Use `ApiError` for 404 errors

### Low Priority

- [ ] `dates/unified-date-utils.ts`: Convert static classes to plain functions
- [ ] `memory/orchestrator.ts`: Accept adapter overrides in factory
- [ ] `tokens/budget.ts`: Add tokenizer reset capability for tests
- [ ] `payments/booking-payment.ts`: Add idempotency key handling

---

## 6. Summary

The `src/lib` layer is **well-architected overall** with proper server/client separation, good use of Zod for validation, and solid telemetry integration. The main technical debt is the dual-format field naming pattern that permeates the data layer, and the scattered use of module-level singletons that hinder testability.

**Immediate priorities:** Fix browser global usage in shared modules and add proper types to query factories to prevent runtime errors.

**Strategic priority:** Consolidate on single naming format (camelCase) with transformers at API boundaries to reduce maintenance burden and type confusion.

---

## 7. Quick Fixes Applied

The following quick wins were implemented during this review:

### Completed

1. **`error-service.ts`**: Added `"use client"` directive since it uses browser globals
2. **`utils.ts`**: Moved `getSessionId()` to `@/lib/client/session.ts` with deprecation re-export
3. **`env/server.ts`**: Added `resetEnvCache()` export for test isolation
4. **`supabase/client.ts`**: Changed to return `null` during SSR; added `useSupabaseRequired()` hook
5. **`cache/upstash.ts`**: Added `getCachedJsonSafe()` with optional Zod schema validation
6. **`telemetry/alerts.ts`**: Now records to OTel in addition to console (for distributed tracing)

### Additional Fixes (Cascading from supabase/client.ts change)

The `supabase/client.ts` change to return `null` during SSR required updates to all consumers:

**Hooks (now using `useSupabaseRequired()`):**
- ✅ `use-supabase-chat.ts` - Updated to use `useSupabaseRequired()`
- ✅ `use-supabase-storage.ts` - Updated to use `useSupabaseRequired()`
- ✅ `use-trips.ts` - Updated to use `useSupabaseRequired()`
- ✅ `use-realtime-channel.ts` - Added null check in useEffect guard

**Components (now handling null gracefully):**
- ✅ `realtime-auth-provider.tsx` - Added null guard with early return
- ✅ `login-form.tsx` - Changed to use `useSupabaseRequired()`
- ✅ `register-form.tsx` - Changed to use `useSupabaseRequired()`
- ✅ `calendar-connect-client.tsx` - Changed to use `useSupabaseRequired()`
- ✅ `trips/[id]/collaborate/page.tsx` - Added null guard in useEffect
- ✅ `chat/page.tsx` - Added null guard in `useCurrentUserId()`

**Tests:**
- ✅ `use-supabase-storage.test.tsx` - Added `useSupabaseRequired` to mock

### Pattern Reference
```typescript
// For hooks that require a client (throws during SSR)
const supabase = useSupabaseRequired();

// For hooks that need to handle SSR gracefully
const supabase = useSupabase();
useEffect(() => {
  if (!supabase) return; // SSR - skip
  // ... client-side logic
}, [supabase]);
```

---

## 8. Legacy/Dead Code Cleanup

The following legacy, deprecated, and test-only code was removed from production source files:

### Deprecated Code Removed
- **`utils.ts`**: Removed deprecated `getSessionId` re-export (consumers now use `@/lib/client/session` directly)

### Test-Only Exports Removed from Production Code
- **`telemetry/span.ts`**: Removed `setTelemetryTracerForTests()` and `resetTelemetryTracerForTests()` - not used anywhere
- **`supabase/client.ts`**: Removed `resetSupabaseClient()` - tests now use `vi.resetModules()` instead
- **`env/server.ts`**: Removed `resetEnvCache()` - not used in any tests
- **`supabase/index.ts`**: Removed `resetSupabaseClient` from public exports

### Test Files Updated
Tests that previously relied on test-only exports from production code were refactored to use proper test patterns:

- **`client.test.ts`**: Now uses `vi.resetModules()` with dynamic imports for module isolation
- **`factory.spec.ts`**: Removed telemetry reset calls; uses vi.mock instead
- **`redis.test.ts`**: Removed telemetry reset calls; tracer is fully mocked
- **`span.test.ts`**: Removed telemetry reset calls; tracer is fully mocked

### Consumer Files Updated
Files that imported deprecated exports were updated to use the canonical paths:
- `app/global-error.tsx` → imports `getSessionId` from `@/lib/client/session`
- `app/error.tsx` → imports `getSessionId` from `@/lib/client/session`
- `app/(auth)/error.tsx` → imports `getSessionId` from `@/lib/client/session`
- `app/(dashboard)/error.tsx` → imports `getSessionId` from `@/lib/client/session`
