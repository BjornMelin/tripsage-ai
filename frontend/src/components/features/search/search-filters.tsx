"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { FilterOption, SearchType } from "@/types/search";
import { useState } from "react";

interface SearchFiltersProps {
  type: SearchType;
  filters: FilterOption[];
  onApplyFilters?: (filters: Record<string, unknown>) => void;
  onResetFilters?: () => void;
}

export function SearchFilters({
  type,
  filters,
  onApplyFilters,
  onResetFilters,
}: SearchFiltersProps) {
  const [activeFilters, setActiveFilters] = useState<Record<string, unknown>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const handleFilterChange = (filterId: string, value: any) => {
    setActiveFilters((prev) => ({
      ...prev,
      [filterId]: value,
    }));
  };

  const handleToggleExpand = (filterId: string) => {
    setExpanded((prev) => ({
      ...prev,
      [filterId]: !prev[filterId],
    }));
  };

  const handleApplyFilters = () => {
    if (onApplyFilters) {
      onApplyFilters(activeFilters);
    }
  };

  const handleResetFilters = () => {
    setActiveFilters({});

    if (onResetFilters) {
      onResetFilters();
    }
  };

  // Group filters by type for better organization
  const groupedFilters: Record<string, FilterOption[]> = {};

  filters.forEach((filter) => {
    if (!groupedFilters[filter.type]) {
      groupedFilters[filter.type] = [];
    }
    groupedFilters[filter.type].push(filter);
  });

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <CardTitle>Filters</CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleResetFilters}
            disabled={Object.keys(activeFilters).length === 0}
          >
            Reset All
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {Object.entries(groupedFilters).map(([type, filtersGroup]) => (
            <div key={type} className="space-y-2">
              <h3 className="text-sm font-semibold capitalize">{type} Filters</h3>
              <div className="space-y-2">
                {filtersGroup.map((filter) => (
                  <div key={filter.id} className="space-y-2">
                    <div
                      className="flex justify-between items-center cursor-pointer"
                      onClick={() => handleToggleExpand(filter.id)}
                    >
                      <span className="text-sm">{filter.label}</span>
                      <span>{expanded[filter.id] ? "−" : "+"}</span>
                    </div>

                    {expanded[filter.id] && (
                      <div className="pl-2 border-l-2 border-muted">
                        {filter.type === "checkbox" && filter.options && (
                          <div className="space-y-1">
                            {filter.options.map((option, index) => (
                              <label
                                key={`${filter.id}-checkbox-${option.value}-${index}`}
                                className="flex items-center space-x-2 text-sm"
                              >
                                <input
                                  type="checkbox"
                                  checked={
                                    Array.isArray(activeFilters[filter.id]) &&
                                    (activeFilters[filter.id] as any[])?.includes(
                                      option.value
                                    )
                                  }
                                  onChange={(e) => {
                                    const currentValues = Array.isArray(
                                      activeFilters[filter.id]
                                    )
                                      ? (activeFilters[filter.id] as any[])
                                      : [];

                                    if (e.target.checked) {
                                      handleFilterChange(filter.id, [
                                        ...currentValues,
                                        option.value,
                                      ]);
                                    } else {
                                      handleFilterChange(
                                        filter.id,
                                        (currentValues as any[]).filter(
                                          (v: string) => v !== option.value
                                        )
                                      );
                                    }
                                  }}
                                  className="h-4 w-4"
                                />
                                <span>{option.label}</span>
                                {option.count !== undefined && (
                                  <span className="text-xs text-muted-foreground">
                                    ({option.count})
                                  </span>
                                )}
                              </label>
                            ))}
                          </div>
                        )}

                        {filter.type === "radio" && filter.options && (
                          <div className="space-y-1">
                            {filter.options.map((option, index) => (
                              <label
                                key={`${filter.id}-radio-${option.value}-${index}`}
                                className="flex items-center space-x-2 text-sm"
                              >
                                <input
                                  type="radio"
                                  name={filter.id}
                                  checked={activeFilters[filter.id] === option.value}
                                  onChange={() =>
                                    handleFilterChange(filter.id, option.value)
                                  }
                                  className="h-4 w-4"
                                />
                                <span>{option.label}</span>
                                {option.count !== undefined && (
                                  <span className="text-xs text-muted-foreground">
                                    ({option.count})
                                  </span>
                                )}
                              </label>
                            ))}
                          </div>
                        )}

                        {filter.type === "range" && (
                          <div className="space-y-2">
                            <div className="flex space-x-2">
                              <input
                                type="number"
                                placeholder="Min"
                                value={(activeFilters[filter.id] as any)?.min || ""}
                                onChange={(e) => {
                                  const min = e.target.value
                                    ? Number(e.target.value)
                                    : undefined;
                                  const max = (activeFilters[filter.id] as any)?.max;
                                  handleFilterChange(filter.id, { min, max });
                                }}
                                className="flex-1 h-8 rounded-md border px-3 py-1 text-sm"
                              />
                              <input
                                type="number"
                                placeholder="Max"
                                value={(activeFilters[filter.id] as any)?.max || ""}
                                onChange={(e) => {
                                  const min = (activeFilters[filter.id] as any)?.min;
                                  const max = e.target.value
                                    ? Number(e.target.value)
                                    : undefined;
                                  handleFilterChange(filter.id, { min, max });
                                }}
                                className="flex-1 h-8 rounded-md border px-3 py-1 text-sm"
                              />
                            </div>
                          </div>
                        )}

                        {filter.type === "select" && filter.options && (
                          <select
                            value={(activeFilters[filter.id] as string) || ""}
                            onChange={(e) =>
                              handleFilterChange(filter.id, e.target.value)
                            }
                            className="w-full h-8 rounded-md border px-3 py-1 text-sm"
                          >
                            <option value="">Select {filter.label}</option>
                            {filter.options.map((option, index) => (
                              <option
                                key={`${filter.id}-option-${option.value}-${index}`}
                                value={String(option.value)}
                              >
                                {option.label}
                              </option>
                            ))}
                          </select>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}

          <Button
            className="w-full"
            onClick={handleApplyFilters}
            disabled={Object.keys(activeFilters).length === 0}
          >
            Apply Filters
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
