/**
 * @fileoverview DestinationCard component for displaying travel destination information
 * with ratings, climate data, attractions, and interactive selection actions.
 */

"use client";

import { Calendar, CloudRain, Globe, MapPin, Star, Thermometer } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Destination } from "@/types/search";

/**
 * Props interface for the DestinationCard component.
 */
interface DestinationCardProps {
  /** Destination data to display in the card. */
  destination: Destination;
  /** Callback when destination is selected. */
  onSelect?: (destination: Destination) => void;
  /** Callback when destination is added to comparison. */
  onCompare?: (destination: Destination) => void;
  /** Callback when destination details are requested. */
  onViewDetails?: (destination: Destination) => void;
}

/**
 * DestinationCard component displaying comprehensive destination information.
 *
 * Shows destination name, address, rating, climate data, attractions, popularity,
 * and provides interactive buttons for selection, comparison, and details view.
 *
 * @param destination - The destination data to display.
 * @param onSelect - Callback fired when destination is selected.
 * @param onCompare - Callback fired when destination is added to comparison.
 * @param onViewDetails - Callback fired when details are requested.
 * @returns The DestinationCard component.
 */
export function DestinationCard({
  destination,
  onSelect,
  onCompare,
  onViewDetails,
}: DestinationCardProps) {
  /**
   * Format destination types into human-readable labels.
   *
   * @param types - Array of destination type identifiers.
   * @returns Formatted string of destination types.
   */
  const formatDestinationType = (types: string[]) => {
    const typeMap: Record<string, string> = {
      administrative_area: "Region",
      country: "Country",
      establishment: "Landmark",
      locality: "City",
      natural_feature: "Natural Feature",
      political: "Administrative",
      tourist_attraction: "Attraction",
    };

    return types
      .map((type) => typeMap[type] || type.replace(/_/g, " "))
      .slice(0, 2)
      .join(", ");
  };

  /**
   * Get appropriate icon component based on destination types.
   *
   * @param types - Array of destination type identifiers.
   * @returns React icon component for the destination type.
   */
  const getDestinationIcon = (types: string[]) => {
    if (types.includes("country")) {
      return <Globe className="h-4 w-4" />;
    }
    if (types.includes("establishment") || types.includes("tourist_attraction")) {
      return <Star className="h-4 w-4" />;
    }
    return <MapPin className="h-4 w-4" />;
  };

  /**
   * Format best time to visit months into a readable string.
   *
   * @param months - Array of month identifiers.
   * @returns Formatted string of best visit months.
   */
  const formatBestTimeToVisit = (months: string[]) => {
    if (!months || months.length === 0) return "Year-round";

    // const monthNames = [ // Future implementation
    //   "Jan",
    //   "Feb",
    //   "Mar",
    //   "Apr",
    //   "May",
    //   "Jun",
    //   "Jul",
    //   "Aug",
    //   "Sep",
    //   "Oct",
    //   "Nov",
    //   "Dec",
    // ];

    return months.slice(0, 3).join(", ");
  };

  return (
    <Card className="h-full hover:shadow-lg transition-shadow duration-200">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg line-clamp-2 mb-2">
              {destination.name}
            </CardTitle>
            <div className="flex items-center text-sm text-muted-foreground mb-2">
              {getDestinationIcon(destination.types)}
              <span className="ml-1">{destination.formattedAddress}</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="text-xs">
                {formatDestinationType(destination.types)}
              </Badge>
              {destination.rating && (
                <div className="flex items-center text-sm">
                  <Star className="h-3 w-3 fill-yellow-400 text-yellow-400 mr-1" />
                  <span className="font-medium">{destination.rating.toFixed(1)}</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Description */}
        {destination.description && (
          <p className="text-sm text-muted-foreground line-clamp-3">
            {destination.description}
          </p>
        )}

        {/* Climate Info */}
        {destination.climate && (
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="flex items-center text-muted-foreground">
              <Thermometer className="h-3 w-3 mr-1" />
              <span>{destination.climate.averageTemp}°C avg</span>
            </div>
            <div className="flex items-center text-muted-foreground">
              <CloudRain className="h-3 w-3 mr-1" />
              <span>{destination.climate.rainfall}mm rain</span>
            </div>
          </div>
        )}

        {/* Best Time to Visit */}
        <div className="flex items-center text-xs text-muted-foreground">
          <Calendar className="h-3 w-3 mr-1" />
          <span>Best: {formatBestTimeToVisit(destination.bestTimeToVisit ?? [])}</span>
        </div>

        {/* Top Attractions */}
        {destination.attractions && destination.attractions.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-medium text-muted-foreground">
              Top Attractions:
            </div>
            <div className="flex flex-wrap gap-1">
              {destination.attractions.slice(0, 3).map((attraction) => (
                <Badge key={attraction} variant="outline" className="text-xs">
                  {attraction}
                </Badge>
              ))}
              {destination.attractions.length > 3 && (
                <Badge variant="outline" className="text-xs">
                  +{destination.attractions.length - 3} more
                </Badge>
              )}
            </div>
          </div>
        )}

        {/* Popularity Score */}
        {destination.popularityScore && (
          <div className="text-xs text-muted-foreground">
            Popularity: {destination.popularityScore}/100
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2">
          {onSelect && (
            <Button size="sm" onClick={() => onSelect(destination)} className="flex-1">
              Select
            </Button>
          )}
          {onViewDetails && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onViewDetails(destination)}
            >
              Details
            </Button>
          )}
          {onCompare && (
            <Button size="sm" variant="outline" onClick={() => onCompare(destination)}>
              Compare
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
