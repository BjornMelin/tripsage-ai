/**
 * @fileoverview Accommodation card component for displaying accommodation information.
 */

import {
  Car,
  Coffee,
  Dumbbell,
  MapPin,
  Star,
  Utensils,
  Waves,
  Wifi,
} from "lucide-react";
import Image from "next/image";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { Accommodation } from "@/lib/schemas/search";

interface AccommodationCardProps {
  accommodation: Accommodation;
  onSelect?: (accommodation: Accommodation) => void;
  onCompare?: (accommodation: Accommodation) => void;
}

const AmenityIcons: Record<string, React.ReactNode> = {
  breakfast: <Coffee className="h-4 w-4" />,
  gym: <Dumbbell className="h-4 w-4" />,
  parking: <Car className="h-4 w-4" />,
  pool: <Waves className="h-4 w-4" />,
  restaurant: <Utensils className="h-4 w-4" />,
  wifi: <Wifi className="h-4 w-4" />,
};

export function AccommodationCard({
  accommodation,
  onSelect,
  onCompare,
}: AccommodationCardProps) {
  const nights = Math.ceil(
    (new Date(accommodation.checkOut).getTime() -
      new Date(accommodation.checkIn).getTime()) /
      (1000 * 60 * 60 * 24)
  );

  return (
    <Card className="overflow-hidden hover:shadow-lg transition-shadow">
      <div className="flex">
        <div className="w-1/3 h-48 bg-muted flex items-center justify-center">
          {accommodation.images?.[0] ? (
            <Image
              src={accommodation.images[0]}
              alt={accommodation.name}
              fill
              className="object-cover"
            />
          ) : (
            <span className="text-muted-foreground">No image</span>
          )}
        </div>
        <CardContent className="flex-1 p-4">
          <div className="flex justify-between items-start mb-2">
            <div className="flex-1">
              <h3 className="font-semibold text-lg line-clamp-1">
                {accommodation.name}
              </h3>
              <div className="flex items-center gap-2 mt-1">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground line-clamp-1">
                  {accommodation.location}
                </span>
              </div>
            </div>
            <div className="text-right">
              <div className="flex items-center gap-1">
                <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                <span className="font-medium">{accommodation.rating}</span>
              </div>
              <Badge variant="secondary" className="mt-1">
                {accommodation.type}
              </Badge>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 mb-3">
            {accommodation.amenities?.slice(0, 6).map((amenity) => (
              <div
                key={amenity}
                className="flex items-center gap-1 text-xs text-muted-foreground"
              >
                {AmenityIcons[amenity] || (
                  <span className="h-4 w-4 rounded-full bg-muted" />
                )}
                <span className="capitalize">{amenity.replace("_", " ")}</span>
              </div>
            ))}
            {accommodation.amenities.length > 6 && (
              <span className="text-xs text-muted-foreground">
                +{accommodation.amenities.length - 6} more
              </span>
            )}
          </div>

          <div className="flex justify-between items-end">
            <div>
              <div className="text-2xl font-bold">
                ${accommodation.pricePerNight}
                <span className="text-sm font-normal text-muted-foreground">
                  /night
                </span>
              </div>
              <div className="text-sm text-muted-foreground">
                Total: ${accommodation.totalPrice} ({nights} nights)
              </div>
            </div>
            <div className="flex gap-2">
              {onCompare && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onCompare(accommodation)}
                >
                  Compare
                </Button>
              )}
              {onSelect && (
                <Button size="sm" onClick={() => onSelect(accommodation)}>
                  View Details
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </div>
    </Card>
  );
}
