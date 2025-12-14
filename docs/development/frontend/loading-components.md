# Loading Components

Reusable loading primitives for TripSage UI, including spinners, skeletons, and
common loading state wrappers. These are primarily exported via
`src/components/ui/loading.tsx`.

## What to use

- **Inline async state**: `LoadingSpinner`
- **Replace content while loading**: `LoadingState` (optionally with a skeleton)
- **Disable buttons while submitting**: `LoadingButton`
- **Block an area while loading**: `LoadingOverlay` / `LoadingContainer`
- **App Router route-level loading**: `PageLoading` (see `src/app/loading.tsx`)
- **Placeholders**: `Skeleton` / `*Skeleton` components

## Imports

Prefer importing from the index module for loading-related UI:

```tsx
import {
  FlightSkeleton,
  LoadingButton,
  LoadingOverlay,
  LoadingSpinner,
  LoadingState,
  PageLoading,
  useAsyncLoading,
  useDebouncedLoading,
  useLoading,
} from "@/components/ui/loading";
```

## Component inventory

### Base primitives

- `Skeleton` (`src/components/ui/skeleton.tsx`)
- `LoadingSpinner` (`src/components/ui/loading-spinner.tsx`)

### Loading wrappers

- `LoadingState`, `LoadingOverlay`, `LoadingContainer`, `LoadingButton`, `PageLoading`
  (`src/components/ui/loading-states.tsx`)

### Generic skeletons

- `AvatarSkeleton`, `CardSkeleton`, `ListItemSkeleton`, `TableSkeleton`, `FormSkeleton`, `ChartSkeleton`
  (`src/components/ui/loading-skeletons.tsx`)

### Travel skeletons

- `FlightSkeleton`, `HotelSkeleton`, `TripSkeleton`, `DestinationSkeleton`, `ItineraryItemSkeleton`,
  `ChatMessageSkeleton`, `SearchFilterSkeleton`
  (`src/components/ui/travel-skeletons.tsx`)

## Hooks

The loading hooks live in `src/hooks/use-loading.ts` and are re-exported from
`@/components/ui/loading` for convenience.

### `useLoading`

Use when you want a simple imperative loading state (optionally with progress):

```tsx
const { isLoading, startLoading, stopLoading, setProgress } = useLoading();
```

### `useAsyncLoading`

Use when you want to wrap an async function and capture `data` + `error`:

```tsx
const { data, isLoading, error, execute } = useAsyncLoading(fetchSomething);
```

### `useDebouncedLoading`

Use to avoid “flash” states for very fast requests:

```tsx
const isLoading = useDebouncedLoading(300);
```

## Accessibility expectations

Loading UI should remain screen-reader friendly:

- Spinners and skeletons include ARIA labels (override when needed).
- Respect reduced motion (`prefers-reduced-motion`) via CSS when possible.
- Prefer skeletons for large content regions to reduce layout shift.

## Next.js App Router integration

- Global route loading: `src/app/loading.tsx`
- Dashboard route loading: `src/app/dashboard/loading.tsx`

## Testing

Component tests live in `src/components/ui/__tests__/` (Vitest + jsdom).
