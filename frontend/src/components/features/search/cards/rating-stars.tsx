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
  const roundedValue = Math.round(value);
  const stars = Array.from({ length: max }, (_, idx) => ({
    filled: idx < roundedValue,
    key: `star-${idx + 1}`,
  }));

  return (
    <div
      className="flex items-center"
      role="img"
      aria-label={`Rating: ${roundedValue} out of ${max} stars`}
    >
      {stars.map((star) => (
        <StarIcon
          key={star.key}
          aria-hidden="true"
          className={`h-3 w-3 ${star.filled ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground"}`}
        />
      ))}
    </div>
  );
}
