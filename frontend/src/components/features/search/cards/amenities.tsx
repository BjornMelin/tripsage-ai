/**
 * @fileoverview Shared amenity icon map and renderer for search cards.
 */

import {
  CarIcon,
  CoffeeIcon,
  DumbbellIcon,
  SparklesIcon,
  UtensilsIcon,
  WavesIcon,
  WifiIcon,
} from "lucide-react";

/** Map of amenity IDs to their corresponding icon components. */
const amenityIconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  breakfast: CoffeeIcon,
  gym: DumbbellIcon,
  parking: CarIcon,
  pool: WavesIcon,
  restaurant: UtensilsIcon,
  spa: SparklesIcon,
  wifi: WifiIcon,
};

/**
 * Retrieves the icon component for a given amenity ID.
 *
 * Supported amenity IDs: breakfast, gym, parking, pool, restaurant, spa, wifi
 *
 * @param id - The amenity identifier to look up
 * @returns The icon component for the amenity, or undefined if the ID is not recognized
 *
 * @example
 * const BedIcon = getAmenityIcon('breakfast');
 * if (BedIcon) {
 *   return <BedIcon className="h-4 w-4" />;
 * }
 */
export function getAmenityIcon(
  id: string
): React.ComponentType<{ className?: string }> | undefined {
  if (process.env.NODE_ENV === "development" && !amenityIconMap[id]) {
    console.warn(
      `Unknown amenity ID: "${id}". Supported IDs are: ${Object.keys(amenityIconMap).join(", ")}`
    );
  }
  return amenityIconMap[id];
}
