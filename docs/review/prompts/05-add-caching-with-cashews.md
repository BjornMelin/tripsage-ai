# Implementation Prompt: Add Route-Level Caching with cashews 7.4.0 and Upstash Redis 1.35.6 (Performance Optimization)

**Objective:** Implement efficient route-level caching on all GET endpoints using cashews 7.4.0 (fastapi-cache2) with Upstash Redis 1.35.6 backend (TTL=300s), integrated with Supabase 2.76.1 for Redis add-on, ensuring cache invalidation on mutations and compatibility with async FastAPI 0.119.0 without affecting RLS or auth.

## Detailed Instructions  

1. **File to Modify/Delete:** `tripsage/api/main.py`  
   * **Action:** Install and configure cashews 7.4.0 cache backend with Upstash Redis 1.35.6, setting up startup event for initialization and ensuring async compatibility.  
   * **Specifics:** If not in deps, add to pyproject.toml: "fastapi-cache2>=0.2.1" (uses cashews 7.4.0). Imports: `from fastapi_cache import FastAPICache; from fastapi_cache.backends.redis import RedisBackend; from fastapi_cache.decorator import cache; from cashews import RedisCache; import aioredis; import os; from fastapi import FastAPI;`. Startup: `@app.on_event("startup") async def startup(): redis = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379")); cache_backend = RedisCache(redis_url=os.getenv("REDIS_URL")); FastAPICache.init(backend=cache_backend, prefix="fastapi-cache");` (docs: github.com/long2ice/fastapi-cache2; Upstash Redis 1.35.6: supabase.com/docs/guides/database/redis or upstash.com/docs/redis/sdks/python; URL: redis://[user]:[pass]@[host]:[port]). Ensure async (aioredis 2.0+ under cashews).  
   * **Action:** Decorate all read-only GET endpoints with cache (expire=300s TTL), and add invalidation on mutations (POST/PUT/DELETE).  
2. **File to Modify/Delete:** `frontend/src/lib/query-provider.tsx` (enhance for cache awareness)  
   * **Action:** Configure TanStack Query 5.90.5 to respect backend cache (staleTime=300000ms matching TTL) and invalidate on mutations.  
   * **Specifics:** In QueryClient: `defaultOptions: { queries: { staleTime: 300000, // 5min matching backend TTL gcTime: 600000, // 10min retry: (failureCount, error) => error.message.includes('401') ? false : failureCount < 3, } }` (docs: tanstack.com/query/v5/docs/react/guides/important-defaults). In mutations: `onSuccess: () => queryClient.invalidateQueries({ queryKey: ['trips'], exact: false });` (refetchType='none' if backend cached).  

## Code Quality & Standards Enforcement  

After making the code changes, you must perform the following:  

* Run `ruff format .` and `ruff check --fix .` to apply auto-formatting and linting across all directories (docs: docs.astral.sh/ruff; rules: E4,E7,E9,F,I,UP,ARG,LOG,TRY,PERF for caching/perf; target-version="py313"; fixable=["ALL"]).  
* Run `pylint tripsage_core/ tripsage/` and resolve **100%** of all reported errors and warnings in backend (pyproject.toml: score=true); for frontend, run `biome check src --apply` (docs: biomejs.dev; no cache key issues).  
* Ensure all new/modified functions/methods have strict, complete type hints (Python: `typing`/`AsyncSession`/`RedisCache`; TS: `Trip[]` from Zod).  
* Ensure all public functions, methods, classes, and components have Google-style docstrings (Python) or JSDoc (frontend), with exactly one blank line after the closing `"""` or `*/` (Ruff D: "google").  

## Testing Requirements  

1. **Delete Obsolete Tests:** Delete any manual cache tests if existing (e.g., `tests/tripsage/api/test_cache.py` if custom).  
2. **Rewrite/Update Tests:** Open `tests/tripsage/api/test_trips.py` (Pytest 8.4.2) and add caching tests: `import pytest; from fastapi.testclient import TestClient; from unittest.mock import patch; @pytest.mark.asyncio async def test_get_trips_cached(client: TestClient, mock_user): with patch('fastapi_cache.backends.redis.RedisBackend.get') as mock_get, patch('fastapi_cache.backends.redis.RedisBackend.set') as mock_set: # First call sets cache response1 = client.get("/trips", headers={"Authorization": f"Bearer {mock_user.token}"}); assert response1.status_code == 200; mock_set.assert_called_once(); # Second call hits cache response2 = client.get("/trips", headers={"Authorization": f"Bearer {mock_user.token}"}); assert response2.status_code == 200; mock_get.assert_called_once(); # Invalidation on POST response_post = client.post("/trips", json={"title": "Test"}, headers={"Authorization": f"Bearer {mock_user.token}"}); assert response_post.status_code == 201; # Clear called await FastAPICache.clear.assert_called();` (use pytest-mock 3.15.1; fakeredis 2.32.0 for Redis mock; pytest-httpx for async). In `frontend/src/__tests__/query.test.ts` (Vitest 4.0.1), test cache/stale: `test('query staleTime and invalidation', async () => { vi.useFakeTimers(); const { result } = renderHook(() => useInfiniteTrips()); await waitFor(() => expect(result.current.isSuccess).toBe(true)); // Initial fetch vi.advanceTimersByTime(300000); // 5min stale expect(result.current.isStale).toBe(false); // Not stale yet const { mutate } = useCreateTripMutation(); await mutate({ title: 'Invalidate' }); expect(result.current.queryClient.invalidateQueries).toHaveBeenCalledWith({ queryKey: ['trips'] }); vi.useRealTimers(); });` (mock fetch/timer; docs: vitest.dev/guide/timers). Playwright 1.56.1 E2E: `test('caching reduces fetches', async ({ page, context }) => { const metricsPage = context.newPage(); await metricsPage.route('**/api/trips', route => route.fulfill({ status: 200, body: JSON.stringify([{ id: 1 }]) })); await page.goto('/trips'); // First load await expect(page.locator('[data-status]')).toBeVisible(); // Second load (same page) await page.reload(); await expect(page.locator('[data-status]')).toBeVisible(); // No new fetch (cache hit) expect(metricsPage.routeFetches('**/api/trips')).toBe(1); // Only once });` (docs: playwright.dev/docs/test-essentials; mock route for fetch count).  
3. **Verify Coverage:** Run `pytest tripsage_core/ tripsage/ --cov` (90%+ thresholds, report html/xml) and `vitest run --coverage` (95%+ thresholds, v8, reporter html/json); ensure >95% coverage for caching paths (mock Redis/FastAPICache in Pytest/Vitest).  
4. **All Tests Must Pass:** Confirm the entire test suite runs to 100% completion without failures, including smoke tests (e.g., Playwright: load trips twice → 1 fetch; Vitest: mutate invalidates cache; Pytest: GET sets cache, POST clears).  

## Documentation Updates  

1. **README.md:** Add 'Caching' section: "Route-level caching via cashews 7.4.0 (fastapi-cache2) on GETs (expire=300s TTL); Upstash Redis 1.35.6 backend (redis://url); invalidation on mutations (FastAPICache.clear(namespace)); TanStack Query staleTime=300000ms syncs with backend." Example: "@router.get('/trips', cache=cache, expire=300) async def get_trips(...): ...".  
2. **CHANGELOG.md:** Add under "Performance":  

   ```markdown  
   - **[Caching Implementation]:** Added cashews 7.4.0 route caching (TTL=300s) with Upstash Redis 1.35.6 on all GETs; mutations invalidate (clear namespace); integrated with async FastAPI 0.119.0 and Supabase RLS, reducing DB hits by 80%.  
   ```  

3. **docs/architecture.md:** Diagram: "sequenceDiagram; Client->>API: GET /trips (Token); API->>Cache: Check Key (user_id+params); Cache->>Client: Hit (TTL=300s); Alt Miss; API->>DB: Async Query (Eager); DB->>Cache: Set; Cache->>Client: Data; End; Mutation->>Cache: Clear (invalidate);".

## Verification  

GET endpoints cache (second call <10ms, no DB query via logs); mutations invalidate (post-cache clear, next GET refetches); Upstash metrics show TTL=300s hits (80%+); RLS unaffected (unauth 403); Ruff/Biome clean; Vitest/Playwright/Pytest pass with 95%+ coverage (mocks for Redis/FastAPICache/fetch). Run app and curl GET twice (time diff verifies cache).
