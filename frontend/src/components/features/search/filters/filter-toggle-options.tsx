/**
 * @fileoverview Toggle options filter component using shadcn/ui ToggleGroup.
 *
 * Used for filters like stops (Any/Nonstop/1/2+), time of day, etc.
 */

"use client";

import { useCallback } from "react";
import { Label } from "@/components/ui/label";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

export interface ToggleOption {
  /** Unique value for the option */
  value: string;
  /** Display label */
  label: string;
  /** Optional icon to display */
  icon?: React.ReactNode;
  /** Whether the option is disabled */
  disabled?: boolean;
}

export interface FilterToggleOptionsProps {
  /** Unique identifier for the filter */
  filterId: string;
  /** Display label for the filter */
  label: string;
  /** Available options */
  options: ToggleOption[];
  /** Current value (single for single-select, array for multi-select) */
  value?: string | string[];
  /** Callback when selection changes */
  onChange: (filterId: string, value: string | string[]) => void;
  /** Whether multiple options can be selected */
  multiple?: boolean;
  /** Whether the filter is disabled */
  disabled?: boolean;
  /** Optional description */
  description?: string;
}

/**
 * Toggle options filter using ToggleGroup.
 *
 * @example
 * ```tsx
 * // Single select
 * <FilterToggleOptions
 *   filterId="stops"
 *   label="Stops"
 *   options={[
 *     { value: "any", label: "Any" },
 *     { value: "0", label: "Nonstop" },
 *     { value: "1", label: "1 Stop" },
 *     { value: "2+", label: "2+" },
 *   ]}
 *   value="any"
 *   onChange={(id, val) => setFilter(id, val)}
 * />
 *
 * // Multi select
 * <FilterToggleOptions
 *   filterId="departure_time"
 *   label="Departure Time"
 *   multiple
 *   options={[
 *     { value: "morning", label: "Morning" },
 *     { value: "afternoon", label: "Afternoon" },
 *     { value: "evening", label: "Evening" },
 *   ]}
 *   value={["morning", "afternoon"]}
 *   onChange={(id, val) => setFilter(id, val)}
 * />
 * ```
 */
export function FilterToggleOptions({
  filterId,
  label,
  options,
  value,
  onChange,
  multiple = false,
  disabled = false,
  description,
}: FilterToggleOptionsProps) {
  const handleValueChange = useCallback(
    (newValue: string | string[]) => {
      // For single select, ToggleGroup returns empty string when deselected
      // For multi select, it returns empty array
      if (multiple) {
        onChange(filterId, newValue as string[]);
      } else {
        // Only update if a value is selected (don't allow deselection in single mode)
        if (newValue) {
          onChange(filterId, newValue as string);
        }
      }
    },
    [filterId, multiple, onChange]
  );

  return (
    <div className="space-y-3">
      <div>
        <Label className="text-sm font-medium">{label}</Label>
        {description && (
          <p className="text-xs text-muted-foreground mt-1">{description}</p>
        )}
      </div>

      {multiple ? (
        <ToggleGroup
          type="multiple"
          value={Array.isArray(value) ? value : []}
          onValueChange={handleValueChange}
          disabled={disabled}
          className="flex flex-wrap gap-1"
        >
          {options.map((option) => (
            <ToggleGroupItem
              key={option.value}
              value={option.value}
              disabled={option.disabled}
              className="px-3 py-1.5 text-xs"
              aria-label={option.label}
            >
              {option.icon && <span className="mr-1">{option.icon}</span>}
              {option.label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      ) : (
        <ToggleGroup
          type="single"
          value={typeof value === "string" ? value : undefined}
          onValueChange={handleValueChange}
          disabled={disabled}
          className="flex flex-wrap gap-1"
        >
          {options.map((option) => (
            <ToggleGroupItem
              key={option.value}
              value={option.value}
              disabled={option.disabled}
              className="px-3 py-1.5 text-xs"
              aria-label={option.label}
            >
              {option.icon && <span className="mr-1">{option.icon}</span>}
              {option.label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      )}
    </div>
  );
}
