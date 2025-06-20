"use client";

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
import { cn } from "@/lib/utils";
import {
  Bed,
  Building2,
  Calendar,
  Car,
  Coffee,
  Dumbbell,
  Loader2,
  MapPin,
  Search,
  Sparkles,
  Star,
  TrendingUp,
  Users,
  Utensils,
  Wifi,
} from "lucide-react";
import { useOptimistic, useState, useTransition } from "react";

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

const AMENITIES = [
  { id: "wifi", label: "Free WiFi", icon: Wifi },
  { id: "breakfast", label: "Free Breakfast", icon: Coffee },
  { id: "parking", label: "Free Parking", icon: Car },
  { id: "pool", label: "Swimming Pool", icon: Building2 },
  { id: "gym", label: "Fitness Center", icon: Dumbbell },
  { id: "restaurant", label: "Restaurant", icon: Utensils },
  { id: "spa", label: "Spa", icon: Sparkles },
  { id: "aircon", label: "Air Conditioning", icon: Building2 },
];

export function HotelSearchForm({
  onSearch,
  suggestions = [],
  className,
  showRecommendations = true,
}: HotelSearchFormProps) {
  const [isPending, startTransition] = useTransition();

  // Form state with React 19 patterns
  const [searchParams, setSearchParams] = useState<ModernHotelSearchParams>({
    location: "",
    checkIn: "",
    checkOut: "",
    rooms: 1,
    adults: 2,
    children: 0,
    rating: 0,
    priceRange: { min: 0, max: 1000 },
    amenities: [],
  });

  // Optimistic search state
  const [optimisticSearching, setOptimisticSearching] = useOptimistic(
    false,
    (_state, isSearching: boolean) => isSearching
  );

  // Mock data for demo - would come from backend
  const trendingDestinations = [
    { name: "Paris", deals: 234, type: "city" as const },
    { name: "Tokyo", deals: 156, type: "city" as const },
    { name: "New York", deals: 298, type: "city" as const },
    { name: "London", deals: 187, type: "city" as const },
  ];

  const allInclusiveDeals = {
    savings: "35%",
    description: "All-Inclusive Era trending",
    avgSavings: "$127/night",
  };

  const handleInputChange = (field: keyof ModernHotelSearchParams, value: any) => {
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
      try {
        await onSearch(searchParams);
      } catch (error) {
        console.error("Hotel search failed:", error);
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
              <Building2 className="h-5 w-5 text-green-600" />
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
                <TrendingUp className="h-3 w-3 mr-1" />
                {allInclusiveDeals.description}
              </Badge>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Location Search */}
        <div className="space-y-2">
          <Label htmlFor="location" className="text-sm font-medium">
            Destination
          </Label>
          <div className="relative">
            <MapPin className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <Input
              id="location"
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
            <Label htmlFor="checkIn" className="text-sm font-medium">
              Check-in
            </Label>
            <div className="relative">
              <Calendar className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="checkIn"
                type="date"
                value={searchParams.checkIn}
                onChange={(e) => handleInputChange("checkIn", e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="checkOut" className="text-sm font-medium">
              Check-out
            </Label>
            <div className="relative">
              <Calendar className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                id="checkOut"
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
                <Bed className="h-4 w-4 mr-2 text-muted-foreground" />
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
            <Label htmlFor="rooms" className="text-sm font-medium">
              Rooms
            </Label>
            <Select
              value={searchParams.rooms.toString()}
              onValueChange={(value) =>
                handleInputChange("rooms", Number.parseInt(value))
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
            <Label htmlFor="adults" className="text-sm font-medium">
              Adults
            </Label>
            <div className="relative">
              <Users className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Select
                value={searchParams.adults.toString()}
                onValueChange={(value) =>
                  handleInputChange("adults", Number.parseInt(value))
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
            <Label htmlFor="children" className="text-sm font-medium">
              Children
            </Label>
            <Select
              value={searchParams.children.toString()}
              onValueChange={(value) =>
                handleInputChange("children", Number.parseInt(value))
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
                    <Star
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
            {AMENITIES.map((amenity) => {
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
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
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
            <div className="bg-gradient-to-r from-orange-50 to-red-50 p-4 rounded-lg border">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-orange-600" />
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
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Searching hotels...
              </>
            ) : (
              <>
                <Search className="h-4 w-4 mr-2" />
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
