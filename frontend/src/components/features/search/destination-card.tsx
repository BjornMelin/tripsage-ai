"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Destination } from "@/types/search";
import { Calendar, CloudRain, Globe, MapPin, Star, Thermometer } from "lucide-react";

interface DestinationCardProps {
  destination: Destination;
  onSelect?: (destination: Destination) => void;
  onCompare?: (destination: Destination) => void;
  onViewDetails?: (destination: Destination) => void;
}

export function DestinationCard({
  destination,
  onSelect,
  onCompare,
  onViewDetails,
}: DestinationCardProps) {
  const formatDestinationType = (types: string[]) => {
    const typeMap: Record<string, string> = {
      locality: "City",
      country: "Country",
      administrative_area: "Region",
      establishment: "Landmark",
      political: "Administrative",
      natural_feature: "Natural Feature",
      tourist_attraction: "Attraction",
    };

    return types
      .map((type) => typeMap[type] || type.replace(/_/g, " "))
      .slice(0, 2)
      .join(", ");
  };

  const getDestinationIcon = (types: string[]) => {
    if (types.includes("country")) {
      return <Globe className="h-4 w-4" />;
    }
    if (types.includes("establishment") || types.includes("tourist_attraction")) {
      return <Star className="h-4 w-4" />;
    }
    return <MapPin className="h-4 w-4" />;
  };

  const formatBestTimeToVisit = (months: string[]) => {
    if (!months || months.length === 0) return "Year-round";

    const _monthNames = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];

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
        {destination.bestTimeToVisit && (
          <div className="flex items-center text-xs text-muted-foreground">
            <Calendar className="h-3 w-3 mr-1" />
            <span>Best: {formatBestTimeToVisit(destination.bestTimeToVisit)}</span>
          </div>
        )}

        {/* Top Attractions */}
        {destination.attractions && destination.attractions.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-medium text-muted-foreground">
              Top Attractions:
            </div>
            <div className="flex flex-wrap gap-1">
              {destination.attractions.slice(0, 3).map((attraction, index) => (
                <Badge
                  key={`${attraction}-${index}`}
                  variant="outline"
                  className="text-xs"
                >
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
