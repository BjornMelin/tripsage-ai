/**
 * @fileoverview Client-side hotel search experience (renders within RSC shell).
 */

"use client";

import type { HotelResult, SearchAccommodationParams } from "@schemas/search";
import {
  AlertCircleIcon,
  Building2Icon,
  FilterIcon,
  LightbulbIcon,
  MapPinIcon,
  SearchIcon,
  SortAscIcon,
  StarIcon,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { buildHotelApiPayload } from "@/components/features/search/filters/api-payload";
import { FilterPanel } from "@/components/features/search/filters/filter-panel";
import { HotelSearchForm } from "@/components/features/search/forms/hotel-search-form";
import { HotelResults } from "@/components/features/search/results/hotel-results";
import { SearchLayout } from "@/components/layouts/search-layout";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { HotelSkeleton } from "@/components/ui/travel-skeletons";
import { useToast } from "@/components/ui/use-toast";
import { useSearchOrchestration } from "@/hooks/search/use-search-orchestration";
import { getErrorMessage } from "@/lib/api/error-types";
import { useSearchFiltersStore } from "@/stores/search-filters-store";
import { useSearchResultsStore } from "@/stores/search-results-store";

/** Hotel search client component props. */
interface HotelsSearchClientProps {
  onSubmitServer: (
    params: SearchAccommodationParams
  ) => Promise<SearchAccommodationParams>;
}

/** Hotel search client component. */
export default function HotelsSearchClient({
  onSubmitServer,
}: HotelsSearchClientProps) {
  const { initializeSearch, executeSearch, isSearching } = useSearchOrchestration();
  const searchError = useSearchResultsStore((state) => state.error);
  const activeFilters = useSearchFiltersStore((s) => s.activeFilters);
  const { toast } = useToast();
  const [hasSearched, setHasSearched] = useState(false);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const accommodationResults = useSearchResultsStore(
    (state) => state.results.accommodations ?? []
  );

  // Initialize accommodation search type on mount
  useEffect(() => {
    initializeSearch("accommodation");
  }, [initializeSearch]);

  const hotelResults: HotelResult[] = useMemo(
    () =>
      accommodationResults.map((accommodation) => {
        // Extract availability from provider data (roomsLeft, urgency)
        const roomsLeft = accommodation.availability?.roomsLeft;
        const urgency = accommodation.availability?.urgency ?? "medium";
        const flexible =
          accommodation.availability?.flexible ??
          accommodation.policies?.cancellation?.refundable ??
          false;

        // Categorize amenities (essential for core needs, premium for luxury, unique for special)
        const amenityList = accommodation.amenities ?? [];
        const normalizedAmenities = (accommodation.amenities ?? []).map((a) =>
          a.toLowerCase().trim()
        );
        const essentialKeywords = [
          "wifi",
          "breakfast",
          "parking",
          "air conditioning",
          "air-conditioned",
          "a/c",
        ];
        const premiumKeywords = ["spa", "pool", "gym", "fitness", "concierge"];
        const essential = (amenityList || []).filter((_a, idx) =>
          essentialKeywords.some((k) => normalizedAmenities[idx]?.includes(k))
        );
        const premium = (amenityList || []).filter((_a, idx) =>
          premiumKeywords.some((k) => normalizedAmenities[idx]?.includes(k))
        );
        const unique = amenityList.filter(
          (a) => !essential.includes(a) && !premium.includes(a)
        );
        const personalizedTags = [...essential, ...premium, ...unique].slice(0, 3);

        // Derive category from type or default to hotel
        const allowedCategories = [
          "hotel",
          "resort",
          "apartment",
          "villa",
          "boutique",
          "hostel",
        ] as const;
        const category = allowedCategories.includes(
          accommodation.category as (typeof allowedCategories)[number]
        )
          ? (accommodation.category as (typeof allowedCategories)[number])
          : "hotel";

        // Derive vibe from category and amenities heuristics
        let vibe: "luxury" | "business" | "family" | "romantic" | "adventure" =
          "business";
        const amenitiesLower = normalizedAmenities.join(" ");
        if (category === "resort" || amenitiesLower.includes("spa")) {
          vibe = "luxury";
        } else if (
          amenitiesLower.includes("kid") ||
          amenitiesLower.includes("family")
        ) {
          vibe = "family";
        } else if (
          amenitiesLower.includes("hiking") ||
          amenitiesLower.includes("surf") ||
          amenitiesLower.includes("rafting") ||
          amenitiesLower.includes("adventure") ||
          amenitiesLower.includes("outdoor")
        ) {
          vibe = "adventure";
        } else if (category === "boutique") {
          vibe = "romantic";
        }

        // Parse address components
        const addressLines = accommodation.address?.lines ?? [];
        const city = accommodation.address?.cityName ?? accommodation.location ?? "";
        const address =
          addressLines.length > 0
            ? addressLines.join(", ")
            : (accommodation.location ?? "");
        const district =
          (accommodation.address as { district?: string } | undefined)?.district ??
          (accommodation as { district?: string }).district;
        const reviewCount =
          (accommodation as { reviewCount?: number }).reviewCount ?? 0;

        const recommendation = (() => {
          if (typeof accommodation.rating === "number") {
            return Math.max(1, Math.min(10, Math.round(accommodation.rating * 2)));
          }
          return 5;
        })();

        return {
          // AI personalization (populated via separate API call or defaults)
          ai: {
            personalizedTags,
            reason: city
              ? `Great ${category} option in ${city}`
              : `Great ${category} option`,
            recommendation,
          },
          amenities: {
            essential: essential.slice(0, 3),
            premium: premium.slice(0, 3),
            unique: unique.slice(0, 3),
          },
          availability: {
            flexible,
            roomsLeft,
            urgency,
          },
          brand: undefined, // Chain code mapping can be applied via getBrandName(accommodation.chainCode)
          category,
          guestExperience: {
            highlights: [],
            recentMentions: [],
            vibe,
          },
          id: accommodation.id,
          images: {
            count: accommodation.images?.length ?? 0,
            gallery: accommodation.images ?? [],
            main: accommodation.images?.[0] ?? "/globe.svg",
          },
          location: {
            address,
            city,
            coordinates: accommodation.coordinates,
            district,
            landmarks: [],
            walkScore: undefined,
          },
          name: accommodation.name,
          pricing: {
            basePrice: accommodation.pricePerNight,
            currency: accommodation.currency ?? "USD",
            priceHistory: "stable",
            pricePerNight: accommodation.pricePerNight,
            taxes: accommodation.taxes ?? 0,
            taxesEstimated: accommodation.taxes === undefined,
            totalPrice: accommodation.totalPrice,
          },
          reviewCount,
          starRating:
            accommodation.starRating &&
            accommodation.starRating >= 1 &&
            accommodation.starRating <= 5
              ? accommodation.starRating
              : undefined,
          sustainability: {
            certified: false,
            practices: [],
            score: 5,
          },
          userRating: accommodation.rating,
        };
      }),
    [accommodationResults]
  );

  const hasAccommodationResults = hotelResults.length > 0;

  const sortedHotelResults = useMemo(
    () =>
      [...hotelResults].sort((first, second) =>
        sortDirection === "asc"
          ? first.pricing.totalPrice - second.pricing.totalPrice
          : second.pricing.totalPrice - first.pricing.totalPrice
      ),
    [hotelResults, sortDirection]
  );

  // TODO: Implement hotel selection flow - navigate to detail page or open booking modal
  const handleHotelSelect = (hotel: HotelResult) => {
    toast({
      description: `${hotel.name} selected`,
      title: "Hotel selected",
    });
    return Promise.resolve();
  };

  // TODO: Implement wishlist persistence - save to user's wishlist via API and update store
  const handleSaveToWishlist = (hotelId: string) => {
    toast({
      description: `Saved hotel ${hotelId}`,
      title: "Wishlist updated",
    });
  };

  const handleSortClick = () => {
    setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
  };

  /** Scroll to filter panel in sidebar (useful on mobile where sidebar is below content) */
  const handleFilterClick = () => {
    const filterPanel = document.querySelector('[data-testid="filter-panel"]');
    filterPanel?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const handleSearch = async (params: SearchAccommodationParams) => {
    try {
      // Merge form params with active filter payload
      const filterPayload = buildHotelApiPayload(activeFilters);
      const searchWithFilters: SearchAccommodationParams = {
        ...params,
        ...filterPayload,
      };
      const validatedParams = await onSubmitServer(searchWithFilters); // server-side telemetry and validation
      await executeSearch(validatedParams); // client fetch/store update via orchestration
      setHasSearched(true);
    } catch (error) {
      toast({
        description: getErrorMessage(error),
        title: "Search Error",
        variant: "destructive",
      });
    }
  };

  return (
    <SearchLayout>
      <TooltipProvider>
        <div className="grid gap-6 lg:grid-cols-4">
          {/* Main content - 3 columns */}
          <div className="lg:col-span-3 space-y-6">
            {/* Search Form */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Building2Icon className="h-5 w-5" />
                  Find Accommodations
                </CardTitle>
                <CardDescription>
                  Search hotels, resorts, and vacation rentals
                </CardDescription>
              </CardHeader>
              <CardContent>
                <HotelSearchForm onSearch={handleSearch} />
              </CardContent>
            </Card>

            {/* Error State */}
            {searchError && (
              <Alert variant="destructive">
                <AlertCircleIcon className="h-4 w-4" />
                <AlertTitle>Search Error</AlertTitle>
                <AlertDescription>
                  {searchError.message || "An error occurred during search"}
                </AlertDescription>
              </Alert>
            )}

            {/* Loading State */}
            {isSearching && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <SearchIcon className="h-5 w-5 animate-pulse" />
                    Searching for accommodations...
                  </CardTitle>
                  <CardDescription>
                    Please wait while we find the best options for you
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {["sk-1", "sk-2", "sk-3"].map((id) => (
                      <Card key={id} className="overflow-hidden">
                        <HotelSkeleton />
                      </Card>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Results State */}
            {hasSearched && !isSearching && hasAccommodationResults && (
              <div className="space-y-6">
                <div className="flex justify-between items-center flex-wrap gap-4">
                  <h2 className="text-2xl font-semibold flex items-center gap-2">
                    <Building2Icon className="h-6 w-6" />
                    Found accommodations
                  </h2>
                  <div className="flex gap-2">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button onClick={handleSortClick} variant="outline" size="sm">
                          <SortAscIcon className="h-4 w-4 mr-2" />
                          Sort by Price (
                          {sortDirection === "asc" ? "Low→High" : "High→Low"})
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Sort results by total price</TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button onClick={handleFilterClick} variant="outline" size="sm">
                          <FilterIcon className="h-4 w-4 mr-2" />
                          Filter
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Open filters</TooltipContent>
                    </Tooltip>
                  </div>
                </div>

                <HotelResults
                  loading={isSearching}
                  onSaveToWishlist={handleSaveToWishlist}
                  onSelect={handleHotelSelect}
                  results={sortedHotelResults}
                  showMap
                />
              </div>
            )}

            {/* Initial State - Popular Destinations & Tips */}
            {!hasSearched && !isSearching && (
              <>
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <MapPinIcon className="h-5 w-5" />
                      Popular Destinations
                    </CardTitle>
                    <CardDescription>
                      Trending hotel destinations and deals
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {/* TODO: Fetch popular destinations from /api/accommodations/popular-destinations or similar endpoint */}
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                      <PopularDestinationCard
                        destination="New York"
                        priceFrom={199}
                        rating={4.8}
                      />
                      <PopularDestinationCard
                        destination="Paris"
                        priceFrom={229}
                        rating={4.7}
                      />
                      <PopularDestinationCard
                        destination="Tokyo"
                        priceFrom={179}
                        rating={4.9}
                      />
                      <PopularDestinationCard
                        destination="London"
                        priceFrom={249}
                        rating={4.6}
                      />
                      <PopularDestinationCard
                        destination="Barcelona"
                        priceFrom={189}
                        rating={4.8}
                      />
                      <PopularDestinationCard
                        destination="Rome"
                        priceFrom={219}
                        rating={4.7}
                      />
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <LightbulbIcon className="h-5 w-5" />
                      Accommodation Tips
                    </CardTitle>
                    <CardDescription>
                      Tips to help you find the best accommodations
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {/* TODO: Fetch personalized tips from AI service or content management system based on user context */}
                    <div className="space-y-4">
                      <AccommodationTip
                        title="Book directly with hotels for possible benefits"
                        description="While we show you the best deals from all sites, booking directly with hotels can sometimes get you perks like free breakfast, room upgrades, or loyalty points."
                      />
                      <Separator />
                      <AccommodationTip
                        title="Consider location carefully"
                        description="A slightly higher price for a central location can save you time and transportation costs. Use the map view to see where properties are located relative to attractions."
                      />
                      <Separator />
                      <AccommodationTip
                        title="Check cancellation policies"
                        description="For maximum flexibility, filter for properties with free cancellation. This allows you to lock in a good rate while still keeping your options open."
                      />
                      <Separator />
                      <AccommodationTip
                        title="Read recent reviews"
                        description="Look at reviews from the last 3-6 months to get the most accurate picture of the current state of the property. Pay special attention to reviews from travelers similar to you."
                      />
                    </div>
                  </CardContent>
                </Card>
              </>
            )}

            {/* Empty State */}
            {hasSearched &&
              !isSearching &&
              !hasAccommodationResults &&
              !searchError && (
                <Card>
                  <CardContent className="text-center py-12">
                    <div className="flex flex-col items-center gap-4">
                      <div className="rounded-full bg-muted p-4">
                        <SearchIcon className="h-8 w-8 text-muted-foreground" />
                      </div>
                      <div className="space-y-2">
                        <h3 className="text-lg font-semibold">
                          No accommodations found
                        </h3>
                        <p className="text-muted-foreground max-w-md">
                          Try adjusting your search criteria, dates, or destination.
                        </p>
                      </div>
                      <Button variant="outline" onClick={() => setHasSearched(false)}>
                        New Search
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}
          </div>

          {/* Sidebar - 1 column */}
          <div className="space-y-6">
            <FilterPanel />
          </div>
        </div>
      </TooltipProvider>
    </SearchLayout>
  );
}

interface PopularDestinationProps {
  destination: string;
  priceFrom: number;
  rating: number;
}

/**
 * Present a highlighted destination card with pricing and rating metadata.
 */
function PopularDestinationCard({
  destination,
  priceFrom,
  rating,
}: PopularDestinationProps) {
  return (
    <Card className="h-full overflow-hidden transition-colors hover:bg-accent/50 group">
      <div className="h-40 bg-linear-to-br from-primary/10 to-primary/5 flex items-center justify-center relative">
        <Building2Icon className="h-16 w-16 text-primary/30" />
        <div className="absolute top-3 right-3">
          <Badge variant="secondary" className="text-xs flex items-center gap-1">
            <StarIcon className="h-3 w-3 fill-yellow-400 text-yellow-400" />
            {rating}
          </Badge>
        </div>
      </div>
      <CardContent className="p-4">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="font-medium group-hover:text-primary transition-colors">
              {destination}
            </h3>
            <p className="text-xs text-muted-foreground mt-1">Hotels & Resorts</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">from</p>
            <span className="font-semibold text-lg">${priceFrom}</span>
            <p className="text-xs text-muted-foreground">per night</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface AccommodationTipProps {
  title: string;
  description: string;
}

/**
 * Display a single accommodation planning tip.
 */
function AccommodationTip({ title, description }: AccommodationTipProps) {
  return (
    <div className="flex gap-4">
      <div className="shrink-0">
        <div className="rounded-full bg-primary/10 p-2">
          <LightbulbIcon className="h-4 w-4 text-primary" />
        </div>
      </div>
      <div>
        <h3 className="font-medium mb-1">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}
