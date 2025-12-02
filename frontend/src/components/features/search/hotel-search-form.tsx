/**
 * @fileoverview Hotel search form component for searching hotels.
 */
"use client";

import {
  BedIcon,
  Building2Icon,
  CalendarIcon,
  CarIcon,
  CoffeeIcon,
  DumbbellIcon,
  Loader2Icon,
  MapPinIcon,
  SearchIcon,
  SparklesIcon,
  StarIcon,
  TrendingUpIcon,
  UsersIcon,
  UtensilsIcon,
  WavesIcon,
  WifiIcon,
  WindIcon,
} from "lucide-react";
import { useId, useOptimistic, useState, useTransition } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";
import { cn } from "@/lib/utils";

// React 19 optimistic update types for hotel search
export interface ModernHotelSearchParams {
  location: string;
  checkIn: string;
  checkOut: string;
  rooms: number;
  adults: number;
  children: number;
  rating: number;
  priceRange: { min: number; max: number };
  amenities: string[];
}

interface LocationSuggestion {
  id: string;
  name: string;
  type: "city" | "hotel" | "landmark";
  country: string;
  deals?: number;
}

interface HotelSearchFormProps {
  onSearch: (params: ModernHotelSearchParams) => Promise<void>;
  suggestions?: LocationSuggestion[];
  className?: string;
  showRecommendations?: boolean;
}

const Amenities = [
  { icon: WifiIcon, id: "wifi", label: "Free WiFi" },
  { icon: CoffeeIcon, id: "breakfast", label: "Free Breakfast" },
  { icon: CarIcon, id: "parking", label: "Free Parking" },
  { icon: WavesIcon, id: "pool", label: "Swimming Pool" },
  { icon: DumbbellIcon, id: "gym", label: "Fitness Center" },
  { icon: UtensilsIcon, id: "restaurant", label: "Restaurant" },
  { icon: SparklesIcon, id: "spa", label: "Spa" },
  { icon: WindIcon, id: "aircon", label: "Air Conditioning" },
];

export function HotelSearchForm({
  onSearch,
  suggestions: _suggestions = [],
  className,
  showRecommendations = true,
}: HotelSearchFormProps) {
  const [isPending, startTransition] = useTransition();
  const locationId = useId();
  const checkInId = useId();
  const checkOutId = useId();
  const roomsId = useId();
  const adultsId = useId();
  const childrenId = useId();

  // Form state with React 19 patterns
  const [searchParams, setSearchParams] = useState<ModernHotelSearchParams>({
    adults: 2,
    amenities: [],
    checkIn: "",
    checkOut: "",
    children: 0,
    location: "",
    priceRange: { max: 1000, min: 0 },
    rating: 0,
    rooms: 1,
  });

  // Error state for user-facing error messages
  const [searchError, setSearchError] = useState<string | null>(null);

  // Optimistic search state
  const [optimisticSearching, setOptimisticSearching] = useOptimistic(
    false,
    (_state, isSearching: boolean) => isSearching
  );

  // Mock data for demo - would come from backend
  const trendingDestinations = [
    { deals: 234, name: "Paris", type: "city" as const },
    { deals: 156, name: "Tokyo", type: "city" as const },
    { deals: 298, name: "New York", type: "city" as const },
    { deals: 187, name: "London", type: "city" as const },
  ];

  const allInclusiveDeals = {
    avgSavings: "$127/night",
    description: "All-Inclusive Era trending",
    savings: "35%",
  };

  const handleInputChange = <K extends keyof ModernHotelSearchParams>(
    field: K,
    value: ModernHotelSearchParams[K]
  ) => {
    setSearchParams((prev) => ({ ...prev, [field]: value }));
  };

  const handleAmenityToggle = (amenityId: string) => {
    setSearchParams((prev) => ({
      ...prev,
      amenities: prev.amenities.includes(amenityId)
        ? prev.amenities.filter((id) => id !== amenityId)
        : [...prev.amenities, amenityId],
    }));
  };

  const handleQuickLocation = (location: string) => {
    setSearchParams((prev) => ({ ...prev, location }));
  };

  const handleSearch = () => {
    startTransition(async () => {
      setOptimisticSearching(true);
      setSearchError(null); // Clear previous errors
      try {
        await onSearch(searchParams);
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : "Failed to search hotels";
        setSearchError(errorMessage);
        recordClientErrorOnActiveSpan(
          error instanceof Error ? error : new Error(String(error)),
          { action: "handleSearch", context: "HotelSearchForm" }
        );
      } finally {
        setOptimisticSearching(false);
      }
    });
  };

  const calculateNights = () => {
    if (!searchParams.checkIn || !searchParams.checkOut) return 0;
    const checkIn = new Date(searchParams.checkIn);
    const checkOut = new Date(searchParams.checkOut);
    const diffTime = checkOut.getTime() - checkIn.getTime();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  };

  return (
    <Card className={cn("w-full max-w-4xl mx-auto", className)}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
              <Building2Icon className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <CardTitle className="text-xl">Find Hotels</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                Discover perfect accommodations for your stay
              </p>
            </div>
          </div>

          {showRecommendations && (
            <div className="hidden md:flex items-center gap-2">
              <Badge
                variant="secondary"
                className="bg-orange-50 text-orange-700 border-orange-200"
              >
                <TrendingUpIcon className="h-3 w-3 mr-1" />
                {allInclusiveDeals.description}
              </Badge>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Location Search */}
        <div className="space-y-2">
          <Label htmlFor={locationId} className="text-sm font-medium">
            Destination
          </Label>
          <div className="relative">
            <MapPinIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              id={locationId}
              placeholder="City, hotel name, or landmark"
              value={searchParams.location}
              onChange={(e) => handleInputChange("location", e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        {/* Dates Section */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor={checkInId} className="text-sm font-medium">
              Check-in
            </Label>
            <div className="relative">
              <CalendarIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id={checkInId}
                type="date"
                value={searchParams.checkIn}
                onChange={(e) => handleInputChange("checkIn", e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor={checkOutId} className="text-sm font-medium">
              Check-out
            </Label>
            <div className="relative">
              <CalendarIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id={checkOutId}
                type="date"
                value={searchParams.checkOut}
                onChange={(e) => handleInputChange("checkOut", e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {calculateNights() > 0 && (
            <div className="space-y-2">
              <Label className="text-sm font-medium">Duration</Label>
              <div className="flex items-center h-10 px-3 border rounded-md bg-muted">
                <BedIcon className="h-4 w-4 mr-2 text-muted-foreground" />
                <span className="text-sm font-medium">
                  {calculateNights()} {calculateNights() === 1 ? "night" : "nights"}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Guests and Rooms */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor={roomsId} className="text-sm font-medium">
              Rooms
            </Label>
            <Select
              value={searchParams.rooms.toString()}
              onValueChange={(value) =>
                handleInputChange("rooms", Number.parseInt(value, 10))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[1, 2, 3, 4, 5].map((num) => (
                  <SelectItem key={num} value={num.toString()}>
                    {num} {num === 1 ? "Room" : "Rooms"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor={adultsId} className="text-sm font-medium">
              Adults
            </Label>
            <div className="relative">
              <UsersIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Select
                value={searchParams.adults.toString()}
                onValueChange={(value) =>
                  handleInputChange("adults", Number.parseInt(value, 10))
                }
              >
                <SelectTrigger className="pl-10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[1, 2, 3, 4, 5, 6].map((num) => (
                    <SelectItem key={num} value={num.toString()}>
                      {num} {num === 1 ? "Adult" : "Adults"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor={childrenId} className="text-sm font-medium">
              Children
            </Label>
            <Select
              value={searchParams.children.toString()}
              onValueChange={(value) =>
                handleInputChange("children", Number.parseInt(value, 10))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {[0, 1, 2, 3, 4].map((num) => (
                  <SelectItem key={num} value={num.toString()}>
                    {num === 0
                      ? "No Children"
                      : `${num} ${num === 1 ? "Child" : "Children"}`}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Star Rating */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Minimum Star Rating</Label>
          <div className="flex gap-2">
            {[0, 1, 2, 3, 4, 5].map((rating) => (
              <Button
                key={rating}
                variant={searchParams.rating === rating ? "default" : "outline"}
                size="sm"
                onClick={() => handleInputChange("rating", rating)}
                className="flex items-center gap-1"
              >
                {rating === 0 ? (
                  "Any"
                ) : (
                  <>
                    {rating}{" "}
                    <StarIcon
                      className={cn(
                        "h-3 w-3",
                        searchParams.rating >= rating && "fill-current"
                      )}
                    />
                  </>
                )}
              </Button>
            ))}
          </div>
        </div>

        {/* Amenities */}
        <div className="space-y-3">
          <Label className="text-sm font-medium">Popular Amenities</Label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {Amenities.map((amenity) => {
              const Icon = amenity.icon;
              const isSelected = searchParams.amenities.includes(amenity.id);
              return (
                <Button
                  key={amenity.id}
                  variant={isSelected ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleAmenityToggle(amenity.id)}
                  className="h-auto py-3 px-3 flex flex-col items-center gap-1"
                >
                  <Icon className="h-4 w-4" />
                  <span className="text-xs text-center">{amenity.label}</span>
                </Button>
              );
            })}
          </div>
        </div>

        {/* Trending Destinations */}
        {showRecommendations && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <TrendingUpIcon className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Trending destinations</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {trendingDestinations.map((dest) => (
                <Button
                  key={dest.name}
                  variant="outline"
                  size="sm"
                  onClick={() => handleQuickLocation(dest.name)}
                  className="h-auto py-2 px-3 flex flex-col items-start"
                >
                  <span className="font-medium">{dest.name}</span>
                  <span className="text-xs text-blue-600">{dest.deals} hotels</span>
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* All-Inclusive Preview */}
        {showRecommendations && (
          <>
            <Separator />
            <div className="bg-linear-to-r from-orange-50 to-red-50 p-4 rounded-lg border">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <SparklesIcon className="h-5 w-5 text-orange-600" />
                  <h3 className="font-semibold text-sm">All-Inclusive Hotels</h3>
                  <Badge variant="secondary" className="bg-orange-100 text-orange-700">
                    Save {allInclusiveDeals.savings}
                  </Badge>
                </div>
                <span className="text-xs text-muted-foreground">
                  avg {allInclusiveDeals.avgSavings}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                {allInclusiveDeals.description} - Everything included: meals, drinks,
                activities, and more!
              </p>
            </div>
          </>
        )}

        {/* Error Message */}
        {searchError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2">
            <div className="text-red-600 text-sm flex-1">
              <strong>Search failed:</strong> {searchError}
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSearchError(null)}
              className="h-6 w-6 p-0 text-red-600 hover:text-red-700"
              aria-label="Dismiss error"
            >
              ×
            </Button>
          </div>
        )}

        {/* Search Button */}
        <div className="flex gap-3 pt-2">
          <Button
            onClick={handleSearch}
            disabled={
              isPending ||
              optimisticSearching ||
              !searchParams.location ||
              !searchParams.checkIn ||
              !searchParams.checkOut
            }
            className="flex-1 bg-green-600 hover:bg-green-700 text-white"
            size="lg"
          >
            {isPending || optimisticSearching ? (
              <>
                <Loader2Icon className="h-4 w-4 mr-2 animate-spin" />
                Searching hotels...
              </>
            ) : (
              <>
                <SearchIcon className="h-4 w-4 mr-2" />
                Search Hotels
              </>
            )}
          </Button>
        </div>

        {/* Progress indicator for optimistic updates */}
        {(isPending || optimisticSearching) && (
          <div className="space-y-2">
            <Progress value={75} className="h-2" />
            <p className="text-xs text-muted-foreground text-center">
              Searching 1M+ properties worldwide...
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
