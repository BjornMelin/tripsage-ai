/**
 * @fileoverview Flight results grid with filters, tags, and sorting controls.
 */

"use client";

import type { FlightResult } from "@schemas/search";
import { PlaneIcon } from "lucide-react";
import { useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { FlightCard } from "../cards/flight-card";
import { ResultsControlsBar } from "./shared/results-controls-bar";
import { ResultsEmptyState } from "./shared/results-empty-state";
import { ResultsLoadingSkeleton } from "./shared/results-loading-skeleton";
import type { SortDirection, ViewMode } from "./shared/use-results-list";
import { useResultsList } from "./shared/use-results-list";

/** Narrow ViewMode to flight-compatible modes (no map view). */
function ToFlightViewMode(mode: ViewMode): "list" | "grid" {
  return mode === "map" ? "list" : mode;
}

type FlightSortField = "price" | "duration" | "departure" | "emissions";

/** Sort options for flight results. */
const FLIGHT_SORT_OPTIONS: Array<{ value: FlightSortField; label: string }> = [
  { label: "Price", value: "price" },
  { label: "Duration", value: "duration" },
  { label: "Departure", value: "departure" },
  { label: "Emissions", value: "emissions" },
];

/** Flight results component props */
interface FlightResultsProps {
  results: FlightResult[];
  loading?: boolean;
  onSelect: (flight: FlightResult) => Promise<void>;
  onCompare: (flights: FlightResult[]) => void;
  onModifySearch?: () => void;
  className?: string;
}

/** Flight comparator for sorting. */
function CompareFlights(
  first: FlightResult,
  second: FlightResult,
  sortBy: FlightSortField,
  sortDirection: SortDirection
): number {
  const direction = sortDirection === "asc" ? 1 : -1;
  switch (sortBy) {
    case "price":
      return direction * (first.price.total - second.price.total);
    case "duration":
      return direction * (first.duration - second.duration);
    case "departure":
      return (
        direction *
        (new Date(`${first.departure.date}T${first.departure.time}`).getTime() -
          new Date(`${second.departure.date}T${second.departure.time}`).getTime())
      );
    case "emissions":
      return direction * (first.emissions.kg - second.emissions.kg);
    default:
      return 0;
  }
}

/** Flight results grid with filters, tags, and sorting controls. */
export function FlightResults({
  results,
  loading = false,
  onSelect,
  onCompare,
  onModifySearch,
  className,
}: FlightResultsProps) {
  const {
    sortedResults,
    sortBy,
    sortDirection,
    viewMode,
    isPending,
    selectedIds,
    optimisticSelectingId,
    setSortBy,
    toggleSortDirection,
    setViewMode,
    toggleSelection,
    clearSelection,
    getSelectedItems,
    handleSelect,
  } = useResultsList<FlightResult, FlightSortField>({
    compare: CompareFlights,
    defaultDirection: "asc",
    defaultSort: "price",
    defaultViewMode: "list",
    errorContext: "FlightResults",
    getId: (flight) => flight.id,
    maxSelections: 3,
    results,
  });

  /** Handle flight selection. */
  const handleFlightSelect = useCallback(
    (flight: FlightResult) => {
      handleSelect(flight, onSelect);
    },
    [handleSelect, onSelect]
  );

  /** Handle comparison. */
  const handleCompare = useCallback(() => {
    onCompare(getSelectedItems());
  }, [onCompare, getSelectedItems]);

  if (loading) {
    return (
      <ResultsLoadingSkeleton
        variant="flight"
        count={3}
        testId="flight-results-loading"
      />
    );
  }

  if (results.length === 0) {
    return (
      <ResultsEmptyState
        icon={PlaneIcon}
        title="No flights found"
        description="Try adjusting your search dates or filters"
        actionLabel="Modify Search"
        onAction={onModifySearch}
      />
    );
  }

  return (
    <div
      className={cn("space-y-4", className)}
      data-view-mode={viewMode}
      data-testid="flight-results-container"
    >
      <ResultsControlsBar
        resultCount={results.length}
        resultLabel="flights"
        sortBy={sortBy}
        sortOptions={FLIGHT_SORT_OPTIONS}
        sortDirection={sortDirection}
        viewMode={viewMode}
        onSortChange={setSortBy}
        onDirectionToggle={toggleSortDirection}
        onViewModeChange={setViewMode}
        onOpenFilters={onModifySearch}
        selectedCount={selectedIds.size}
        maxCompare={3}
        onClearSelection={clearSelection}
        onCompare={handleCompare}
        testId="flight-results-controls"
      />

      {/* Flight Results */}
      <div className="space-y-3">
        {sortedResults.map((flight) => (
          <FlightCard
            key={flight.id}
            flight={flight}
            viewMode={ToFlightViewMode(viewMode)}
            isSelected={selectedIds.has(flight.id)}
            isOptimisticSelecting={optimisticSelectingId === flight.id}
            isPending={isPending}
            onSelect={() => handleFlightSelect(flight)}
            onToggleComparison={() => toggleSelection(flight.id)}
          />
        ))}
      </div>

      {/* Load More */}
      {sortedResults.length > 0 && (
        <Card className="p-4 text-center">
          <Button variant="outline">Load More Flights</Button>
        </Card>
      )}
    </div>
  );
}
