/**
 * @fileoverview Hotel results grid with filters, badges, and sorting controls.
 */

"use client";

import {
  ArrowUpDownIcon,
  Building2Icon,
  CalendarIcon,
  FilterIcon,
  Grid3X3Icon,
  HeartIcon,
  ImageIcon,
  ListIcon,
  MapIcon,
  MapPinIcon,
  RefreshCwIcon,
  ShieldIcon,
  SparklesIcon,
  StarIcon,
  TrendingUpIcon,
  ZapIcon,
} from "lucide-react";
import Image from "next/image";
import { useOptimistic, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";
import { cn } from "@/lib/utils";
import { GetAmenityIcon } from "./cards/amenities";
import { RatingStars } from "./cards/rating-stars";
import { formatCurrency } from "./common/format";

// Hotel result type
export interface HotelResult {
  id: string;
  name: string;
  brand?: string;
  category: "hotel" | "resort" | "apartment" | "villa" | "boutique";
  starRating: number;
  userRating: number;
  reviewCount: number;
  location: {
    address: string;
    city: string;
    district: string;
    landmarks: string[];
    walkScore?: number;
  };
  images: {
    main: string;
    gallery: string[];
    count: number;
  };
  pricing: {
    basePrice: number;
    totalPrice: number;
    pricePerNight: number;
    currency: string;
    taxes: number;
    deals?: {
      type: "early_bird" | "last_minute" | "extended_stay" | "all_inclusive";
      description: string;
      savings: number;
      originalPrice: number;
    };
    priceHistory: "rising" | "falling" | "stable";
  };
  amenities: {
    essential: string[];
    premium: string[];
    unique: string[];
  };
  sustainability: {
    certified: boolean;
    score: number; // 1-10
    practices: string[];
  };
  allInclusive?: {
    available: boolean;
    inclusions: string[];
    tier: "basic" | "premium" | "luxury";
  };
  availability: {
    roomsLeft: number;
    urgency: "low" | "medium" | "high";
    flexible: boolean;
  };
  guestExperience: {
    highlights: string[];
    recentMentions: string[];
    vibe: "luxury" | "business" | "family" | "romantic" | "adventure";
  };
  ai: {
    recommendation: number; // 1-10
    reason: string;
    personalizedTags: string[];
  };
}

/** Hotel results props */
interface HotelResultsProps {
  results: HotelResult[];
  loading?: boolean;
  onSelect: (hotel: HotelResult) => Promise<void>;
  onSaveToWishlist: (hotelId: string) => void;
  className?: string;
  showMap?: boolean;
}

/** Hotel results component */
export function HotelResults({
  results,
  loading = false,
  onSelect,
  onSaveToWishlist,
  className,
  showMap = true,
}: HotelResultsProps) {
  const [isPending, startTransition] = useTransition();
  const [viewMode, setViewMode] = useState<"list" | "grid" | "map">("list");
  const [savedHotels, setSavedHotels] = useState<Set<string>>(new Set());
  const [sortBy, _setSortBy] = useState<"price" | "rating" | "distance" | "ai">("ai");
  const [_sortDirection, _setSortDirection] = useState<"asc" | "desc">("desc");

  // Optimistic selection state
  const [optimisticSelecting, setOptimisticSelecting] = useOptimistic(
    "",
    (_state, hotelId: string) => hotelId
  );

  /** Handle hotel selection */
  const handleHotelSelect = (hotel: HotelResult) => {
    startTransition(async () => {
      setOptimisticSelecting(hotel.id);
      try {
        await onSelect(hotel);
      } catch (error) {
        recordClientErrorOnActiveSpan(
          error instanceof Error ? error : new Error(String(error)),
          {
            action: "handleHotelSelect",
            context: "HotelResults",
            hotelId: hotel.id,
          }
        );
      } finally {
        setOptimisticSelecting("");
      }
    });
  };

  /** Toggle hotel for comparison */
  const toggleWishlist = (hotelId: string) => {
    setSavedHotels((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(hotelId)) {
        newSet.delete(hotelId);
      } else {
        newSet.add(hotelId);
      }
      onSaveToWishlist(hotelId);
      return newSet;
    });
  };

  /** Get urgency color */
  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case "high":
        return "text-red-600 bg-red-50 border-red-200";
      case "medium":
        return "text-orange-600 bg-orange-50 border-orange-200";
      default:
        return "text-green-600 bg-green-50 border-green-200";
    }
  };

  /** Get price history icon */
  const getPriceHistoryIcon = (trend: string) => {
    if (trend === "falling")
      return <TrendingUpIcon className="h-3 w-3 text-green-500 rotate-180" />;
    if (trend === "rising") return <TrendingUpIcon className="h-3 w-3 text-red-500" />;
    return null;
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={`hotel-skeleton-${i}`} className="p-6">
            <div className="animate-pulse flex gap-4">
              <div className="w-48 h-32 bg-muted rounded-lg" />
              <div className="flex-1 space-y-4">
                <div className="space-y-2">
                  <div className="h-4 bg-muted rounded w-3/4" />
                  <div className="h-3 bg-muted rounded w-1/2" />
                </div>
                <div className="h-2 bg-muted rounded" />
                <div className="flex gap-2">
                  <div className="h-6 bg-muted rounded w-16" />
                  <div className="h-6 bg-muted rounded w-16" />
                </div>
              </div>
              <div className="w-32 space-y-2">
                <div className="h-6 bg-muted rounded" />
                <div className="h-8 bg-muted rounded" />
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <Card className="p-12 text-center">
        <Building2Icon className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="text-lg font-semibold mb-2">No hotels found</h3>
        <p className="text-muted-foreground mb-4">
          Try adjusting your search criteria or dates
        </p>
        <Button variant="outline">
          <RefreshCwIcon className="h-4 w-4 mr-2" />
          Modify Search
        </Button>
      </Card>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Search Controls */}
      <Card className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium">{results.length} hotels found</span>
            <Separator orientation="vertical" className="h-4" />
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm">
                <FilterIcon className="h-4 w-4 mr-2" />
                Filters
              </Button>
              <Button variant="ghost" size="sm">
                <ArrowUpDownIcon className="h-4 w-4 mr-2" />
                Sort: {sortBy === "ai" ? "AI Recommended" : sortBy}
              </Button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant={viewMode === "list" ? "default" : "outline"}
              size="sm"
              onClick={() => setViewMode("list")}
            >
              <ListIcon className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === "grid" ? "default" : "outline"}
              size="sm"
              onClick={() => setViewMode("grid")}
            >
              <Grid3X3Icon className="h-4 w-4" />
            </Button>
            {showMap && (
              <Button
                variant={viewMode === "map" ? "default" : "outline"}
                size="sm"
                onClick={() => setViewMode("map")}
              >
                <MapIcon className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* Hotel Results */}
      <div
        className={cn(
          viewMode === "grid"
            ? "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
            : "space-y-4"
        )}
      >
        {results.map((hotel) => (
          <Card
            key={hotel.id}
            className={cn(
              "relative transition-all duration-200 hover:shadow-lg",
              optimisticSelecting === hotel.id && "opacity-75",
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
              onClick={() => toggleWishlist(hotel.id)}
              aria-label={
                savedHotels.has(hotel.id) ? "Remove from wishlist" : "Save to wishlist"
              }
            >
              <HeartIcon
                className={cn(
                  "h-4 w-4",
                  savedHotels.has(hotel.id)
                    ? "fill-red-500 text-red-500"
                    : "text-gray-600"
                )}
              />
            </Button>

            <CardContent
              className={cn(
                "p-0",
                viewMode === "list" ? "flex" : "flex flex-col h-full"
              )}
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
                  <Badge
                    variant="secondary"
                    className="absolute bottom-2 right-2 text-xs"
                  >
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
                className={cn(
                  "p-4 flex flex-col",
                  viewMode === "list" ? "flex-1" : "flex-1"
                )}
              >
                {/* Header */}
                <div className="mb-3">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-lg leading-tight mb-1 truncate">
                        {hotel.name}
                      </h3>
                      <div className="flex items-center gap-2 mb-2">
                        <RatingStars value={hotel.starRating} />
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
                      {hotel.location.district}, {hotel.location.city}
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
                      getUrgencyColor(hotel.availability.urgency)
                    )}
                  >
                    Only {hotel.availability.roomsLeft} room
                    {hotel.availability.roomsLeft > 1 ? "s" : ""} left!
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
                        {getPriceHistoryIcon(hotel.pricing.priceHistory)}
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
                      onClick={() => handleHotelSelect(hotel)}
                      disabled={isPending || optimisticSelecting === hotel.id}
                      className="w-full"
                    >
                      {optimisticSelecting === hotel.id
                        ? "Selecting..."
                        : "View Details"}
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
        ))}
      </div>

      {/* Load More */}
      {results.length > 0 && (
        <Card className="p-4 text-center">
          <Button variant="outline">Load More Hotels</Button>
        </Card>
      )}
    </div>
  );
}
