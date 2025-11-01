# Frontend Vitest Modernization Triage (October 28, 2025)

This document captures the current backlog of failing Vitest suites, their feature alignment, and the proposed modernization action for each. Decisions reflect the final-only policy: legacy and deprecated behaviour will be removed instead of preserved.

## Legend

| Decision | Description |
|----------|-------------|
| **Rewrite** | Feature is still part of the shipping frontend; tests must be rewritten to match the modern implementation. |
| **Remove** | Feature/code path is deprecated or replaced; delete the suite and associated dead code. |
| **Pending** | Requires product/design confirmation before proceeding. |

## Triage Matrix

| Suite | Feature Area | Current Assessment | Decision | Notes |
|-------|--------------|--------------------|----------|-------|
| `src/hooks/__tests__/use-authenticated-api.test.tsx` | API client hook | Hook is actively used by `useApiQuery` and mutations | Rewrite ✅ | Rewritten on 2025-10-28 using typed Supabase mocks and shared render helpers. |
| `src/hooks/__tests__/use-api-query.test.tsx` | API query/mutation hooks | Validates query/mutation helpers powering the app | Rewrite | Update to harness utilities and controlled query helpers added in Phase 2. |
| `src/hooks/__tests__/use-supabase-query.test.tsx` | Supabase query hook | Hook exported from `src/hooks` in active use | Rewrite ✅ | Rewritten on 2025-10-28 using shared Supabase client mocks and controlled query helpers. |
| `src/hooks/__tests__/use-supabase-storage.test.tsx` | Supabase storage hook | Hook still referenced in storage flows | Rewrite ✅ | Rebuilt on 2025-10-28 using shared Supabase storage mocks and controlled query builders. |
| `src/stores/__tests__/api-key-store.test.ts` | Zustand API key store | Store drives `/api/keys` UI state | Rewrite | Replace legacy assertions with store snapshot helpers. |
| `src/stores/__tests__/deals-store.test.ts` | Deals store | Deals feature live in dashboard | Rewrite | Modernize to use typed selectors and frozen state checks. |
| `src/stores/__tests__/search-params-store.test.ts` | Search params store | Still consumed by search flows | Rewrite | Cover new param validation and resets. |
| `src/stores/__tests__/search-store.test.ts` | Search aggregate store | Active | Rewrite | Rebuild tests around async search orchestration (debounce, fetch pipeline). |
| `src/stores/__tests__/trip-store.test.ts` | Trip store | Utilized across dashboard | Rewrite | Use store harness to assert computed selectors. |
| `src/stores/__tests__/ui-store.test.ts` | UI state store | Acts as global UI context | Rewrite | Rewrite using store inspector helpers. |
| `src/components/api-key-management/__tests__/api-key-management.test.tsx` | API key management UI | Active admin UX | Rewrite | Pair with new `/api/keys` utilities; integrate TanStack Query mocks. |
| `src/components/chat/__tests__/chat-interface.test.tsx` | Chat interface | Chat feature active | Rewrite | Modernize around streaming + suspense patterns. |
| `src/components/error/__tests__/error-boundary.test.tsx` | Error boundaries | Core shell | Rewrite | Re-align with new logging, retry semantics, and session IDs. |
| `src/components/error/__tests__/error-fallback.test.tsx` | Error fallback UI | Core shell | Rewrite | Ensure copy and CTA flow matches current product spec. |
| `src/components/layouts/__tests__/chat-layout.test.tsx` | Chat layout | Layout still present | Rewrite | Update to new layout composition (suspense + cache components). |
| `src/components/ui/__tests__/error-boundary.test.tsx` | UI-level boundary | Duplicates global boundary | Pending | Confirm if component is still exported; remove if redundant. |
| `src/components/ui/__tests__/loading-skeletons.test.tsx` | Skeleton components | Still rendered in list views | Rewrite | Switch to snapshotless render checks + accessibility assertions. |
| `src/components/ui/__tests__/loading-spinner.test.tsx` | Loading spinner | Shared component | Rewrite | Minimal test verifying ARIA attrs only. |
| `src/components/ui/__tests__/loading-states.test.tsx` | Loading wrappers | Needs confirmation | Pending | Verify usage; decide rewrite vs removal. |
| `src/components/ui/__tests__/travel-skeletons.test.tsx` | Travel skeleton UI | Active in itinerary views | Rewrite | Validate skeleton semantics/ARIA. |
| `src/lib/api/__tests__/api-client.test.ts` | API client wrappers | Still exported | Rewrite | Update to new fetch + error handling. |
| `src/lib/schemas/__tests__/error-boundary.test.ts` | Schema validation | Used by error logging | Rewrite | Align with latest Zod schema definitions. |
| `src/lib/schemas/__tests__/memory.test.ts` | Memory data schemas | Feature active | Rewrite | Ensure tests reference current schema shape. |
| `src/lib/supabase/__tests__/client.test.ts` | Supabase client factory | Core infra | Rewrite | Modernize to match SSR client + caching strategy. |
| `src/app/auth/confirm/__tests__/route.test.ts` | Auth route | Active route | Rewrite | Update to match Next 16 route handlers. |
| `src/components/features/agent-monitoring/__tests__/agent-workflow.test.tsx` | Agent monitoring | Feature flagged? | Pending | Confirm product roadmap; remove if retired, otherwise rewrite. |
| `src/components/features/chat/__tests__/memory-context-panel.test.tsx` | Chat memory panel | Active | Rewrite | Focus on context selection interactions. |
| `src/components/features/profile/__tests__/profile-integration.test.tsx` | Profile integration | Active | Rewrite | Convert to integration harness with mocked API. |
| `src/components/features/dashboard/__tests__/recent-trips.test.tsx` | Dashboard widgets | Active | Rewrite | Align with new data hooks. |
| `src/components/features/dashboard/__tests__/trip-suggestions.test.tsx` | Dashboard suggestions | Active | Rewrite | Cover tanstack query usage. |
| `src/components/features/dashboard/__tests__/upcoming-flights.test.tsx` | Dashboard flights | Active | Rewrite | Validate flight cards + skeleton transitions. |
| `src/components/features/trips/__tests__/budget-tracker.test.tsx` | Budget tracker | Active | Rewrite | Replace brittle getByRole with scoped queries + currency formatting checks. |
| `src/components/features/search/__tests__/activity-card.test.tsx` | Activity card | Active | Rewrite | Assert new tooltip/CTA behaviour. |
| `src/components/features/search/__tests__/destination-card.test.tsx` | Destination card | Active | Rewrite | Cover image fallback + action buttons. |
| `src/components/features/search/__tests__/destination-search-form.test.tsx` | Destination search form | Active | Rewrite | Exercise validation + debounce. |
| `src/components/features/search/__tests__/flight-search-form.test.tsx` | Flight search form | Active | Rewrite | Align with new schema + multi-segment handling. |
| `src/components/features/search/__tests__/search-results.test.tsx` | Search results | Active | Rewrite | Validate empty/error states with new components. |

## Progress Log

- **2025-10-28** – Initial triage captured for all failing suites, highlighting rewrite vs remove candidates. Harness modernization (Phase 2) kicked off by refactoring `src/test/test-utils.tsx`, `src/test-setup.ts`, and typed Supabase/query helpers.
- **2025-10-28** – Replaced legacy mock helpers with typed implementations (`src/test/mock-helpers.ts`, `src/test/query-mocks.tsx`, `src/test/trip-store-test-helpers.ts`) and removed obsolete scaffolding to eliminate `any` usage and centralize Supabase stubs.
- **2025-10-28** – Completed modernization of `src/hooks/__tests__/use-authenticated-api.test.tsx`; suite now leverages the shared Supabase/query mocks and passes under Vitest.
- **2025-10-28** – Tightened Supabase and TanStack Query mocks to satisfy strict `tsc` signatures, refreshed `use-api-query` test harness to consume the new helpers, and cleared outstanding type-check blocks for Phase 2.
- **2025-10-28** – Rebuilt `src/hooks/__tests__/use-supabase-query.test.tsx` around the shared Supabase client factory and controlled query builders; suite passes under strict Vitest run.
- **2025-10-28** – Modernized `src/hooks/__tests__/use-supabase-storage.test.tsx` with the shared storage/client mocks, typed attachment fixtures, and controlled query builders; validated with targeted Vitest run.

## Next Actions

1. Confirm “Pending” entries with product/design stakeholders (agent monitoring, UI loading states/boundary). Update the matrix with final decisions.
2. Finalize shared testing harness cleanup (finish removing legacy mocks/`any` usage) so all rewrites can consume the same utilities before Phase 3.
3. Use this table to drive the rewrite backlog (Phase 3) once the shared testing harness is refreshed.
