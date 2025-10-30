# Implementation Prompt: Implement TanStack Query 5.90.5 Mutations with Optimistic Updates and Scopes (Frontend Data Fetching Optimization)

**Objective:** Migrate all frontend data fetching and mutations to TanStack React Query 5.90.5 with optimistic updates, serial scopes for concurrent safety, infinite queries for lists, and persistQueryClient for offline support, integrating Supabase 2.76.1 auth tokens and Zod 4.1.12 parsing for type-safe async flows.

## Detailed Instructions  

* **Action:** Replace native fetch/useState with TanStack Query 5.90.5 hooks for mutations and infinite queries, adding optimistic UI updates and Supabase auth integration.  

1. **File to Modify/Delete:** `frontend/src/lib/query-provider.tsx` (create if missing)  
   * **Action:** Wrap app with QueryClientProvider and configure defaults for staleTime, retries, and Supabase auth persistence.  
   * **Specifics:** `import { QueryClient, QueryClientProvider } from '@tanstack/react-query'; import { ReactQueryDevtools } from '@tanstack/react-query-devtools'; const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 5 * 60 * 1000, gcTime: 10 * 60 * 1000, retry: (failureCount, error) => { if (error.message.includes('401')) return false; return failureCount < 3; }, }, mutations: { retry: 1, }, } }); export function QueryProvider({ children }: { children: React.ReactNode }) { return ( <QueryClientProvider client={queryClient}> {children} <ReactQueryDevtools initialIsOpen={false} /> </QueryClientProvider> ); }` (docs: tanstack.com/query/v5/docs/react/guides/important-defaults; devtools from @tanstack/react-query-devtools 5.90.2). In layout.tsx: `<QueryProvider><Component {...pageProps} /></QueryProvider>;`.  

## Code Quality & Standards Enforcement  

After making the code changes, you must perform the following:  

* Run `ruff format .` and `ruff check --fix .` to apply auto-formatting and linting across all directories (docs: docs.astral.sh/ruff; rules: E4,E7,E9,F,I,UP,ARG,LOG,TRY,PERF for async/perf; target-version="py313"; fixable=["ALL"]).  
* Run `pylint tripsage_core/ tripsage/` and resolve **100%** of all reported errors and warnings in backend (pyproject.toml: score=true); for frontend, run `biome check src --apply` (docs: biomejs.dev; strict no unused hooks).  
* Ensure all new/modified functions/methods have strict, complete type hints (Python: `typing`/`AsyncSession`; TS: `TripCreate` from Zod `z.infer`, async/await in mutationFn).  
* Ensure all public functions, methods, classes, and components have Google-style docstrings (Python) or JSDoc (frontend), with exactly one blank line after the closing `"""` or `*/` (Ruff D: "google").  

## Testing Requirements  

1. **Delete Obsolete Tests:** Delete `frontend/src/__tests__/fetch-api.spec.ts` and any native fetch tests in `tests/frontend/old-fetch.py` (if exists).  
2. **Rewrite/Update Tests:** Open `frontend/src/__tests__/trips.test.ts` (Vitest 4.0.1) and add mutation/infinite tests: `import { renderHook, waitFor } from '@testing-library/react'; import { vi } from 'vitest'; import { useCreateTripMutation, useInfiniteTrips } from '@/hooks/trips'; vi.mock('@supabase/auth-helpers-nextjs', () => ({ useSupabaseClient: vi.fn(() => ({ auth: { getSession: vi.fn(() => ({ data: { session: { access_token: 'mock' } } })) } })), })); vi.mock('next/navigation'); global.fetch = vi.fn(); test('createTripMutation optimistic', async () => { const { result } = renderHook(() => useCreateTripMutation()); const mockData = { id: 1, title: 'Test', status: 'active' }; (global.fetch as any).mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockData) }); await result.current.mutate({ title: 'Test' }); await waitFor(() => { const data = result.current.queryClient.getQueryData(['trips']); expect(data?.[data.length - 1].status).toBe('pending'); // Optimistic }); expect(global.fetch).toHaveBeenCalledWith('/api/trips', expect.objectContaining({ headers: { Authorization: 'Bearer mock' } })); }); test('infiniteTrips pagination', async () => { const { result } = renderHook(() => useInfiniteTrips()); const mockPage1 = [{ id: 1 }]; const mockPage2 = [{ id: 2 }]; (global.fetch as any).mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockPage1) }).mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(mockPage2) }); await waitFor(() => expect(result.current.data?.pages[0]).toEqual(mockPage1)); result.current.fetchNextPage(); await waitFor(() => expect(result.current.data?.pages[1]).toEqual(mockPage2)); expect(result.current.hasNextPage).toBe(false); // No more pages });` (docs: vitest.dev/guide/testing-library; mock fetch for async, globals: true). For backend integration, Pytest 8.4.2: `@pytest.mark.asyncio async def test_async_endpoint(db_session: AsyncSession): stmt = select(TripDB).options(selectinload(TripDB.user)); result = await db_session.execute(stmt); assert len(result.scalars().all()) == 0; # Eager: no additional queries` (pytest-asyncio 1.2.0). Playwright 1.56.1 E2E: `test('mutation with optimistic UI', async ({ page }) => { await page.goto('/trips'); const beforeCount = await page.locator('[data-status]').count(); await page.click('button[aria-label="Add Trip"]'); await page.fill('#trip-title', 'Optimistic Test'); await page.click('button[type="submit"]'); await expect(page.locator('[data-status="pending"]')).toBeVisible(); // Optimistic await page.waitForSelector('[data-status="active"]', { state: 'visible' }); // Success await expect(page.locator('[data-status]').locator('text=Optimistic Test')).toBeVisible(); expect(await page.locator('[data-status]').count()).toBe(beforeCount + 1); });` (docs: playwright.dev/docs/test-essentials; trace for perf).  
3. **Verify Coverage:** Run `pytest tripsage_core/ tripsage/ --cov` (pytest-cov 7.0.0; 90%+ thresholds, report html/xml/term-missing, cov-branch, fail-under=90) and `vitest run --coverage` (Vitest 4.0.1; 95%+ thresholds, v8 provider, reporter text/html/json, include src/**/*.{ts,tsx}); ensure >95% coverage for modified paths and integrations (mock fetch/Supabase in Vitest, async db in Pytest).  
4. **All Tests Must Pass:** Confirm the entire test suite (backend + frontend) runs to 100% completion without failures, including API-to-UI smoke tests (e.g., Playwright: add trip → optimistic pending → success active; Vitest: mutate with token, optimistic data, invalidate; Pytest: async execute with selectinload called once).  

## Documentation Updates  

1. **README.md:** Update 'Frontend Data Fetching' section to describe TanStack Query 5.90.5 integration: "Mutations with optimistic updates (onMutate pending UI, onSuccess invalidate), serial scopes (id: 'create-trip'), infinite queries (getNextPageParam for pagination), persistQueryClient (localStorage offline); Supabase token in headers; Zod parsing post-fetch." Include example: "useMutation({ mutationFn: async (data) => fetch('/api/trips', { headers: { Authorization: `Bearer ${token}` } }), onMutate: ... });".  
2. **CHANGELOG.md:** Add the following entry under a "Refactor" section:  

   ```markdown  
   - **[Frontend Mutations & Queries]:** Migrated to TanStack Query 5.90.5 with optimistic updates, scopes for serial, infinite pagination, persistQueryClient offline, and Zod 4.1.12 parsing; integrated Supabase 2.76.1 tokens, reducing duplicate fetches by 50% and enabling instant UI.  
   ```  

3. **docs/architecture.md:** Add caching/mutation flow diagram: "sequenceDiagram; User->>UI: Click Add Trip; UI->>QueryClient: onMutate (optimistic pending); UI->>API: POST /trips (Bearer Token); API->>Supabase: RLS Check; Supabase->>DB: Async Insert; DB->>API: Trip; API->>UI: Success; UI->>QueryClient: onSuccess (invalidate, refetchType='none'); QueryClient->>localStorage: Persist (offline);".

## Verification  

Mutations optimistic (UI shows pending pre-response, rollback on error); infinite loads next page (fetchNextPage called, hasNextPage false at end); persist works (localStorage has dehydrated state, rehydrates on reload); Supabase token in headers (Vitest mock verifies); no duplicate fetches (staleTime 5min); Ruff/Biome clean; Vitest/Playwright/Pytest pass with 95%+ coverage (mocks for fetch/Supabase). Run `npm run dev` and test add trip (instant UI, offline reload shows data).
