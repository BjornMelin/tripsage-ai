# Standards

Single source for how we write TripSage code.

## TypeScript & Quality

- Strict typing: no `any`; handle `null`/`undefined` explicitly; type all params/returns; prefer narrow unions over broad strings.
- Prefer functions/components with clear props and return types; hooks use `use*` naming.
- Examples:

```ts
interface Trip {
  id: string;
  name: string;
  destinations: string[];
  status: "planning" | "booked" | "completed";
}

export function TripCard({ trip, onEdit }: { trip: Trip; onEdit: (id: string) => void }) {
  return (
    <div>
      <h3>{trip.name}</h3>
      <button onClick={() => onEdit(trip.id)}>Edit</button>
    </div>
  );
}
```

```ts
function useTrips() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchTrips = async () => {
    setLoading(true);
    try {
      const response = await api.getTrips();
      setTrips(response.data);
    } finally {
      setLoading(false);
    }
  };

  return { trips, loading, fetchTrips };
}
```

- Commands: `pnpm -C frontend biome:check`, `pnpm -C frontend biome:fix`, `pnpm -C frontend type-check`, `pnpm -C frontend test:run`.

## Import Paths

Semantic aliases (configured in `frontend/tsconfig.json`):

| Alias | Target | Use For |
| --- | --- | --- |
| `@schemas/*` | `./src/domain/schemas/*` | Zod/domain schemas |
| `@domain/*` | `./src/domain/*` | Domain logic |
| `@ai/*` | `./src/ai/*` | AI SDK tooling/models |
| `@/*` | `./src/*` | Generic src-root (lib, components, stores, hooks, app) |

Usage rules:

- Use aliases when crossing feature/architecture boundaries or importing schemas from anywhere.
- Use relative paths (`./`, `../`) within the same small feature tree (≤2 levels) for clarity.
- Disallowed: `@/domain/*`, `@/ai/*`, `@/domain/schemas/*`.

Examples:

```ts
// Correct
import { accommodationSchema } from "@schemas/accommodations";
import { AccommodationsService } from "@domain/accommodations/service";
import { createAiTool } from "@ai/lib/tool-factory";
import { createServerSupabase } from "@/lib/supabase/server";

// Correct relative within feature
import { AMADEUS_DEFAULT_BASE_URL } from "./constants";

// Incorrect (alias misuse)
// import { AccommodationsService } from "@/domain/accommodations/service";
```

Migration checklist for new imports:

1) Decide boundary: schema → `@schemas/*`; domain → `@domain/*`; AI → `@ai/*`; generic → `@/*`.
2) If same feature folder and short path, prefer relative.
3) Verify alias exists in `tsconfig` and `vitest.config.ts`.
4) Run `pnpm biome:check` to catch violations.
5) Do not add new imports from `@/lib/providers/registry`; use `@ai/models/registry` (shim removal planned).

Troubleshooting: restart TS server, confirm path mapping, run `pnpm type-check` for detailed errors.

## Code Style

- Formatter/linter: Biome. Use `pnpm biome:fix` to apply fixes; `pnpm format:biome` for formatting only.
- Keep schemas, types, and exports documented with concise JSDoc when public.

## Zod Schemas (v4)

- Single source per domain under `@schemas/*`; co-locate tool input schemas with the domain file when specific, but prefer shared domain files when consumed by multiple layers (route + tool + UI). Use section markers (`// ===== CORE SCHEMAS =====`, `// ===== TOOL INPUT SCHEMAS =====`).
- Use `z.strictObject`/`z.looseObject`; `z.enum(MyEnum)` for TS enums; `z.number().int()` for ints; prefer `.nullable()` over `.optional()` for strict tool inputs; avoid deprecated Zod 3 APIs.
- Use `.refine`/`.superRefine` for invariants (e.g., checkout after checkin); prefer `.transform` for normalization rather than ad-hoc post-processing.
- Error messages use `{ error: "..." }` (no deprecated `message` fields).
- Pair schema and inferred type in the same file:

```ts
export const userSchema = z.strictObject({ id: z.string().uuid(), email: z.string().email() });
export type User = z.infer<typeof userSchema>;
```

- Registry helpers: use `primitiveSchemas`, `transformSchemas`, `refinedSchemas` from `@schemas/registry`.
- Tool schemas (AI SDK v6): include `.describe()` on fields, `z.strictObject` inputs, `temperature: 0` for tool calls.

## Architecture & Services

- Keep business logic in service/handler functions, wrapped with `withTelemetrySpan`; avoid module-scope state in route handlers.
- Example service pattern with DI + telemetry:

```ts
import { withTelemetrySpan } from "@/lib/telemetry/span";

interface ServiceDeps {
  db: DatabaseService;
  cache: CacheService;
  externalApi: ExternalApiService;
  rateLimiter?: RateLimiter;
}

export class TripService {
  constructor(private readonly deps: ServiceDeps) {}

  async createTrip(tripData: TripData, userId: string) {
    return withTelemetrySpan("trip.create", { attributes: { userId } }, async () => {
      // business logic
    });
  }
}
```

- Logging/telemetry: use `@/lib/telemetry/{span,logger}` only; no `console.*` in server code (tests/client-only UI allowed).

## Security & Validation

- Validate all external inputs with Zod before use.
- Use `withApiGuards` and `createServerSupabase` for authenticated routes; keep auth in handlers, not in helpers.
- Sensitive actions (MFA backup codes, credential changes, BYOK operations) must enforce step-up MFA: call `requireAal2()` before the action and return `mfa_required` on failure.
- Record security-sensitive recovery events: backup code regeneration/consumption must log via `mfa_backup_code_audit` (metadata only, never the code value).
- Example input validation:

```ts
import { z } from "zod";
import { primitiveSchemas } from "@schemas/registry";

const tripCreateSchema = z.strictObject({
  title: primitiveSchemas.nonEmptyString.max(200),
  destination: primitiveSchemas.nonEmptyString.max(200),
  startDate: z.string(),
  endDate: z.string(),
  budget: primitiveSchemas.nonNegativeNumber.optional(),
  travelers: primitiveSchemas.positiveNumber.int().default(1),
});
```

- Auth wrapper example:

```ts
import { NextResponse } from "next/server";
import { withApiGuards } from "@/lib/api/factory";

export const GET = withApiGuards({
  auth: true,
  rateLimit: "trips:list",
  telemetry: "trips.list",
})(async (_req, { supabase, user }) => {
  const { data } = await supabase.from("trips").select("*").eq("user_id", user!.id);
  return NextResponse.json(data);
});
```

## Zustand Stores

- Small stores (<300 LOC): single file with middleware (`devtools`, `persist`).
- Large stores: use slice composition (`stores/<feature>/*`), compose in `index.ts`, expose selective exports only.
- Architecture pattern for composed stores:

```text
stores/auth/
├── auth-core.ts       # core state/actions
├── auth-session.ts    # session flows (login/logout/refresh)
├── auth-validation.ts # validation logic
├── reset-auth.ts      # reset utilities
└── index.ts           # unified store composition + exports
```

Core slice example:

```ts
import { StateCreator } from "zustand";

export interface AuthCore {
  user: User | null;
  isLoading: boolean;
  error: string | null;
}

export interface AuthCoreActions {
  setUser: (user: User | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export type AuthCoreSlice = AuthCore & AuthCoreActions;

export const createAuthCoreSlice: StateCreator<AuthCoreSlice> = (set) => ({
  user: null,
  isLoading: false,
  error: null,
  setUser: (user) => set({ user }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
});
```

Unified store with middleware:

```ts
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { createAuthCoreSlice } from "./auth-core";
import { createAuthSessionSlice } from "./auth-session";
import { createAuthValidationSlice } from "./auth-validation";

type AuthStore = AuthCoreSlice & AuthSessionSlice & AuthValidationSlice;

export const useAuthStore = create<AuthStore>()(
  devtools(
    persist(
      (...args) => ({
        ...createAuthCoreSlice(...args),
        ...createAuthSessionSlice(...args),
        ...createAuthValidationSlice(...args),
      }),
      { name: "auth-store", partialize: (state) => ({ user: state.user }) }
    ),
    { name: "AuthStore" }
  )
);
```

- Helpers: `resetStore`, `setupTimeoutMock`, `waitForStoreState` from `@/test/helpers/store` for tests.
- Selectors: expose derived selectors for complex state; avoid broad subscriptions to minimize re-renders.

### Computed Middleware

For stores with complex derived state (aggregations, validation flags, counts), use the `withComputed` middleware:

```ts
import { withComputed, createComputeFn } from '@/stores/middleware/computed';

const computeFilterState = createComputeFn<FilterState>({
  activeFilterCount: (state) => Object.keys(state.activeFilters || {}).length,
  hasActiveFilters: (state) => Object.keys(state.activeFilters || {}).length > 0,
});

export const useFilterStore = create<FilterState>()(
  devtools(
    persist(
      withComputed(
        { compute: computeFilterState },
        (set) => ({
          activeFilters: {},
          activeFilterCount: 0,
          hasActiveFilters: false,
          // ... actions
        })
      ),
      { name: 'filter-store' }
    )
  )
);
```

Do not persist computed fields — configure `persist` with `partialize` to omit derived keys (e.g., `activeFilterCount`, `hasActiveFilters`) so they are recomputed on hydration.

**When to use**:

- Aggregations from collections (counts, sums, filters)
- Multi-property derived flags (form validation, UI states)
- Expensive computations needed by multiple components

**When NOT to use**:

- Simple property access (use selectors)
- Rarely-accessed values (compute on-demand with `useMemo`)
- Values dependent on React props/context

**Performance**: Compute functions run on every state update. Keep them O(1) or O(n) with small n. See [Zustand Computed Middleware Guide](./zustand-computed-middleware.md) for detailed patterns, examples, and performance considerations.

## Performance

- Databases: add indexes for frequent lookups; avoid N+1s; favor streaming/pagination.
- Caching: cache expensive operations with clear TTLs and invalidation rules (Upstash Redis); invalidate on writes.
- Async: use async/await for I/O; avoid blocking calls; handle errors explicitly.
- Frontend/state: batch state updates; avoid global fake timers; keep test fixtures minimal.

## Code Review Checklist

- [ ] Tests pass and are meaningful; coverage meets targets.
- [ ] Types are explicit; no `any`; imports follow alias rules.
- [ ] Lint/format/type-check scripts pass.
- [ ] Security: inputs validated; auth handled; secrets not logged.
- [ ] Performance: no obvious N+1, cache misuse, or blocking I/O.
- [ ] Docs updated if behavior/contract changes.

## Additional Store Practices

- For shared patterns, use helpers from `@/lib/stores/helpers` (loading/error state creators) instead of duplicating logic.
- Prefer selectors modules for derived views (e.g., `stores/trip/selectors.ts`) to keep components lean and memoized.
- Persist only the minimal subset of state; configure `partialize` in `persist` middleware.
