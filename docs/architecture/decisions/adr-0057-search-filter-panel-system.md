# ADR-0057: Search Filter Panel System with shadcn/ui Components

**Version**: 1.0.0
**Status**: Accepted
**Date**: 2025-12-03
**Category**: Frontend Architecture
**Domain**: Search & Filtering
**Related ADRs**: ADR-0035 (React Compiler), ADR-0045 (Flights DTO Frontend Zod)
**Related Specs**: None

## Context

The TripSage search experience currently has an incomplete filter system:

1. **FilterPresets component exists** - Users can save/load filter presets, but there's no UI to actually apply filters in the first place
2. **search-filters-store.ts is bloated** - Contains 1,237 lines with 13+ unused methods that were never wired to UI
3. **No visual filter controls** - The flights page has `FilterPresets` in the sidebar but no `FilterPanel` for users to set filters
4. **Store methods were removed as YAGNI** - Some removed methods (`clearFiltersByCategory`, `applyFiltersFromObject`) would actually improve UX; `getMostUsedFilters` is deferred pending a follow-up ADR and implementation.

### Current State Analysis

```text
search-filters-store.ts (974 lines after cleanup)
├── Available filters/sort options by search type ✓
├── Active filters and presets ✓
├── Filter validation ✓
├── Preset management (save/load/delete/duplicate) ✓
└── UI Controls to SET filters ✗ (MISSING)
```

The filter presets workflow is broken:

- Users cannot apply filters → cannot save meaningful presets → presets feature is unusable

## Decision

**Status note:** This ADR is *Accepted*. Sections 4–6 describe the planned FilterPanel component/store architecture that is not yet implemented; Section 7 reflects current integration points with the existing `useSearchFiltersStore`; Sections 8–9 outline deep-linking and page wiring that remain to be built. See **Deferred Work** below for tracked follow-ups.

We will implement a complete search filter system using shadcn/ui components with the following architecture:

### 1. Prerequisites

- `shadcn/ui` is already installed and configured (see `docs/development/ui.md`).
- Run all shadcn commands from the repository root so the generator picks up the Next.js workspace config.
- **Versioning strategy**: We intentionally use `@latest` for shadcn component additions to track upstream bug fixes and improvements. Versions are pinned in `pnpm-lock.yaml` for reproducibility across environments; CI/CD and local dev will have identical locked versions. If a breaking change occurs in a shadcn release, replace `@latest` with a specific vetted version in `package.json` (e.g., `shadcn-ui@0.8.1`) and document the constraint in this ADR with the breaking change details. Team members should review shadcn changelog entries during routine `pnpm update` cycles and flag any known issues (search `github.com/shadcn-ui/ui/releases` for accordion/toggle-group breaking changes before upgrade).

### 2. Restore Valuable Store Methods

Restore two methods that were incorrectly removed as YAGNI (the previously proposed `getMostUsedFilters` is deferred to a follow-up ADR because it is not implemented in the store yet):

| Method | User Value |
|--------|-----------|
| `clearFiltersByCategory(category)` | "Clear all pricing filters" - better UX than clearing one by one |
| `applyFiltersFromObject(filterObject)` | Enable URL deep-linking, shareable filter configurations |

### 3. Install Additional shadcn/ui Components

```bash
npx shadcn@latest add accordion toggle-group
```

### 4. Component Architecture

```text
FilterPanel (Card)
├── Header
│   ├── Title: "Filters"
│   ├── Active filter count (Badge)
│   └── "Clear All" button
├── QuickFilters (interim, see follow-ups below)
│   └── Badges from usage analytics (deferred: `getMostUsedFilters` implementation; renders disabled/hidden until implemented or analytics presets provided via props)
├── Accordion
│   ├── AccordionItem: Price Range
│   │   └── FilterRange (Slider dual-thumb)
│   ├── AccordionItem: Stops
│   │   └── FilterToggleOptions (ToggleGroup)
│   ├── AccordionItem: Airlines
│   │   └── FilterCheckboxGroup (Checkbox list + ScrollArea)
│   ├── AccordionItem: Departure Time
│   │   └── FilterToggleOptions (ToggleGroup)
│   └── AccordionItem: Duration
│       └── FilterRange (Slider)
└── ActiveFilters
    └── Badge chips with remove (×) buttons
```

### 5. File Structure

```text
src/components/features/search/
├── cards/                        # Card components
│   ├── accommodation-card.tsx
│   ├── activity-card.tsx
│   ├── destination-card.tsx
│   ├── flight-card.tsx
│   ├── hotel-card.tsx
│   ├── amenities.tsx
│   └── rating-stars.tsx
├── common/                       # Shared utilities
│   └── format.ts
├── filters/
│   ├── __tests__/
│   ├── api-payload.ts            # Build API payloads from filter state
│   ├── constants.ts              # FILTER_IDS and configuration
│   ├── filter-checkbox-group.tsx # Multi-select with select all/none
│   ├── filter-panel.tsx          # Main filter panel component
│   ├── filter-presets.tsx        # Save/load presets
│   ├── filter-range.tsx          # Reusable range slider (price, duration)
│   ├── filter-toggle-options.tsx # Single/multi toggle options
│   └── utils.ts                  # Type guards for filter values
├── forms/                        # Search form components
│   ├── __tests__/
│   ├── activity-search-form.tsx
│   ├── destination-search-form.tsx
│   ├── flight-search-form.tsx
│   └── hotel-search-form.tsx
├── modals/                       # Modal dialogs
│   ├── activity-comparison-modal.tsx
│   └── trip-selection-modal.tsx
├── results/                      # Results display components
│   ├── __tests__/
│   ├── shared/
│   │   ├── use-results-list.ts   # Shared results state hook
│   │   ├── results-controls-bar.tsx
│   │   ├── results-empty-state.tsx
│   │   └── results-loading-skeleton.tsx
│   ├── activity-results.tsx
│   ├── flight-results.tsx
│   └── hotel-results.tsx
├── search-analytics.tsx          # Cross-cutting analytics
└── search-collections.tsx        # Cross-cutting collections
```

### 5.1 Testing Strategy

- **Frameworks**: Vitest + React Testing Library for component behavior; MSW for network interactions in results lists; snapshot tests only for low-change presentational pieces (skeletons, badges).
- **Placement**: colocate tests under `filters/__tests__/`, `forms/__tests__/`, and `results/__tests__/` as shown in the structure; shared factories live in `src/test/factories`.
- **Coverage**: target ≥85% line/branch coverage for filter panel logic, store adapters, and URL serialization helpers; critical paths (apply/clear filters, deep-linking hydration, preset save/load) must be exercised.
- **Fixtures/mocks**: mock filter payloads and search params in `src/test/fixtures/search-filters.ts`; use MSW handlers for API payload builders in `filters/api-payload.ts`.

**Example test file structure:**

```typescript
// src/components/features/search/filters/__tests__/filter-panel.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FilterPanel } from '../filter-panel';
import { useSearchFiltersStore } from '@/stores/search-filters-store';

describe('FilterPanel', () => {
  beforeEach(() => {
    // Reset store before each test
    useSearchFiltersStore.getState().clearAllFilters();
  });

  it('applies price range filter', async () => {
    render(<FilterPanel />);
    const slider = screen.getByRole('slider', { name: /price/i });
    await userEvent.click(slider);
    expect(useSearchFiltersStore.getState().activeFilters).toContainEqual(
      expect.objectContaining({ id: 'price' })
    );
  });

  it('clears all filters on Clear All button click', async () => {
    // Setup: apply some filters
    useSearchFiltersStore.getState().setActiveFilter('price', { min: 0, max: 1000 });
    render(<FilterPanel />);

    const clearButton = screen.getByRole('button', { name: /clear all/i });
    await userEvent.click(clearButton);

    expect(useSearchFiltersStore.getState().hasActiveFilters()).toBe(false);
  });

  // ... more test cases ...
});
```

### 6. shadcn/ui Components Mapping

| Filter Type | shadcn/ui Component | Example Use |
|-------------|--------------------|--------------|
| Range (min/max) | `Slider` (dual-thumb) | Price: $0-$2000 |
| Single select | `ToggleGroup` (single) | Stops: Any/Nonstop/1/2+ |
| Multi select | `Checkbox` + `ScrollArea` | Airlines: AA, UA, DL |
| Toggle | `ToggleGroup` (multiple) | Time: Morning/Afternoon/Evening |
| Active filters | `Badge` | Removable filter chips |
| Sections | `Accordion` | Collapsible filter categories |

### 6.1 Hotel Search Sort Options

The `HotelResults` component supports four sort criteria:

| Sort | Description | Availability |
|------|-------------|--------------|
| AI Recommended | Sort by AI recommendation score (1-10) | Always |
| Price | Sort by total price | Always |
| Rating | Sort by star rating | Always |
| Distance | Sort by proximity to search center (Haversine) | When `searchCenter` prop provided |

Distance sorting uses the Haversine formula (`@/lib/geo`) to calculate great-circle distance from the search center to each hotel's coordinates. Hotels without coordinates are sorted to the end.

### 7. Store Integration

The FilterPanel will integrate with `useSearchFiltersStore`:

```typescript
const {
  // State
  currentFilters,
  activeFilters,
  hasActiveFilters,
  activeFilterCount,
  
  // Actions
  setActiveFilter,
  removeActiveFilter,
  clearAllFilters,
  clearFiltersByCategory,  // Restored

  // Validation
  validateFilter,
  getFilterValidationError,
} = useSearchFiltersStore();
```

**QuickFilters interim behavior (follow-up):** The QuickFilters component will be included in FilterPanel but initially render as disabled or hidden. Two paths to activation exist:
  1. **Store API** (deferred follow-up): Once `getMostUsedFilters` is implemented in the store, QuickFilters will call it to populate badge suggestions from usage analytics.
  2. **Props fallback** (interim): Parent component can pass `quickFilterPresets?: FilterPreset[]` prop as a temporary source until the store API is ready.

  Until one of these is implemented, the component gracefully hides itself (e.g., `if (!getMostUsedFilters && !presets) return null`). This defers the analytics integration work while keeping the UI architecture complete.

### 8. Deferred: Deep-linking Implementation

Deep-linking for filters is **not yet implemented**. To enable it, deliver all the following:

- Implement `queryToFilters` and `filtersToQueryParams` utilities (format TBD; include tests).
- Integrate URL read/write in the filter panel flow (e.g., hydrate via `applyFiltersFromObject` on load and update URL when filters change).
- Provide example integration points (e.g., where `applyFiltersFromObject` is invoked inside `filter-panel.tsx` or a page-level effect).
- Add documentation and tests that cover serialization, deserialization, and no-op behavior when deep-linking is disabled.

### 9. Page Integration

Update `flights/page.tsx` sidebar:

```tsx
<div className="space-y-6">
  <ErrorBoundary fallback={<FilterPanelSkeleton />}>
    <Suspense fallback={<FilterPanelSkeleton />}>
      <FilterPanel />      {/* NEW: Apply filters */}
    </Suspense>
  </ErrorBoundary>
  <FilterPresets />        {/* Existing: Save/load presets */}
</div>
```

`FilterPanelSkeleton` shows disabled controls while async hydration (URL → store) or analytics-powered quick filters are loading.

## Deferred Work

- QuickFilters analytics integration (`getMostUsedFilters` store API) and activation path — Tracking: [issue draft placeholder](https://github.com/tripsage-ai/tripsage/issues/new?title=ADR-0057%3A%20QuickFilters%20analytics%20integration&labels=adr,frontend,filters).
- Deep-linking and page wiring (Sections 8–9) for flights and other search pages — Tracking: [issue draft placeholder](https://github.com/tripsage-ai/tripsage/issues/new?title=ADR-0057%3A%20Search%20filter%20deep-linking%20and%20page%20wiring&labels=adr,frontend,filters).

## Consequences

### Positive

- **Complete filter workflow** - Users can apply filters → save presets → reload presets
- **Consistent UI** - All filter controls use shadcn/ui components matching design system
- **Reusable components** - FilterRange, FilterCheckboxGroup, FilterToggleOptions work across all search types
- **Better UX** - Accordion sections, clear by category, quick filters from usage stats
- **Type-safe** - All filter values validated through Zod schemas in store
- **Accessible** - shadcn/ui components have built-in ARIA support
- **Partial deep-linking readiness** - Plumbing identified; hydration via `applyFiltersFromObject` planned after `queryToFilters`/`filtersToQueryParams` and URL wiring land

### Negative

- **Additional bundle size** - Estimated +5KB for Accordion/Toggle Group (shadcn) — validate with `pnpm build:analyze` after implementation
- **Implementation effort** - Estimated ~590 LOC across six primary files (filter-panel.tsx, filter-presets.tsx, filter-range.tsx, filter-toggle-options.tsx, filter-checkbox-group.tsx, search-filters-store.ts); excludes existing shared components listed in File Structure (cards/forms/modals/results) which remain mostly untouched.
- **Store complexity** - ~50 new lines from restored methods

### Neutral

- **No breaking changes** - Existing FilterPresets component unchanged
- **Filter configs remain static** - No runtime filter configuration changes needed

## Alternatives Considered

### Alternative 1: Use Collapsible Instead of Accordion

**Description**: Use existing `Collapsible` component for filter sections.

**Why not chosen**: Accordion provides better UX with automatic collapse of other sections, reducing cognitive load. Accordion is the standard pattern for filter panels in e-commerce and travel sites.

### Alternative 2: Build Custom Filter Components

**Description**: Build filter controls from scratch without shadcn/ui.

**Why not chosen**: Violates library-first principle. shadcn/ui components are accessible, tested, and consistent with our design system. Custom components would duplicate effort and risk accessibility issues.

### Alternative 3: Keep Store Minimal (No Method Restoration)

**Description**: Don't restore the removed store methods.

**Why not chosen**: The two restored methods provide genuine UX value:

- `clearFiltersByCategory` - Essential for filter-heavy interfaces
- `applyFiltersFromObject` - Required for URL deep-linking feature

`getMostUsedFilters` remains deferred to a follow-up ADR once the store API is implemented.

### Alternative 4: Use React Query for Filter State

**Description**: Move filter state to React Query instead of Zustand.

**Why not chosen**: Filters are UI state, not server state. Zustand is appropriate for client-side form/filter state. React Query is for server cache synchronization.

## References

- [shadcn/ui Accordion](https://ui.shadcn.com/docs/components/accordion)
- [shadcn/ui Toggle Group](https://ui.shadcn.com/docs/components/toggle-group)
- [shadcn/ui Slider](https://ui.shadcn.com/docs/components/slider)
- [Zustand Slices Pattern](https://docs.pmnd.rs/zustand/guides/slices-pattern)
- [Radix UI Primitives](https://www.radix-ui.com/primitives)
- Existing: `src/stores/search-filters-store.ts`
- Existing: `src/components/features/search/filters/filter-presets.tsx`
- Existing: `src/components/features/search/filters/filter-panel.tsx`
