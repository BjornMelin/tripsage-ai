/**
 * @fileoverview Rating stars component for displaying activity ratings.
 */

import { StarIcon } from "lucide-react";

/**
 * Rating stars component for displaying activity ratings.
 * 
 * @param value - The rating value to display.
 * @param max - The maximum number of stars to display.
 * @returns The rating stars component.
 */
export function RatingStars({ value, max = 5 }: { value: number; max?: number }) {
  const items = Array.from({ length: max });
  const roundedValue = Math.round(value);
  const ariaLabel = `${roundedValue} out of ${max} stars`;

  return (
    <div className="flex items-center" role="img" aria-label={ariaLabel}>
      {items.map((_, idx) => (
        <StarIcon
          key={`star-${idx}`}
          aria-hidden="true"
          className={`h-3 w-3 ${idx < roundedValue ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground"}`}
        />
      ))}
    </div>
  );
}
