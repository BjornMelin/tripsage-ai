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
import { formatCurrency, formatDurationMinutes } from "./common/format";
import { FilterCheckboxGroup } from "./filters/filter-checkbox-group";
import { FilterRange } from "./filters/filter-range";
import { FilterToggleOptions } from "./filters/filter-toggle-options";

/** Props for the FilterPanel component */
interface FilterPanelProps {
  /** Optional CSS class name */
  className?: string;
  /** Default open accordion sections */
  defaultOpenSections?: string[];
}

/** Flight stops options */
const STOPS_OPTIONS = [
  { label: "Any", value: "any" },
  { label: "Nonstop", value: "0" },
  { label: "1 Stop", value: "1" },
  { label: "2+", value: "2+" },
];

/** Departure time options */
const TIME_OPTIONS = [
  { label: "Early (12a-6a)", value: "early_morning" },
  { label: "Morning (6a-12p)", value: "morning" },
  { label: "Afternoon (12p-6p)", value: "afternoon" },
  { label: "Evening (6p-12a)", value: "evening" },
];

/** Airlines options (would typically come from API/store) */
const AIRLINES_OPTIONS = [
  { label: "American Airlines", value: "AA" },
  { label: "United Airlines", value: "UA" },
  { label: "Delta Air Lines", value: "DL" },
  { label: "Southwest Airlines", value: "WN" },
  { label: "Alaska Airlines", value: "AS" },
  { label: "JetBlue Airways", value: "B6" },
];

function GetFilterValue<T extends FilterValue>(
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
function GetFilterLabel(
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
    if (filterId === "stops") {
      const option = STOPS_OPTIONS.find((o) => o.value === value);
      return option ? `${label}: ${option.label}` : `${label}: ${value}`;
    }
    if (filterId.includes("time")) {
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
  defaultOpenSections = ["price_range", "stops"],
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

  const isRangeObject = (value: FilterValue): value is { max: number; min: number } =>
    typeof value === "object" &&
    value !== null &&
    "min" in value &&
    "max" in value &&
    typeof (value as { min: unknown }).min === "number" &&
    typeof (value as { max: unknown }).max === "number";

  const isStringValue = (value: FilterValue): value is string =>
    typeof value === "string";

  const isStringArray = (value: FilterValue): value is string[] =>
    Array.isArray(value) && value.every((entry) => typeof entry === "string");

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
    <Card className={className}>
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
          {filtersByCategory.pricing?.some((f) => f.id === "price_range") && (
            <AccordionItem value="price_range">
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
                  filterId="price_range"
                  label="Price"
                  min={0}
                  max={2000}
                  step={10}
                  value={GetFilterValue(activeFilters, "price_range", isRangeObject)}
                  onChange={handleRangeChange}
                  formatValue={formatCurrency}
                />
              </AccordionContent>
            </AccordionItem>
          )}

          {/* Stops */}
          {filtersByCategory.routing?.some((f) => f.id === "stops") && (
            <AccordionItem value="stops">
              <AccordionTrigger className="py-3 text-sm">Stops</AccordionTrigger>
              <AccordionContent>
                <FilterToggleOptions
                  filterId="stops"
                  label=""
                  options={STOPS_OPTIONS}
                  value={GetFilterValue(activeFilters, "stops", isStringValue)}
                  onChange={handleFilterChange}
                />
              </AccordionContent>
            </AccordionItem>
          )}

          {/* Airlines */}
          {filtersByCategory.airline?.some((f) => f.id === "airlines") && (
            <AccordionItem value="airlines">
              <AccordionTrigger className="py-3 text-sm">
                <div className="flex items-center justify-between w-full pr-2">
                  <span>Airlines</span>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                {activeFilters.airlines && (
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
                  filterId="airlines"
                  label=""
                  options={AIRLINES_OPTIONS}
                  value={GetFilterValue(activeFilters, "airlines", isStringArray)}
                  onChange={handleFilterChange}
                  maxHeight={180}
                />
              </AccordionContent>
            </AccordionItem>
          )}

          {/* Departure Time */}
          {filtersByCategory.timing?.some((f) => f.id === "departure_time") && (
            <AccordionItem value="departure_time">
              <AccordionTrigger className="py-3 text-sm">
                Departure Time
              </AccordionTrigger>
              <AccordionContent>
                <FilterToggleOptions
                  filterId="departure_time"
                  label=""
                  options={TIME_OPTIONS}
                  value={GetFilterValue(activeFilters, "departure_time", isStringArray)}
                  onChange={handleFilterChange}
                  multiple
                />
              </AccordionContent>
            </AccordionItem>
          )}

          {/* Duration */}
          {filtersByCategory.timing?.some((f) => f.id === "duration") && (
            <AccordionItem value="duration">
              <AccordionTrigger className="py-3 text-sm">
                Flight Duration
              </AccordionTrigger>
              <AccordionContent>
                <FilterRange
                  filterId="duration"
                  label="Max Duration"
                  min={0}
                  max={1440}
                  step={30}
                  value={GetFilterValue(activeFilters, "duration", isRangeObject)}
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
