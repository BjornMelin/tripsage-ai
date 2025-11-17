# Store Development

TripSage Zustand store patterns and composition guidelines.

## Store Architecture

### Single File Stores (<300 LOC)

For simple stores, use a single file with middleware:

```typescript
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";

interface UserStore {
  user: User | null;
  setUser: (user: User) => void;
  clearUser: () => void;
}

export const useUserStore = create<UserStore>()(
  devtools(
    persist(
      (set) => ({
        user: null,
        setUser: (user) => set({ user }),
        clearUser: () => set({ user: null }),
      }),
      { name: "user-store" }
    ),
    { name: "UserStore" }
  )
);
```

### Composed Stores (>500 LOC)

For complex stores, split into slices:

```text
stores/auth/
├── auth-core.ts      # Core state and actions
├── auth-session.ts   # Session management
├── auth-validation.ts # Validation logic
├── reset-auth.ts     # Reset utilities
└── index.ts          # Unified exports
```

## Slice Composition Pattern

### Core Slice (auth-core.ts)

```typescript
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

export const createAuthCoreSlice: StateCreator<
  AuthCoreSlice,
  [],
  [],
  AuthCoreSlice
> = (set) => ({
  user: null,
  isLoading: false,
  error: null,

  setUser: (user) => set({ user }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
});
```

### Feature Slice (auth-session.ts)

```typescript
import { StateCreator } from "zustand";
import type { AuthCoreSlice } from "./auth-core";

export interface AuthSessionActions {
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

export type AuthSessionSlice = AuthSessionActions;

export const createAuthSessionSlice: StateCreator<
  AuthCoreSlice & AuthSessionSlice,
  [],
  [],
  AuthSessionSlice
> = (set, get) => ({
  login: async (credentials) => {
    const { setLoading, setError, setUser } = get();
    try {
      setLoading(true);
      setError(null);
      const user = await loginApi(credentials);
      setUser(user);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  },

  logout: async () => {
    const { setUser } = get();
    await logoutApi();
    setUser(null);
  },

  refreshSession: async () => {
    const { setUser } = get();
    try {
      const user = await refreshSessionApi();
      setUser(user);
    } catch {
      setUser(null);
    }
  },
});
```

### Unified Store (index.ts)

```typescript
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
      {
        name: "auth-store",
        partialize: (state) => ({ user: state.user }), // Only persist user
      }
    ),
    { name: "AuthStore" }
  )
);

// Selective exports for external use
export { resetAuthState } from "./reset-auth";
```

## Helper Patterns

### Shared Store Helpers

Use helpers from `@/lib/stores/helpers` for common patterns:

```typescript
import { createLoadingState, createErrorState } from "@/lib/stores/helpers";

interface ApiState {
  loading: boolean;
  error: string | null;
  data: Data | null;
}

const createApiState = (): ApiState => ({
  loading: false,
  error: null,
  data: null,
});

const createApiActions = <T extends ApiState>(
  set: (fn: (state: T) => Partial<T>) => void
) => ({
  ...createLoadingState(set),
  ...createErrorState(set),
  setData: (data: Data) => set({ data, loading: false, error: null }),
});
```

### Selector Patterns

Create selectors for complex derived state:

```typescript
// store.ts
export const useTripStore = create<TripStore>()(/* ... */);

// selectors.ts
export const useTripSelectors = () => {
  const trips = useTripStore((state) => state.trips);
  const userId = useAuthStore((state) => state.user?.id);

  return {
    userTrips: trips.filter(trip => trip.userId === userId),
    upcomingTrips: trips.filter(trip => trip.startDate > new Date()),
    completedTrips: trips.filter(trip => trip.endDate < new Date()),
  };
};
```

## Testing Patterns

### Store Testing

```typescript
import { resetStore } from "@/test/store-helpers";
import { createMockUser } from "@/test/factories";

describe("AuthStore", () => {
  beforeEach(() => {
    resetStore(useAuthStore, { user: null, isLoading: false, error: null });
  });

  it("sets user on login", async () => {
    const mockUser = createMockUser();
    await useAuthStore
      .getState()
      .login({ email: "test@test.com", password: "pass" });

    expect(useAuthStore.getState().user).toEqual(mockUser);
  });
});
```

### Slice Testing

```typescript
import { createAuthCoreSlice } from "./auth-core";

describe("AuthCore Slice", () => {
  it("sets user", () => {
    const slice = createAuthCoreSlice(
      (fn) => fn({ user: null, isLoading: false, error: null })
    );

    slice.setUser({ id: "1", email: "test@test.com" });

    // Assert state changes
  });
});
```

## Middleware Usage

### DevTools (Required)

```typescript
create(
  devtools(store, { name: "StoreName" })
)
```

### Persistence

```typescript
create(
  persist(store, {
    name: "store-key",
    partialize: (state) => pick(state, ["persistentField"]),
  })
)
```

### Immer (Optional)

```typescript
create(
  immer(store) // For mutable updates
)
```

## Performance Considerations

### Selector Usage

```typescript
// ❌ Bad - causes re-render on any store change
const user = useStore((state) => state.user);

// ✅ Good - only re-renders when user changes
const user = useStore((state) => state.user);

// ✅ Better - use selectors for complex derived state
const userTrips = useStore((state) => state.trips.filter(/* ... */));
```

### State Updates

```typescript
// ❌ Bad - multiple updates
set({ loading: true });
set({ data: result });
set({ loading: false });

// ✅ Good - single update
set({ loading: false, data: result });
```

## Migration Guide

### From Single File to Slices

1. **Extract Core State**
   - Move base state and simple setters to core slice
   - Keep complex logic in feature slices

2. **Create Feature Slices**
   - Group related actions together
   - Use consistent naming: `createFeatureSlice`

3. **Add Composition**
   - Combine slices in main store
   - Preserve middleware and persistence

4. **Update Imports**
   - Change from single import to selective imports
   - Update tests to use new patterns

### Benefits

- Clear separation of concerns across slices
- Easier testing with isolated logic
- Tree-shakable slices for smaller bundles
