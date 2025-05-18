# Frontend Migration Guide: v1 to v2

This guide provides a comprehensive walkthrough for migrating the TripSage frontend from v1 to v2 architecture.

## Overview

The v2 architecture introduces significant updates to leverage the latest web technologies and improve performance, developer experience, and user experience.

## Major Changes

### 1. Core Framework Updates

| Component | v1 | v2 | Breaking Changes |
|-----------|----|----|------------------|
| Next.js | 14+ | 15.3.1 | New App Router, caching behavior |
| React | 18+ | 19.1.0 | Server Components by default |
| TypeScript | 5+ | 5.5+ | Stricter type checking |
| Node.js | 18+ | 20+ | New runtime features |

### 2. Styling System

#### Tailwind CSS v3 → v4

```css
/* v1: RGB colors */
.text-primary {
  color: rgb(59, 130, 246);
}

/* v2: OKLCH colors */
.text-primary {
  color: oklch(0.75 0.18 240);
}
```

- **Action Required**: Update color definitions to OKLCH
- **New Features**: Container queries, P3 color support
- **Config Changes**: CSS-based configuration instead of JS

### 3. State Management

#### Zustand v4 → v5

```typescript
// v1: With custom equality
const useStore = create((set) => ({...}), shallow);

// v2: Use useShallow hook
import { useShallow } from 'zustand/shallow';
const state = useStore(useShallow((state) => ({...})));
```

- **Breaking**: Removed custom equality function parameter
- **New**: Native `useSyncExternalStore` usage
- **Requirements**: React 18+ required

### 4. Data Fetching

#### TanStack Query v4 → v5

```typescript
// v1: Experimental suspense
const { data } = useQuery({
  queryKey: ['trips'],
  queryFn: fetchTrips,
  suspense: true, // experimental
});

// v2: First-class suspense support
const { data } = useSuspenseQuery({
  queryKey: ['trips'],
  queryFn: fetchTrips,
});
```

- **New Hooks**: `useSuspenseQuery`, `useSuspenseInfiniteQuery`
- **Breaking**: Renamed `cacheTime` to `gcTime`
- **Breaking**: Merged `keepPreviousData` with `placeholderData`

### 5. UI Components

#### shadcn/ui v2 → v3

- **Update**: New component APIs
- **Breaking**: Some prop changes
- **New**: Tailwind CSS v4 compatibility

## Migration Steps

### Step 1: Update Dependencies

```bash
# Update package.json
npm update next@15.3.1 react@19.1.0 react-dom@19.1.0
npm update typescript@5.5
npm update tailwindcss@4.0
npm update zustand@5.0.4
npm update @tanstack/react-query@5.x
```

### Step 2: Update Next.js Configuration

```typescript
// next.config.js → next.config.ts
export default {
  reactStrictMode: true,
  experimental: {
    serverActions: true,
    ppr: true, // Partial Prerendering
  },
  // Remove deprecated options
};
```

### Step 3: Migrate to App Router

1. Move pages from `pages/` to `app/`
2. Convert to new file conventions:
   - `_app.tsx` → `app/layout.tsx`
   - `index.tsx` → `app/page.tsx`
   - API routes → `app/api/route.ts`

### Step 4: Update State Management

```typescript
// Before (v1)
import create from 'zustand';

const useStore = create((set) => ({
  trips: [],
  addTrip: (trip) => set((state) => ({ 
    trips: [...state.trips, trip] 
  })),
}), shallow);

// After (v2)
import { create } from 'zustand';
import { useShallow } from 'zustand/shallow';

const useStore = create((set) => ({
  trips: [],
  addTrip: (trip) => set((state) => ({ 
    trips: [...state.trips, trip] 
  })),
}));

// In component
const { trips, addTrip } = useStore(
  useShallow((state) => ({ 
    trips: state.trips, 
    addTrip: state.addTrip 
  }))
);
```

### Step 5: Update Data Fetching

```typescript
// Before (v1)
const { data, isLoading } = useQuery({
  queryKey: ['trips'],
  queryFn: fetchTrips,
  suspense: true,
});

// After (v2)
const { data } = useSuspenseQuery({
  queryKey: ['trips'],
  queryFn: fetchTrips,
});
```

### Step 6: Update Tailwind Configuration

```typescript
// tailwind.config.js → tailwind.config.ts
export default {
  content: ['./app/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Convert RGB to OKLCH
        primary: 'oklch(0.75 0.18 240)',
        secondary: 'oklch(0.65 0.15 120)',
      },
    },
  },
};
```

### Step 7: Update Component Patterns

```typescript
// Before (v1) - Client Component by default
export default function TripCard({ trip }) {
  return <div>{trip.name}</div>;
}

// After (v2) - Server Component by default
export default function TripCard({ trip }: { trip: Trip }) {
  return <div>{trip.name}</div>;
}

// Client Component when needed
'use client';

export default function InteractiveTripCard({ trip }: { trip: Trip }) {
  const [expanded, setExpanded] = useState(false);
  return <div onClick={() => setExpanded(!expanded)}>{trip.name}</div>;
}
```

### Step 8: Update API Routes

```typescript
// Before (v1) - pages/api/trips.ts
export default function handler(req, res) {
  if (req.method === 'GET') {
    res.json({ trips: [] });
  }
}

// After (v2) - app/api/trips/route.ts
export async function GET() {
  return Response.json({ trips: [] });
}

export async function POST(request: Request) {
  const data = await request.json();
  return Response.json({ success: true });
}
```

### Step 9: Update Testing

```typescript
// Update test configuration for v2
// vitest.config.ts
export default {
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: './tests/setup.ts',
  },
};
```

## Common Issues & Solutions

### Issue 1: Hydration Mismatches

- **Cause**: Server/Client rendering differences
- **Solution**: Use `useEffect` for client-only logic

### Issue 2: TypeScript Errors

- **Cause**: Stricter typing in v2
- **Solution**: Update type definitions, use strict mode

### Issue 3: State Management Errors

- **Cause**: Zustand v5 breaking changes
- **Solution**: Use `useShallow` hook for object selections

### Issue 4: Build Errors

- **Cause**: Deprecated Next.js features
- **Solution**: Update to new APIs and patterns

## Performance Improvements

### Before & After Metrics

- **First Contentful Paint**: 2.5s → 1.5s
- **Time to Interactive**: 5s → 3s
- **Bundle Size**: 350KB → 200KB
- **Lighthouse Score**: 85 → 95+

## Resources

- [Next.js 15 Migration Guide](https://nextjs.org/docs/upgrading)
- [React 19 Upgrade Guide](https://react.dev/blog/2024/04/25/react-19-upgrade-guide)
- [Tailwind CSS v4 Migration](https://tailwindcss.com/docs/upgrade-guide)
- [Zustand v5 Migration](https://github.com/pmndrs/zustand/blob/main/docs/migrations/migrating-to-v5.md)
- [TanStack Query v5 Migration](https://tanstack.com/query/latest/docs/framework/react/guides/migrating-to-v5)

## Checklist

- [ ] Update all dependencies to v2 versions
- [ ] Migrate from Pages Router to App Router
- [ ] Update state management to Zustand v5
- [ ] Convert to React Server Components
- [ ] Update data fetching to TanStack Query v5
- [ ] Migrate Tailwind CSS to v4
- [ ] Update all TypeScript types
- [ ] Run comprehensive test suite
- [ ] Performance testing
- [ ] Deploy to staging environment
- [ ] Monitor for errors
- [ ] Deploy to production

## Support

For migration support:

1. Check the official migration guides
2. Review the example code in `/examples`
3. Consult the TripSage development team
4. Open an issue in the repository
