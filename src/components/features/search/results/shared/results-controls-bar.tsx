/**
 * @fileoverview Controls bar component for search results.
 *
 * Provides sort, filter, and view mode controls with optional
 * comparison selection UI.
 */

"use client";

import {
  ArrowUpDownIcon,
  FilterIcon,
  Grid3X3Icon,
  ListIcon,
  MapIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import type { SortDirection, ViewMode } from "./use-results-list";

/** Sort option configuration. */
export interface SortOption<S extends string> {
  /** Sort field value. */
  value: S;
  /** Display label. */
  label: string;
}

/** Props for the ResultsControlsBar component. */
export interface ResultsControlsBarProps<S extends string> {
  /** Number of results found. */
  resultCount: number;
  /** Label for the result type (e.g., "flights", "hotels"). */
  resultLabel: string;
  /** Current sort field. */
  sortBy: S;
  /** Available sort options. */
  sortOptions: SortOption<S>[];
  /** Current sort direction. */
  sortDirection: SortDirection;
  /** Current view mode. */
  viewMode: ViewMode;
  /** Whether to show the map view option. */
  showMapView?: boolean;
  /** Callback when sort field changes. */
  onSortChange: (field: S) => void;
  /** Callback when sort direction toggles. */
  onDirectionToggle: () => void;
  /** Callback when view mode changes. */
  onViewModeChange: (mode: ViewMode) => void;
  /** Callback when filter button is clicked. */
  onOpenFilters?: () => void;
  /** Number of items selected for comparison. */
  selectedCount?: number;
  /** Maximum items that can be compared. */
  maxCompare?: number;
  /** Callback to clear comparison selection. */
  onClearSelection?: () => void;
  /** Callback to trigger comparison. */
  onCompare?: () => void;
  /** Additional content to render in the controls bar. */
  children?: ReactNode;
  /** Test ID for the component. */
  testId?: string;
}

/**
 * Controls bar component for search results.
 *
 * Provides a consistent UI for sorting, filtering, and view mode
 * selection across different result types.
 *
 * @example
 * ```tsx
 * <ResultsControlsBar
 *   resultCount={flights.length}
 *   resultLabel="flights"
 *   sortBy={sortBy}
 *   sortOptions={[
 *     { value: "price", label: "Price" },
 *     { value: "duration", label: "Duration" },
 *   ]}
 *   sortDirection={sortDirection}
 *   viewMode={viewMode}
 *   onSortChange={setSortBy}
 *   onDirectionToggle={toggleSortDirection}
 *   onViewModeChange={setViewMode}
 *   onOpenFilters={handleOpenFilters}
 * />
 * ```
 */
export function ResultsControlsBar<S extends string>({
  resultCount,
  resultLabel,
  sortBy,
  sortOptions,
  sortDirection,
  viewMode,
  showMapView = false,
  onSortChange,
  onDirectionToggle,
  onViewModeChange,
  onOpenFilters,
  selectedCount = 0,
  maxCompare,
  onClearSelection,
  onCompare,
  children,
  testId,
}: ResultsControlsBarProps<S>) {
  const hasSelection = selectedCount > 0 && onCompare;
  const canCompare = selectedCount >= 2;

  return (
    <Card className="p-4" data-testid={testId}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium">
            {resultCount} {resultLabel} found
          </span>
          <Separator orientation="vertical" className="h-4" />
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={onOpenFilters}
              disabled={!onOpenFilters}
              aria-label={onOpenFilters ? "Open filters" : "Filters unavailable"}
            >
              <FilterIcon className="h-4 w-4 mr-2" />
              Filters
            </Button>
            <Select value={sortBy} onValueChange={(value) => onSortChange(value as S)}>
              <SelectTrigger aria-label={`Sort ${resultLabel}`} className="w-40 h-9">
                <div className="flex items-center gap-2">
                  <ArrowUpDownIcon className="h-4 w-4" />
                  <SelectValue placeholder="Sort" />
                </div>
              </SelectTrigger>
              <SelectContent>
                {sortOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              variant="ghost"
              size="sm"
              onClick={onDirectionToggle}
              aria-label={`Sort direction: ${sortDirection}`}
            >
              {sortDirection === "asc" ? "↑ Asc" : "↓ Desc"}
            </Button>
          </div>
        </div>

        <fieldset className="flex items-center gap-2" aria-label="View mode options">
          <Button
            variant={viewMode === "list" ? "default" : "outline"}
            size="sm"
            onClick={() => onViewModeChange("list")}
            aria-pressed={viewMode === "list"}
            data-state={viewMode === "list" ? "on" : "off"}
            aria-label="List view"
          >
            <ListIcon className="h-4 w-4" />
          </Button>
          <Button
            variant={viewMode === "grid" ? "default" : "outline"}
            size="sm"
            onClick={() => onViewModeChange("grid")}
            aria-pressed={viewMode === "grid"}
            data-state={viewMode === "grid" ? "on" : "off"}
            aria-label="Grid view"
          >
            <Grid3X3Icon className="h-4 w-4" />
          </Button>
          {showMapView && (
            <Button
              variant={viewMode === "map" ? "default" : "outline"}
              size="sm"
              onClick={() => onViewModeChange("map")}
              aria-pressed={viewMode === "map"}
              data-state={viewMode === "map" ? "on" : "off"}
              aria-label="Map view"
            >
              <MapIcon className="h-4 w-4" />
            </Button>
          )}
        </fieldset>
      </div>

      {/* Comparison selection bar */}
      {hasSelection && (
        <div className="mt-3 pt-3 border-t">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">
              {selectedCount} {selectedCount > 1 ? "items" : "item"} selected
              {maxCompare ? ` (max ${maxCompare})` : ""} for comparison
            </span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={onClearSelection}>
                Clear
              </Button>
              <Button size="sm" onClick={onCompare} disabled={!canCompare}>
                Compare ({selectedCount})
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Additional content */}
      {children}
    </Card>
  );
}
