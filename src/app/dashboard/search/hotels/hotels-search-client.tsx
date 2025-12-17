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
import { useEffect, useMemo, useRef, useState } from "react";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { useCurrencyStore } from "@/stores/currency-store";
import { useSearchFiltersStore } from "@/stores/search-filters-store";
import { useSearchResultsStore } from "@/stores/search-results-store";
import { mapAccommodationToHotelResult } from "./hotel-mapping";

/** Hotel search client component props. */
interface HotelsSearchClientProps {
  onSubmitServer: (
    params: SearchAccommodationParams
  ) => Promise<SearchAccommodationParams>;
}

const POPULAR_DESTINATIONS = [
  { destination: "New York", priceFrom: 199, rating: 4.8 },
  { destination: "Paris", priceFrom: 229, rating: 4.7 },
  { destination: "Tokyo", priceFrom: 179, rating: 4.9 },
  { destination: "London", priceFrom: 249, rating: 4.6 },
  { destination: "Barcelona", priceFrom: 189, rating: 4.8 },
  { destination: "Rome", priceFrom: 219, rating: 4.7 },
] as const;

type PopularDestinationApiResponse = {
  city: string;
  country?: string;
  avgPrice?: string;
  imageUrl?: string;
};

const POPULAR_DESTINATIONS_BY_CITY = new Map(
  POPULAR_DESTINATIONS.map((destination) => [
    destination.destination.toLowerCase(),
    destination,
  ])
);

const POPULAR_DESTINATIONS_CACHE_KEY = "hotelsSearch:popularDestinations";
const POPULAR_DESTINATIONS_CACHE_TTL_MS = 60 * 60 * 1000;

function parseAvgPrice(value: string | undefined): number | null {
  if (!value) return null;
  const numeric = Number.parseFloat(value.replace(/[^\d.]/g, ""));
  return Number.isFinite(numeric) && numeric >= 0 ? numeric : null;
}

function readCachedPopularDestinations(): PopularDestinationProps[] | null {
  try {
    const stored = window.sessionStorage.getItem(POPULAR_DESTINATIONS_CACHE_KEY);
    if (!stored) return null;
    const parsed: unknown = JSON.parse(stored);
    if (
      typeof parsed !== "object" ||
      parsed === null ||
      !("ts" in parsed) ||
      !("destinations" in parsed)
    ) {
      return null;
    }
    const ts = (parsed as { ts: unknown }).ts;
    if (typeof ts !== "number" || Date.now() - ts > POPULAR_DESTINATIONS_CACHE_TTL_MS) {
      return null;
    }
    const destinations = (parsed as { destinations: unknown }).destinations;
    if (
      !Array.isArray(destinations) ||
      !destinations.every(
        (item) =>
          typeof item === "object" &&
          item !== null &&
          "destination" in item &&
          "priceFrom" in item &&
          "rating" in item
      )
    ) {
      return null;
    }
    return destinations as PopularDestinationProps[];
  } catch {
    return null;
  }
}

function writeCachedPopularDestinations(destinations: PopularDestinationProps[]): void {
  try {
    window.sessionStorage.setItem(
      POPULAR_DESTINATIONS_CACHE_KEY,
      JSON.stringify({ destinations, ts: Date.now() })
    );
  } catch {
    // ignore
  }
}

/** Hotel search client component. */
export default function HotelsSearchClient({
  onSubmitServer,
}: HotelsSearchClientProps) {
  const { initializeSearch, executeSearch, isSearching } = useSearchOrchestration();
  const searchError = useSearchResultsStore((state) => state.error);
  const activeFilters = useSearchFiltersStore((s) => s.activeFilters);
  const baseCurrency = useCurrencyStore((state) => state.baseCurrency);
  const { toast } = useToast();
  const [hasSearched, setHasSearched] = useState(false);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const currentSearchController = useRef<AbortController | null>(null);
  const filterPanelRef = useRef<HTMLDivElement | null>(null);
  const [selectedHotel, setSelectedHotel] = useState<HotelResult | null>(null);
  const [wishlistHotelIds, setWishlistHotelIds] = useState<Set<string>>(new Set());
  const [isWishlistUpdating, setIsWishlistUpdating] = useState(false);
  const [popularDestinations, setPopularDestinations] = useState<
    PopularDestinationProps[]
  >(() => POPULAR_DESTINATIONS.slice());
  const [isPopularDestinationsLoading, setIsPopularDestinationsLoading] =
    useState(false);
  const accommodationResults = useSearchResultsStore(
    (state) => state.results.accommodations ?? []
  );

  // Initialize accommodation search type on mount
  useEffect(() => {
    initializeSearch("accommodation");
  }, [initializeSearch]);

  useEffect(() => {
    return () => {
      currentSearchController.current?.abort();
      currentSearchController.current = null;
    };
  }, []);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem("hotelsSearch:wishlistHotels");
      if (!stored) return;
      const parsed: unknown = JSON.parse(stored);
      if (Array.isArray(parsed) && parsed.every((value) => typeof value === "string")) {
        setWishlistHotelIds(new Set(parsed));
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    const cached = readCachedPopularDestinations();
    if (cached) {
      setPopularDestinations(cached);
      return;
    }

    const controller = new AbortController();
    setIsPopularDestinationsLoading(true);
    (async () => {
      try {
        const res = await fetch("/api/accommodations/popular-destinations", {
          signal: controller.signal,
        });
        if (!res.ok) return;
        const body: unknown = await res.json();
        if (!Array.isArray(body)) return;
        const mapped = body
          .filter(
            (item): item is PopularDestinationApiResponse =>
              typeof item === "object" && item !== null && "city" in item
          )
          .map((item) => {
            const city = String(item.city ?? "").trim();
            const fallback = POPULAR_DESTINATIONS_BY_CITY.get(city.toLowerCase());
            const parsedPrice = parseAvgPrice(item.avgPrice);
            return {
              destination: city,
              priceFrom: parsedPrice ?? fallback?.priceFrom ?? 0,
              rating: fallback?.rating ?? 4.6,
            } satisfies PopularDestinationProps;
          })
          .filter((item) => item.destination.length > 0 && item.priceFrom > 0);

        if (mapped.length > 0) {
          setPopularDestinations(mapped);
          writeCachedPopularDestinations(mapped);
        }
      } catch (error) {
        if (
          controller.signal.aborted ||
          (error instanceof Error && error.name === "AbortError")
        ) {
          return;
        }
      } finally {
        setIsPopularDestinationsLoading(false);
      }
    })();

    return () => controller.abort();
  }, []);

  const hotelResults: HotelResult[] = useMemo(
    () => accommodationResults.map(mapAccommodationToHotelResult),
    [accommodationResults]
  );

  const hasAccommodationResults = hotelResults.length > 0;

  const sortedHotelResults = useMemo(
    () =>
      [...hotelResults].sort((first, second) => {
        const firstPrice = first.pricing.totalPrice ?? first.pricing.pricePerNight ?? 0;
        const secondPrice =
          second.pricing.totalPrice ?? second.pricing.pricePerNight ?? 0;

        return sortDirection === "asc"
          ? firstPrice - secondPrice
          : secondPrice - firstPrice;
      }),
    [hotelResults, sortDirection]
  );

  const handleHotelSelect = (hotel: HotelResult): Promise<void> => {
    setSelectedHotel(hotel);
    toast({
      description: `${hotel.name} selected`,
      title: "Hotel selected",
    });
    return Promise.resolve();
  };

  const updateWishlist = (hotelId: string): void => {
    if (isWishlistUpdating) return;
    setIsWishlistUpdating(true);
    try {
      const next = new Set(wishlistHotelIds);
      const wasSaved = next.has(hotelId);
      if (wasSaved) {
        next.delete(hotelId);
      } else {
        next.add(hotelId);
      }

      setWishlistHotelIds(next);
      try {
        window.localStorage.setItem(
          "hotelsSearch:wishlistHotels",
          JSON.stringify([...next])
        );
      } catch {
        // ignore
      }

      toast({
        description: wasSaved ? `Removed hotel ${hotelId}` : `Saved hotel ${hotelId}`,
        title: "Wishlist updated",
      });
    } catch (error) {
      toast({
        description: getErrorMessage(error),
        title: "Wishlist update failed",
        variant: "destructive",
      });
    } finally {
      setIsWishlistUpdating(false);
    }
  };

  const handleSaveToWishlist = (hotelId: string) => {
    updateWishlist(hotelId);
  };

  const handleSortClick = () => {
    setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
  };

  /** Scroll to filter panel in sidebar (useful on mobile where sidebar is below content) */
  const handleFilterClick = () => {
    filterPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const handleSearch = async (params: SearchAccommodationParams) => {
    currentSearchController.current?.abort();
    const controller = new AbortController();
    currentSearchController.current = controller;
    try {
      // Merge form params with active filter payload
      const filterPayload = buildHotelApiPayload(activeFilters);
      const searchWithFilters: SearchAccommodationParams = {
        ...params,
        ...filterPayload,
      };
      const validatedParams = await onSubmitServer(searchWithFilters); // server-side telemetry and validation
      if (controller.signal.aborted) return;
      await executeSearch(validatedParams, controller.signal); // client fetch/store update via orchestration
      if (controller.signal.aborted) return;
      setHasSearched(true);
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        return;
      }
      toast({
        description: getErrorMessage(error),
        title: "Search Error",
        variant: "destructive",
      });
    } finally {
      if (currentSearchController.current === controller) {
        currentSearchController.current = null;
      }
    }
  };

  return (
    <SearchLayout>
      <TooltipProvider>
        <Dialog
          open={selectedHotel !== null}
          onOpenChange={(open) => !open && setSelectedHotel(null)}
        >
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Hotel details</DialogTitle>
              <DialogDescription>
                {selectedHotel?.location.city
                  ? `${selectedHotel.name} • ${selectedHotel.location.city}`
                  : (selectedHotel?.name ?? null)}
              </DialogDescription>
            </DialogHeader>
            {selectedHotel ? (
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Rating</span>
                  <span className="font-medium">
                    {selectedHotel.userRating.toFixed(1)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Price/night</span>
                  <span className="font-medium">
                    {selectedHotel.pricing.currency}{" "}
                    {selectedHotel.pricing.pricePerNight.toFixed(2)}
                  </span>
                </div>
                <div className="pt-2 text-muted-foreground">
                  Booking flow is not yet available.
                </div>
              </div>
            ) : null}
          </DialogContent>
        </Dialog>

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
                  wishlistHotelIds={wishlistHotelIds}
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
                    {isPopularDestinationsLoading ? (
                      <p className="text-sm text-muted-foreground mb-4">
                        Loading popular destinations…
                      </p>
                    ) : null}
                    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {popularDestinations.map((destination) => (
                        <PopularDestinationCard
                          key={destination.destination}
                          currencyCode={baseCurrency}
                          {...destination}
                        />
                      ))}
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
          <div className="space-y-6" data-testid="filter-panel" ref={filterPanelRef}>
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

interface PopularDestinationCardProps extends PopularDestinationProps {
  currencyCode: string;
}

/**
 * Present a highlighted destination card with pricing and rating metadata.
 */
function PopularDestinationCard({
  destination,
  currencyCode,
  priceFrom,
  rating,
}: PopularDestinationCardProps) {
  const formattedPrice = new Intl.NumberFormat(undefined, {
    currency: currencyCode,
    maximumFractionDigits: 0,
    style: "currency",
  }).format(priceFrom);
  return (
    <Card className="h-full overflow-hidden transition-colors hover:bg-accent/50 group">
      <div className="h-40 bg-gradient-to-br from-primary/10 to-primary/5 flex items-center justify-center relative">
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
            <span className="font-semibold text-lg">{formattedPrice}</span>
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
