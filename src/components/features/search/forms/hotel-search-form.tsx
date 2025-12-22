/**
 * @fileoverview Hotel search form component for searching hotels.
 */

"use client";

import {
  type HotelSearchFormData,
  hotelSearchFormSchema,
  type SearchAccommodationParams,
  searchAccommodationParamsSchema,
} from "@schemas/search";
import {
  BedIcon,
  Building2Icon,
  CalendarIcon,
  CarIcon,
  CoffeeIcon,
  DumbbellIcon,
  MapPinIcon,
  SparklesIcon,
  StarIcon,
  TrendingUpIcon,
  UsersIcon,
  UtensilsIcon,
  WavesIcon,
  WifiIcon,
  WindIcon,
} from "lucide-react";
import { useId, useMemo } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { useSearchHistoryStore } from "@/stores/search-history";
import { type QuickSelectItem, SearchFormShell } from "../common/search-form-shell";
import { useSearchForm } from "../common/use-search-form";

export type HotelSearchParams = HotelSearchFormData;

/** Location suggestion interface. */
interface LocationSuggestion {
  id: string;
  name: string;
  type: "city" | "hotel" | "landmark";
  country: string;
  deals?: number;
}

/** Hotel search form props. */
interface HotelSearchFormProps {
  onSearch: (params: HotelSearchParams) => Promise<void>;
  suggestions?: LocationSuggestion[];
  className?: string;
  showRecommendations?: boolean;
}

/** Amenities array. */
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

const DEFAULT_PRICE_RANGE = { max: 1000, min: 0 } as const;

const TRENDING_DESTINATIONS: Array<{ name: string; deals: number }> = [
  { deals: 234, name: "Paris" },
  { deals: 156, name: "Tokyo" },
  { deals: 298, name: "New York" },
  { deals: 187, name: "London" },
];

/** Hotel search form component. */
export function HotelSearchForm({
  onSearch,
  suggestions: _suggestions = [],
  className,
  showRecommendations = true,
}: HotelSearchFormProps) {
  const form = useSearchForm(
    hotelSearchFormSchema,
    {
      adults: 2,
      amenities: [],
      checkIn: "",
      checkOut: "",
      children: 0,
      location: "",
      priceRange: DEFAULT_PRICE_RANGE,
      rating: 0,
      rooms: 1,
    },
    {}
  );

  const locationId = useId();
  const checkInId = useId();
  const checkOutId = useId();
  const roomsId = useId();
  const adultsId = useId();
  const childrenId = useId();

  const calculateNights = () => {
    const checkIn = form.getValues("checkIn");
    const checkOut = form.getValues("checkOut");
    if (!checkIn || !checkOut) return 0;
    const checkInDate = new Date(checkIn);
    const checkOutDate = new Date(checkOut);
    const diffTime = checkOutDate.getTime() - checkInDate.getTime();
    const nights = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    if (!Number.isFinite(nights) || nights <= 0) {
      return 0;
    }
    return nights;
  };

  const nights = calculateNights();
  const values = form.watch();

  const handleAmenityToggle = (amenityId: string) => {
    const current = form.getValues("amenities");
    const next = current.includes(amenityId)
      ? current.filter((id) => id !== amenityId)
      : [...current, amenityId];
    form.setValue("amenities", next, { shouldDirty: true, shouldValidate: true });
  };

  const popularItems: QuickSelectItem<HotelSearchFormData>[] | undefined =
    useMemo(() => {
      if (!showRecommendations) return undefined;
      return TRENDING_DESTINATIONS.map((dest) => ({
        description: `${dest.deals} hotels`,
        id: dest.name,
        label: dest.name,
        params: { location: dest.name },
      }));
    }, [showRecommendations]);

  const recentSearchesByType = useSearchHistoryStore(
    (state) => state.recentSearchesByType.accommodation
  );
  const recentSearches = useMemo(
    () => recentSearchesByType.slice(0, 4),
    [recentSearchesByType]
  );
  const recentItems: QuickSelectItem<HotelSearchFormData>[] = useMemo(() => {
    return recentSearches.flatMap((search) => {
      const parsed = searchAccommodationParamsSchema.safeParse(search.params);
      if (!parsed.success) return [];

      const params: SearchAccommodationParams = parsed.data;
      const destination = params.destination ?? "Destination";
      const dateLabel =
        params.checkIn && params.checkOut
          ? `${params.checkIn} → ${params.checkOut}`
          : undefined;

      const mapped: Partial<HotelSearchFormData> = {
        adults: params.adults ?? undefined,
        amenities: params.amenities ?? undefined,
        checkIn: params.checkIn ?? undefined,
        checkOut: params.checkOut ?? undefined,
        children: params.children ?? undefined,
        currency: params.currency ?? undefined,
        location: params.destination ?? undefined,
        rooms: params.rooms ?? undefined,
      };

      if (params.minRating !== undefined) {
        mapped.rating = Math.max(0, Math.min(5, Math.round(params.minRating)));
      }

      if (
        params.priceRange?.min !== undefined ||
        params.priceRange?.max !== undefined
      ) {
        mapped.priceRange = {
          max: params.priceRange?.max ?? DEFAULT_PRICE_RANGE.max,
          min: params.priceRange?.min ?? DEFAULT_PRICE_RANGE.min,
        };
      }

      const item: QuickSelectItem<HotelSearchFormData> = {
        id: search.id,
        label: destination,
        params: mapped,
        ...(dateLabel ? { description: dateLabel } : {}),
      };

      return [item];
    });
  }, [recentSearches]);

  return (
    <Card className={cn("w-full max-w-4xl mx-auto", className)}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
              <Building2Icon aria-hidden className="h-5 w-5 text-green-600" />
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
                <TrendingUpIcon aria-hidden className="h-3 w-3 mr-1" />
                All-Inclusive Era trending
              </Badge>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        <SearchFormShell
          form={form}
          onSubmit={onSearch}
          telemetrySpanName="search.hotel.form.submit"
          telemetryAttributes={{ searchType: "hotel" }}
          telemetryErrorMetadata={{
            action: "handleSearch",
            context: "HotelSearchForm",
          }}
          submitLabel="Search Hotels"
          loadingLabel="Searching hotels..."
          disableSubmitWhenInvalid
          className="space-y-6"
          popularItems={popularItems}
          popularLabel="Trending destinations"
          recentItems={recentItems}
          footer={
            showRecommendations
              ? () => (
                  <>
                    <Separator />
                    <div className="bg-linear-to-r from-orange-50 to-red-50 p-4 rounded-lg border">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <SparklesIcon
                            aria-hidden
                            className="h-5 w-5 text-orange-600"
                          />
                          <h3 className="font-semibold text-sm">
                            All-Inclusive Hotels
                          </h3>
                          <Badge
                            variant="secondary"
                            className="bg-orange-100 text-orange-700"
                          >
                            Save 35%
                          </Badge>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          avg $127/night
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Everything included: meals, drinks, activities, and more.
                      </p>
                    </div>
                  </>
                )
              : undefined
          }
        >
          {(form, _state) => (
            <>
              <div className="space-y-2">
                <Label htmlFor={locationId} className="text-sm font-medium">
                  Destination
                </Label>
                <div className="relative">
                  <MapPinIcon
                    aria-hidden
                    className="absolute left-3 top-3 h-4 w-4 text-muted-foreground"
                  />
                  <Input
                    id={locationId}
                    placeholder="City, hotel name, or landmark"
                    {...form.register("location")}
                    className="pl-10"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor={checkInId} className="text-sm font-medium">
                    Check-in
                  </Label>
                  <div className="relative">
                    <CalendarIcon
                      aria-hidden
                      className="absolute left-3 top-3 h-4 w-4 text-muted-foreground"
                    />
                    <Input
                      id={checkInId}
                      type="date"
                      {...form.register("checkIn")}
                      className="pl-10"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor={checkOutId} className="text-sm font-medium">
                    Check-out
                  </Label>
                  <div className="relative">
                    <CalendarIcon
                      aria-hidden
                      className="absolute left-3 top-3 h-4 w-4 text-muted-foreground"
                    />
                    <Input
                      id={checkOutId}
                      type="date"
                      {...form.register("checkOut")}
                      className="pl-10"
                    />
                  </div>
                </div>

                {nights > 0 && (
                  <div className="space-y-2">
                    <Label className="text-sm font-medium">Duration</Label>
                    <div className="flex items-center h-10 px-3 border rounded-md bg-muted">
                      <BedIcon
                        aria-hidden
                        className="h-4 w-4 mr-2 text-muted-foreground"
                      />
                      <span className="text-sm font-medium">
                        {nights} {nights === 1 ? "night" : "nights"}
                      </span>
                    </div>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor={roomsId} className="text-sm font-medium">
                    Rooms
                  </Label>
                  <Select
                    value={values.rooms.toString()}
                    onValueChange={(value) =>
                      form.setValue("rooms", Number.parseInt(value, 10), {
                        shouldDirty: true,
                        shouldValidate: true,
                      })
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
                    <UsersIcon
                      aria-hidden
                      className="absolute left-3 top-3 h-4 w-4 text-muted-foreground"
                    />
                    <Select
                      value={values.adults.toString()}
                      onValueChange={(value) =>
                        form.setValue("adults", Number.parseInt(value, 10), {
                          shouldDirty: true,
                          shouldValidate: true,
                        })
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
                    value={values.children.toString()}
                    onValueChange={(value) =>
                      form.setValue("children", Number.parseInt(value, 10), {
                        shouldDirty: true,
                        shouldValidate: true,
                      })
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

              <div className="space-y-3">
                <Label className="text-sm font-medium">Minimum Star Rating</Label>
                <div className="flex gap-2">
                  {[0, 1, 2, 3, 4, 5].map((rating) => (
                    <Button
                      key={rating}
                      variant={values.rating === rating ? "default" : "outline"}
                      size="sm"
                      onClick={() =>
                        form.setValue("rating", rating, {
                          shouldDirty: true,
                          shouldValidate: true,
                        })
                      }
                      className="flex items-center gap-1"
                      type="button"
                    >
                      {rating === 0 ? (
                        "Any"
                      ) : (
                        <>
                          {rating}{" "}
                          <StarIcon
                            aria-hidden
                            className={cn(
                              "h-3 w-3",
                              values.rating >= rating && "fill-current"
                            )}
                          />
                        </>
                      )}
                    </Button>
                  ))}
                </div>
              </div>

              <div className="space-y-3">
                <Label className="text-sm font-medium">Popular Amenities</Label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {Amenities.map((amenity) => {
                    const Icon = amenity.icon;
                    const isSelected = values.amenities.includes(amenity.id);
                    return (
                      <Button
                        key={amenity.id}
                        variant={isSelected ? "default" : "outline"}
                        size="sm"
                        onClick={() => handleAmenityToggle(amenity.id)}
                        className="h-auto py-3 px-3 flex flex-col items-center gap-1"
                        type="button"
                      >
                        <Icon aria-hidden className="h-4 w-4" />
                        <span className="text-xs text-center">{amenity.label}</span>
                      </Button>
                    );
                  })}
                </div>
              </div>
            </>
          )}
        </SearchFormShell>
      </CardContent>
    </Card>
  );
}
