/**
 * @fileoverview Reusable range filter component with dual-thumb slider.
 *
 * Uses shadcn/ui Slider for price range, duration, and similar filters.
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";

export interface FilterRangeProps {
  /** Unique identifier for the filter */
  filterId: string;
  /** Display label for the filter */
  label: string;
  /** Minimum allowed value */
  min: number;
  /** Maximum allowed value */
  max: number;
  /** Step increment */
  step?: number;
  /** Current value as [min, max] tuple */
  value?: [number, number];
  /** Callback when value changes */
  onChange: (filterId: string, value: { min: number; max: number }) => void;
  /** Format function for displaying values */
  formatValue?: (value: number) => string;
  /** Optional description */
  description?: string;
  /** Whether the filter is disabled */
  disabled?: boolean;
}

/** Default value formatter */
const DEFAULT_FORMAT_VALUE = (value: number) => value.toLocaleString();

/**
 * Range filter component with dual-thumb slider.
 *
 * @example
 * ```tsx
 * <FilterRange
 *   filterId="price_range"
 *   label="Price"
 *   min={0}
 *   max={2000}
 *   value={[100, 500]}
 *   onChange={(id, val) => setFilter(id, val)}
 *   formatValue={(v) => `$${v}`}
 * />
 * ```
 */
export function FilterRange({
  filterId,
  label,
  min,
  max,
  step = 1,
  value,
  onChange,
  formatValue = DEFAULT_FORMAT_VALUE,
  description,
  disabled = false,
}: FilterRangeProps) {
  // Validate range parameters
  if (min >= max || step <= 0) {
    console.error(
      `Invalid FilterRange props for "${filterId}": min (${min}) must be < max (${max}), and step (${step}) must be > 0`
    );
    return null;
  }

  // Clamp initial value to valid range
  const clampedValue: [number, number] = value
    ? [Math.max(min, Math.min(max, value[0])), Math.max(min, Math.min(max, value[1]))]
    : [min, max];

  // Internal state for smooth slider interaction
  const [internalValue, setInternalValue] = useState<[number, number]>(clampedValue);

  // Sync with external value
  useEffect(() => {
    if (value) {
      setInternalValue(value);
    }
  }, [value]);

  const handleValueChange = useCallback((newValue: number[]) => {
    const rangeValue: [number, number] = [newValue[0], newValue[1]];
    setInternalValue(rangeValue);
  }, []);

  const handleValueCommit = useCallback(
    (newValue: number[]) => {
      onChange(filterId, { max: newValue[1], min: newValue[0] });
    },
    [filterId, onChange]
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label htmlFor={filterId} className="text-sm font-medium">
          {label}
        </Label>
        <span className="text-sm text-muted-foreground tabular-nums">
          {formatValue(internalValue[0])} – {formatValue(internalValue[1])}
        </span>
      </div>

      {description && <p className="text-xs text-muted-foreground">{description}</p>}

      <Slider
        id={filterId}
        min={min}
        max={max}
        step={step}
        value={internalValue}
        onValueChange={handleValueChange}
        onValueCommit={handleValueCommit}
        disabled={disabled}
        className="w-full"
        aria-label={`${label} range from ${formatValue(min)} to ${formatValue(max)}`}
      />

      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{formatValue(min)}</span>
        <span>{formatValue(max)}</span>
      </div>
    </div>
  );
}
