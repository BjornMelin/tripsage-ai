/**
 * @fileoverview Reusable hotel card component for hotel results display.
 */

"use client";

import type { HotelResult } from "@schemas/search";
import {
  Building2Icon,
  CalendarIcon,
  HeartIcon,
  ImageIcon,
  MapPinIcon,
  ShieldIcon,
  SparklesIcon,
  StarIcon,
  TrendingUpIcon,
  ZapIcon,
} from "lucide-react";
import Image from "next/image";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { statusVariants } from "@/lib/variants/status";
import { formatCurrency } from "../common/format";
import { GetAmenityIcon } from "./amenities";
import { RatingStars } from "./rating-stars";

/** Get price history icon based on trend */
export function PriceHistoryIcon({ trend }: { trend: string }) {
  if (trend === "falling")
    return <TrendingUpIcon className="h-3 w-3 text-green-500 rotate-180" />;
  if (trend === "rising") return <TrendingUpIcon className="h-3 w-3 text-red-500" />;
  return null;
}

/** Hotel card component props */
export interface HotelCardProps {
  hotel: HotelResult;
  viewMode: "list" | "grid" | "map";
  isSaved: boolean;
  isOptimisticSelecting: boolean;
  isPending: boolean;
  onSelect: () => void;
  onToggleWishlist: () => void;
}

/** Individual hotel card for results display */
export function HotelCard({
  hotel,
  viewMode,
  isSaved,
  isOptimisticSelecting,
  isPending,
  onSelect,
  onToggleWishlist,
}: HotelCardProps) {
  return (
    <Card
      className={cn(
        "relative transition-all duration-200 hover:shadow-lg",
        isOptimisticSelecting && "opacity-75",
        viewMode === "list" ? "overflow-hidden" : "h-full"
      )}
    >
      {/* AI Recommendation Badge */}
      {hotel.ai.recommendation >= 8 && (
        <div className="absolute top-3 left-3 z-10">
          <Badge className="bg-purple-500 text-white">
            <ZapIcon className="h-3 w-3 mr-1" />
            AI Pick
          </Badge>
        </div>
      )}

      {/* Wishlist Button */}
      <Button
        variant="ghost"
        size="icon"
        className="absolute top-3 right-3 z-10 bg-white/80 hover:bg-white"
        onClick={onToggleWishlist}
        aria-label={isSaved ? "Remove from wishlist" : "Save to wishlist"}
      >
        <HeartIcon
          className={cn(
            "h-4 w-4",
            isSaved ? "fill-red-500 text-red-500" : "text-gray-600"
          )}
        />
      </Button>

      <CardContent
        className={cn("p-0", viewMode === "list" ? "flex" : "flex flex-col h-full")}
      >
        {/* Hotel Image */}
        <div
          className={cn(
            "relative bg-muted flex items-center justify-center",
            viewMode === "list" ? "w-64 h-48" : "h-48 w-full"
          )}
        >
          {hotel.images.main ? (
            <Image
              src={hotel.images.main}
              alt={hotel.name}
              fill
              className="object-cover"
            />
          ) : (
            <div className="flex flex-col items-center text-muted-foreground">
              <ImageIcon className="h-8 w-8 mb-2" />
              <span className="text-sm">No image</span>
            </div>
          )}

          {/* Image Count Badge */}
          {hotel.images.count > 1 && (
            <Badge variant="secondary" className="absolute bottom-2 right-2 text-xs">
              {hotel.images.count} photos
            </Badge>
          )}

          {/* Deals Banner */}
          {hotel.pricing.deals && (
            <div className="absolute bottom-2 left-2">
              <Badge className="bg-red-500 text-white text-xs">
                Save ${hotel.pricing.deals.savings}
              </Badge>
            </div>
          )}
        </div>

        {/* Hotel Details */}
        <div
          className={cn("p-4 flex flex-col", viewMode === "list" ? "flex-1" : "flex-1")}
        >
          {/* Header */}
          <div className="mb-3">
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold text-lg leading-tight mb-1 truncate">
                  {hotel.name}
                </h3>
                <div className="flex items-center gap-2 mb-2">
                  <RatingStars value={hotel.starRating ?? 0} />
                  <span className="text-xs text-muted-foreground">
                    {hotel.category}
                  </span>
                </div>
                <div className="flex items-center gap-1 mb-2">
                  <span className="text-sm font-medium">
                    {hotel.userRating.toFixed(1)}
                  </span>
                  <StarIcon className="h-3 w-3 fill-current text-yellow-500" />
                  <span className="text-xs text-muted-foreground">
                    ({hotel.reviewCount.toLocaleString()} reviews)
                  </span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1 text-sm text-muted-foreground mb-3">
              <MapPinIcon className="h-3 w-3" />
              <span className="truncate">
                {hotel.location.district ?? "Unknown district"},{" "}
                {hotel.location.city ?? "Unknown city"}
              </span>
            </div>
          </div>

          {/* Amenities */}
          <div className="mb-3">
            <div className="flex flex-wrap gap-1">
              {hotel.amenities.essential.slice(0, 4).map((amenity) => {
                const Icon = GetAmenityIcon(amenity) ?? Building2Icon;
                return (
                  <Badge key={amenity} variant="secondary" className="text-xs">
                    <Icon className="h-3 w-3 mr-1" />
                    {amenity}
                  </Badge>
                );
              })}
              {hotel.amenities.essential.length > 4 && (
                <Badge variant="outline" className="text-xs">
                  +{hotel.amenities.essential.length - 4} more
                </Badge>
              )}
            </div>
          </div>

          {/* Special Features */}
          <div className="mb-3 space-y-2">
            {hotel.allInclusive?.available && (
              <Badge className="bg-orange-100 text-orange-800">
                <SparklesIcon className="h-3 w-3 mr-1" />
                All-Inclusive {hotel.allInclusive.tier}
              </Badge>
            )}

            {hotel.sustainability.certified && (
              <Badge className="bg-green-100 text-green-800">
                <ShieldIcon className="h-3 w-3 mr-1" />
                Eco-Certified
              </Badge>
            )}

            {hotel.guestExperience.highlights.length > 0 && (
              <div className="text-xs text-muted-foreground">
                "{hotel.guestExperience.highlights[0]}"
              </div>
            )}
          </div>

          {/* Availability & Urgency */}
          {hotel.availability.urgency === "high" && (
            <div
              className={cn(
                "text-xs p-2 rounded mb-3",
                statusVariants({
                  urgency: hotel.availability.urgency as "high" | "medium" | "low",
                })
              )}
            >
              {`Only ${hotel.availability.roomsLeft ?? 0} room${
                (hotel.availability.roomsLeft ?? 0) > 1 ? "s" : ""
              } left!`}
            </div>
          )}

          {/* Pricing */}
          <div className="mt-auto">
            <div className="flex items-center justify-between mb-3">
              <div>
                {hotel.pricing.deals && (
                  <div className="text-xs text-muted-foreground line-through">
                    ${hotel.pricing.deals.originalPrice}/night
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <span className="text-xl font-bold">
                    {formatCurrency(hotel.pricing.pricePerNight)}
                  </span>
                  <PriceHistoryIcon trend={hotel.pricing.priceHistory} />
                </div>
                <div className="text-xs text-muted-foreground">per night</div>
                <div className="text-sm font-medium">
                  {formatCurrency(hotel.pricing.totalPrice)} total
                </div>
              </div>
            </div>

            {/* AI Recommendation */}
            {hotel.ai.recommendation >= 7 && (
              <div className="mb-3 p-2 bg-purple-50 rounded text-xs">
                <div className="flex items-center gap-1 font-medium text-purple-800">
                  <ZapIcon className="h-3 w-3" />
                  AI Recommendation: {hotel.ai.recommendation}/10
                </div>
                <div className="text-purple-600 mt-1">{hotel.ai.reason}</div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="space-y-2">
              <Button
                onClick={onSelect}
                disabled={isPending || isOptimisticSelecting}
                className="w-full"
              >
                {isOptimisticSelecting ? "Selecting..." : "View Details"}
              </Button>

              {hotel.availability.flexible && (
                <Button variant="outline" size="sm" className="w-full text-xs">
                  <CalendarIcon className="h-3 w-3 mr-1" />
                  Free Cancellation
                </Button>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
