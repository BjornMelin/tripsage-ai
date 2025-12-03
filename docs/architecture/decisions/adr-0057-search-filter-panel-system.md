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
4. **Store methods were removed as YAGNI** - Some removed methods (`clearFiltersByCategory`, `getMostUsedFilters`, `applyFiltersFromObject`) would actually improve UX

### Current State Analysis

```
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

We will implement a complete search filter system using shadcn/ui components with the following architecture:

### 1. Restore Valuable Store Methods

Restore three methods that were incorrectly removed as YAGNI:

| Method | User Value |
|--------|-----------|
| `clearFiltersByCategory(category)` | "Clear all pricing filters" - better UX than clearing one by one |
| `getMostUsedFilters(searchType, limit)` | Power "Quick Filters" section showing frequently used filters |
| `applyFiltersFromObject(filterObject)` | Enable URL deep-linking, shareable filter configurations |

### 2. Install Additional shadcn/ui Components

```bash
npx shadcn@latest add accordion toggle-group
```

### 3. Component Architecture

```
FilterPanel (Card)
├── Header
│   ├── Title: "Filters"
│   ├── Active filter count (Badge)
│   └── "Clear All" button
├── QuickFilters (optional)
│   └── Badges from getMostUsedFilters()
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

### 4. File Structure

```
frontend/src/components/features/search/
├── filter-panel.tsx              # Main filter panel component
├── filter-presets.tsx            # Existing - save/load presets
├── filters/
│   ├── filter-range.tsx          # Reusable range slider (price, duration)
│   ├── filter-checkbox-group.tsx # Multi-select with select all/none
│   ├── filter-toggle-options.tsx # Single/multi toggle options
│   └── index.ts                  # Barrel exports
└── index.ts                      # Updated exports
```

### 5. shadcn/ui Components Mapping

| Filter Type | shadcn/ui Component | Example Use |
|-------------|--------------------|--------------| 
| Range (min/max) | `Slider` (dual-thumb) | Price: $0-$2000 |
| Single select | `ToggleGroup` (single) | Stops: Any/Nonstop/1/2+ |
| Multi select | `Checkbox` + `ScrollArea` | Airlines: AA, UA, DL |
| Toggle | `ToggleGroup` (multiple) | Time: Morning/Afternoon/Evening |
| Active filters | `Badge` | Removable filter chips |
| Sections | `Accordion` | Collapsible filter categories |

### 6. Store Integration

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
  getMostUsedFilters,      // Restored
  
  // Validation
  validateFilter,
  getFilterValidationError,
} = useSearchFiltersStore();
```

### 7. Page Integration

Update `flights/page.tsx` sidebar:

```tsx
<div className="space-y-6">
  <FilterPanel />      {/* NEW: Apply filters */}
  <FilterPresets />    {/* Existing: Save/load presets */}
</div>
```

## Consequences

### Positive

- **Complete filter workflow** - Users can apply filters → save presets → reload presets
- **Consistent UI** - All filter controls use shadcn/ui components matching design system
- **Reusable components** - FilterRange, FilterCheckboxGroup, FilterToggleOptions work across all search types
- **Better UX** - Accordion sections, clear by category, quick filters from usage stats
- **Type-safe** - All filter values validated through Zod schemas in store
- **Accessible** - shadcn/ui components have built-in ARIA support
- **Deep-linking ready** - `applyFiltersFromObject` enables shareable URLs

### Negative

- **Additional bundle size** - ~5KB for accordion + toggle-group components
- **Implementation effort** - ~590 new lines of code across 6 files
- **Store complexity** - 3 methods restored (~50 lines)

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

**Why not chosen**: The three methods provide genuine UX value:
- `clearFiltersByCategory` - Essential for filter-heavy interfaces
- `getMostUsedFilters` - Enables personalized quick filters
- `applyFiltersFromObject` - Required for URL deep-linking feature

### Alternative 4: Use React Query for Filter State

**Description**: Move filter state to React Query instead of Zustand.

**Why not chosen**: Filters are UI state, not server state. Zustand is appropriate for client-side form/filter state. React Query is for server cache synchronization.

## References

- [shadcn/ui Accordion](https://ui.shadcn.com/docs/components/accordion)
- [shadcn/ui Toggle Group](https://ui.shadcn.com/docs/components/toggle-group)
- [shadcn/ui Slider](https://ui.shadcn.com/docs/components/slider)
- [Zustand Slices Pattern](https://docs.pmnd.rs/zustand/guides/slices-pattern)
- [Radix UI Primitives](https://www.radix-ui.com/primitives)
- Existing: `frontend/src/stores/search-filters-store.ts`
- Existing: `frontend/src/components/features/search/filter-presets.tsx`
