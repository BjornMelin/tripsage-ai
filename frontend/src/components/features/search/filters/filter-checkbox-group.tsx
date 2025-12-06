/**
 * @fileoverview Multi-select checkbox group filter component.
 *
 * Uses shadcn/ui Checkbox for multi-select filters like airlines, amenities.
 */

"use client";

import { useCallback, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";

export interface FilterOption {
  /** Unique value for the option */
  value: string;
  /** Display label */
  label: string;
  /** Optional count to display */
  count?: number;
  /** Whether the option is disabled */
  disabled?: boolean;
}

export interface FilterCheckboxGroupProps {
  /** Unique identifier for the filter */
  filterId: string;
  /** Display label for the filter */
  label: string;
  /** Available options */
  options: readonly FilterOption[];
  /** Currently selected values */
  value?: string[];
  /** Callback when selection changes */
  onChange: (filterId: string, value: string[]) => void;
  /** Maximum height before scrolling */
  maxHeight?: number;
  /** Show select all / none buttons */
  showSelectAll?: boolean;
  /** Whether the filter is disabled */
  disabled?: boolean;
}

/**
 * Multi-select checkbox group filter.
 *
 * @example
 * ```tsx
 * <FilterCheckboxGroup
 *   filterId="airlines"
 *   label="Airlines"
 *   options={[
 *     { value: "AA", label: "American Airlines", count: 12 },
 *     { value: "UA", label: "United Airlines", count: 8 },
 *   ]}
 *   value={["AA"]}
 *   onChange={(id, val) => setFilter(id, val)}
 * />
 * ```
 */
export function FilterCheckboxGroup({
  filterId,
  label,
  options,
  value = [],
  onChange,
  maxHeight = 200,
  showSelectAll = true,
  disabled = false,
}: FilterCheckboxGroupProps) {
  const selectedSet = useMemo(() => new Set(value), [value]);

  const handleToggle = useCallback(
    (optionValue: string, checked: boolean) => {
      const newValue = checked
        ? [...value, optionValue]
        : value.filter((v) => v !== optionValue);
      onChange(filterId, newValue);
    },
    [filterId, value, onChange]
  );

  const handleSelectAll = useCallback(() => {
    const enabledOptions = options
      .filter((opt) => !opt.disabled)
      .map((opt) => opt.value);
    onChange(filterId, enabledOptions);
  }, [filterId, options, onChange]);

  const handleSelectNone = useCallback(() => {
    onChange(filterId, []);
  }, [filterId, onChange]);

  const allSelected = useMemo(() => {
    const enabledOptions = options.filter((opt) => !opt.disabled);
    return (
      enabledOptions.length > 0 &&
      enabledOptions.every((opt) => selectedSet.has(opt.value))
    );
  }, [options, selectedSet]);

  const noneSelected = value.length === 0;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">{label}</Label>
        {showSelectAll && (
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs"
              onClick={handleSelectAll}
              disabled={disabled || allSelected}
            >
              All
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs"
              onClick={handleSelectNone}
              disabled={disabled || noneSelected}
            >
              None
            </Button>
          </div>
        )}
      </div>

      <ScrollArea className="pr-4" style={{ maxHeight }}>
        <div className="space-y-2">
          {options.map((option) => (
            <div key={option.value} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Checkbox
                  id={`${filterId}-${option.value}`}
                  checked={selectedSet.has(option.value)}
                  onCheckedChange={(checked) =>
                    handleToggle(option.value, checked === true)
                  }
                  disabled={disabled || option.disabled}
                />
                <Label
                  htmlFor={`${filterId}-${option.value}`}
                  className="text-sm font-normal cursor-pointer"
                >
                  {option.label}
                </Label>
              </div>
              {option.count !== undefined && (
                <span className="text-xs text-muted-foreground tabular-nums">
                  ({option.count})
                </span>
              )}
            </div>
          ))}
        </div>
      </ScrollArea>

      {value.length > 0 && (
        <p className="text-xs text-muted-foreground">{value.length} selected</p>
      )}
    </div>
  );
}
