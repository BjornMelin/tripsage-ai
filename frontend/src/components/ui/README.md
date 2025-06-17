# UI Components Library

This directory contains reusable UI components for the TripSage frontend application.

## Loading Components

Comprehensive loading state management with accessibility support and TypeScript validation.

### Components Included

#### Base Components

- **Skeleton** - Configurable skeleton placeholders with animation support
- **LoadingSpinner** - Various spinner animations (default, dots, bars, pulse)

#### Loading States

- **LoadingOverlay** - Full-screen or container overlay with progress support
- **LoadingState** - Wrapper component for conditional loading/content display
- **LoadingButton** - Button with integrated loading state
- **LoadingContainer** - Container with loading state management
- **PageLoading** - Full-page loading component for app router

#### Generic Skeletons

- **AvatarSkeleton** - Circular avatar placeholders
- **CardSkeleton** - Card layout with optional image/avatar
- **ListItemSkeleton** - List item with avatar and action support
- **TableSkeleton** - Table structure with configurable rows/columns
- **FormSkeleton** - Form fields with submit button
- **ChartSkeleton** - Different chart types (bar, line, pie, area)

#### Travel-Specific Skeletons

- **FlightSkeleton** - Flight search result layout
- **HotelSkeleton** - Hotel/accommodation result layout
- **TripSkeleton** - Trip card with image and details
- **DestinationSkeleton** - Destination card with tags
- **ItineraryItemSkeleton** - Timeline-based itinerary item
- **ChatMessageSkeleton** - Chat message with user/assistant variants
- **SearchFilterSkeleton** - Search filter sections

### Hooks

#### useLoading

```typescript
const { isLoading, startLoading, stopLoading, setProgress } = useLoading({
  timeout: 5000,
  onTimeout: () => console.log('Loading timed out')
});
```

#### useAsyncLoading

```typescript
const { data, isLoading, error, execute } = useAsyncLoading(asyncFunction);
```

#### useDebouncedLoading

```typescript
const loading = useDebouncedLoading(300); // 300ms debounce
```

### Types and Validation

All components use Zod schemas for prop validation and TypeScript for type safety:

- `LoadingState` - Loading state interface
- `SkeletonConfig` - Skeleton configuration options  
- `LoadingSpinnerConfig` - Spinner configuration
- `SkeletonType` - Enum for skeleton variants

### Accessibility Features

- Proper ARIA attributes (`role="status"`, `aria-label`, `aria-live`)
- Screen reader friendly loading messages
- Reduced motion support via CSS media queries
- Focus management during loading states

### Usage Example

```tsx
import { LoadingState, FlightSkeleton, useLoading } from '@/components/ui/loading';

function FlightResults() {
  const { isLoading } = useLoading();
  
  return (
    <LoadingState
      isLoading={isLoading}
      skeleton={<FlightSkeleton />}
    >
      <FlightResultsList />
    </LoadingState>
  );
}
```

### Next.js Integration

Loading components are integrated with Next.js App Router:

- `/app/loading.tsx` - Root level loading
- `/app/(dashboard)/loading.tsx` - Dashboard loading with skeleton grid

### Testing

Comprehensive test coverage (>90%) includes:

- Component rendering and props
- Accessibility attributes
- Animation states
- Hook functionality
- Error handling
- Edge cases

Run tests with:

```bash
pnpm test src/components/ui/__tests__/
```

### Performance

- CSS-based animations for optimal performance
- Debounced loading states to prevent flashing
- Minimal bundle size with tree-shaking support
- Proper cleanup of timers and effects
