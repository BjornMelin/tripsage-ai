/**
 * @fileoverview Main filter panel component for search pages.
 *
 * Integrates with Zustand search-filters-store and uses shadcn/ui
 * Accordion for collapsible filter sections.
 *
 * @see ADR-0057 for architecture decisions
 */

"use client";

import type { FilterValue, ValidatedFilterOption } from "@schemas/stores";
import { SlidersHorizontalIcon, XIcon } from "lucide-react";
import { useCallback, useMemo } from "react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useSearchFiltersStore } from "@/stores/search-filters-store";
import { formatCurrency, formatDurationMinutes } from "../common/format";
import { AIRLINES_OPTIONS, FILTER_IDS, STOPS_OPTIONS, TIME_OPTIONS } from "./constants";
import { FilterCheckboxGroup } from "./filter-checkbox-group";
import { FilterRange } from "./filter-range";
import { FilterToggleOptions } from "./filter-toggle-options";
import { isRangeObject, isStringArray, isStringValue } from "./utils";

/** Props for the FilterPanel component */
interface FilterPanelProps {
  /** Optional CSS class name */
  className?: string;
  /** Default open accordion sections */
  defaultOpenSections?: string[];
}

/** Get typed filter value from active filters map. */
export function GetFilterValue<T extends FilterValue>(
  activeFilters: Record<string, { value: FilterValue }>,
  filterId: string,
  guard: (value: FilterValue) => value is T
): T | undefined {
  const entry = activeFilters[filterId];
  if (!entry) {
    return undefined;
  }
  return guard(entry.value) ? entry.value : undefined;
}

/** Get display label for an active filter. */
export function GetFilterLabel(
  filterId: string,
  value: FilterValue,
  currentFilters: ValidatedFilterOption[]
): string {
  const filterConfig = currentFilters.find((f) => f.id === filterId);
  const label = filterConfig?.label || filterId;

  if (typeof value === "object" && value !== null && "min" in value && "max" in value) {
    const rangeValue = value as { min: number; max: number };
    if (filterId.includes("price")) {
      return `${label}: ${formatCurrency(rangeValue.min)}-${formatCurrency(rangeValue.max)}`;
    }
    if (filterId.includes("duration")) {
      return `${label}: ${formatDurationMinutes(rangeValue.min)}-${formatDurationMinutes(rangeValue.max)}`;
    }
    return `${label}: ${rangeValue.min}-${rangeValue.max}`;
  }

  if (Array.isArray(value)) {
    return `${label}: ${value.length} selected`;
  }

  if (typeof value === "string") {
    // Try to find option label
    if (filterId === FILTER_IDS.stops) {
      const option = STOPS_OPTIONS.find((o) => o.value === value);
      return option ? `${label}: ${option.label}` : `${label}: ${value}`;
    }
    if (filterId === FILTER_IDS.departureTime) {
      const option = TIME_OPTIONS.find((o) => o.value === value);
      return option ? `${label}: ${option.label}` : `${label}: ${value}`;
    }
    return `${label}: ${value}`;
  }

  return label;
}

/**
 * Main filter panel component.
 *
 * Displays filter controls organized in collapsible accordion sections.
 * Integrates with Zustand store for state management.
 */
export function FilterPanel({
  className,
  defaultOpenSections = [FILTER_IDS.priceRange, FILTER_IDS.stops],
}: FilterPanelProps) {
  const {
    currentFilters,
    activeFilters,
    hasActiveFilters,
    activeFilterCount,
    currentSearchType,
    setActiveFilter,
    removeActiveFilter,
    clearAllFilters,
    clearFiltersByCategory,
  } = useSearchFiltersStore();

  // Group filters by category
  const filtersByCategory = useMemo(() => {
    const grouped: Record<string, ValidatedFilterOption[]> = {};
    currentFilters.forEach((filter) => {
      const category = filter.category || "other";
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(filter);
    });
    return grouped;
  }, [currentFilters]);

  // Get active filter entries for display
  const activeFilterEntries = useMemo(() => {
    return Object.entries(activeFilters).map(([filterId, filter]) => ({
      filterId,
      label: GetFilterLabel(filterId, filter.value, currentFilters),
      value: filter.value,
    }));
  }, [activeFilters, currentFilters]);

  // Handle filter value change
  const handleFilterChange = useCallback(
    (filterId: string, value: FilterValue) => {
      setActiveFilter(filterId, value);
    },
    [setActiveFilter]
  );

  // Handle range filter change (converts to FilterValue format)
  const handleRangeChange = useCallback(
    (filterId: string, value: { min: number; max: number }) => {
      setActiveFilter(filterId, value);
    },
    [setActiveFilter]
  );

  // Handle remove filter badge
  const handleRemoveFilter = useCallback(
    (filterId: string) => {
      removeActiveFilter(filterId);
    },
    [removeActiveFilter]
  );

  // Handle clear category
  const handleClearCategory = useCallback(
    (category: string) => {
      clearFiltersByCategory(category);
    },
    [clearFiltersByCategory]
  );

  // Don't render if no search type is selected
  if (!currentSearchType) {
    return null;
  }

  return (
    <Card className={className} data-testid="filter-panel">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SlidersHorizontalIcon className="h-4 w-4" />
            <CardTitle className="text-base">Filters</CardTitle>
            {hasActiveFilters && (
              <Badge variant="secondary" className="ml-1">
                {activeFilterCount}
              </Badge>
            )}
          </div>
          {hasActiveFilters && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={clearAllFilters}
              className="h-7 px-2 text-xs focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
              aria-label="Clear all filters"
            >
              Clear All
            </Button>
          )}
        </div>
        <CardDescription className="text-xs">
          Refine your search results
        </CardDescription>
      </CardHeader>

      <CardContent className="pt-0">
        {/* Active filter badges */}
        {activeFilterEntries.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-4 pb-3 border-b">
            {activeFilterEntries.map(({ filterId, label }) => (
              <Badge
                key={filterId}
                variant="outline"
                className="pl-2 pr-1 py-0.5 text-xs gap-1"
                data-testid={`active-filter-badge-${filterId}`}
              >
                {label}
                <button
                  type="button"
                  onClick={() => handleRemoveFilter(filterId)}
                  className="ml-1 hover:bg-muted rounded-full p-0.5 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                  aria-label={`Remove ${label} filter`}
                >
                  <XIcon className="h-3 w-3" />
                </button>
              </Badge>
            ))}
          </div>
        )}

        {/* Filter sections */}
        <Accordion
          type="multiple"
          defaultValue={defaultOpenSections}
          className="w-full"
        >
          {/* Price Range */}
          {filtersByCategory.pricing?.some((f) => f.id === FILTER_IDS.priceRange) && (
            <AccordionItem value={FILTER_IDS.priceRange}>
              <AccordionTrigger className="py-3 text-sm">
                <div className="flex items-center justify-between w-full pr-2">
                  <span>Price Range</span>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                {filtersByCategory.pricing.some((f) => activeFilters[f.id]) && (
                  <div className="flex justify-end mb-2">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-6 px-2 text-xs focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleClearCategory("pricing");
                      }}
                      aria-label="Clear price range filter"
                    >
                      Clear
                    </Button>
                  </div>
                )}
                <FilterRange
                  filterId={FILTER_IDS.priceRange}
                  label="Price"
                  min={0}
                  max={2000}
                  step={10}
                  value={GetFilterValue(
                    activeFilters,
                    FILTER_IDS.priceRange,
                    isRangeObject
                  )}
                  onChange={handleRangeChange}
                  formatValue={formatCurrency}
                />
              </AccordionContent>
            </AccordionItem>
          )}

          {/* Stops */}
          {filtersByCategory.routing?.some((f) => f.id === FILTER_IDS.stops) && (
            <AccordionItem value={FILTER_IDS.stops}>
              <AccordionTrigger className="py-3 text-sm">Stops</AccordionTrigger>
              <AccordionContent>
                <FilterToggleOptions
                  filterId={FILTER_IDS.stops}
                  label=""
                  options={STOPS_OPTIONS}
                  value={GetFilterValue(activeFilters, FILTER_IDS.stops, isStringValue)}
                  onChange={handleFilterChange}
                />
              </AccordionContent>
            </AccordionItem>
          )}

          {/* Airlines */}
          {filtersByCategory.airline?.some((f) => f.id === FILTER_IDS.airlines) && (
            <AccordionItem value={FILTER_IDS.airlines}>
              <AccordionTrigger className="py-3 text-sm">
                <div className="flex items-center justify-between w-full pr-2">
                  <span>Airlines</span>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                {activeFilters[FILTER_IDS.airlines] && (
                  <div className="flex justify-end mb-2">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-6 px-2 text-xs focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleClearCategory("airline");
                      }}
                      aria-label="Clear airlines filter"
                    >
                      Clear
                    </Button>
                  </div>
                )}
                <FilterCheckboxGroup
                  filterId={FILTER_IDS.airlines}
                  label=""
                  options={AIRLINES_OPTIONS}
                  value={GetFilterValue(
                    activeFilters,
                    FILTER_IDS.airlines,
                    isStringArray
                  )}
                  onChange={handleFilterChange}
                  maxHeight={180}
                />
              </AccordionContent>
            </AccordionItem>
          )}

          {/* Departure Time */}
          {filtersByCategory.timing?.some((f) => f.id === FILTER_IDS.departureTime) && (
            <AccordionItem value={FILTER_IDS.departureTime}>
              <AccordionTrigger className="py-3 text-sm">
                Departure Time
              </AccordionTrigger>
              <AccordionContent>
                <FilterToggleOptions
                  filterId={FILTER_IDS.departureTime}
                  label=""
                  options={TIME_OPTIONS}
                  value={GetFilterValue(
                    activeFilters,
                    FILTER_IDS.departureTime,
                    isStringArray
                  )}
                  onChange={handleFilterChange}
                  multiple
                />
              </AccordionContent>
            </AccordionItem>
          )}

          {/* Duration */}
          {filtersByCategory.timing?.some((f) => f.id === FILTER_IDS.duration) && (
            <AccordionItem value={FILTER_IDS.duration}>
              <AccordionTrigger className="py-3 text-sm">
                Flight Duration
              </AccordionTrigger>
              <AccordionContent>
                <FilterRange
                  filterId={FILTER_IDS.duration}
                  label="Max Duration"
                  min={0}
                  max={1440}
                  step={30}
                  value={GetFilterValue(
                    activeFilters,
                    FILTER_IDS.duration,
                    isRangeObject
                  )}
                  onChange={handleRangeChange}
                  formatValue={formatDurationMinutes}
                />
              </AccordionContent>
            </AccordionItem>
          )}
        </Accordion>

        {/* Empty state */}
        {currentFilters.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-4">
            No filters available for this search type.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
