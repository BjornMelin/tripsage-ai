/**
 * @fileoverview Client-side hotel search experience (renders within RSC shell).
 */

"use client";

import type { HotelResult, SearchAccommodationParams } from "@schemas/search";
import {
  AlertCircleIcon,
  Building2Icon,
  FilterIcon,
  SearchIcon,
  SortAscIcon,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { SearchLayout } from "@/components/layouts/search-layout";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { HotelSkeleton } from "@/components/ui/travel-skeletons";
import { useToast } from "@/components/ui/use-toast";
import { buildHotelApiPayload } from "@/features/search/components/filters/api-payload";
import { FilterPanel } from "@/features/search/components/filters/filter-panel";
import { HotelSearchForm } from "@/features/search/components/forms/hotel-search-form";
import { HotelResults } from "@/features/search/components/results/hotel-results";
import {
  HOTEL_WISHLIST_STORAGE_KEY,
  isAbortError,
  toggleStringSetValue,
  useAbortableSearchTask,
  usePersistentStringSet,
} from "@/features/search/hooks/search/use-search-client-state";
import { useSearchOrchestration } from "@/features/search/hooks/search/use-search-orchestration";
import { useSearchFiltersStore } from "@/features/search/store/search-filters-store";
import { useSearchResultsStore } from "@/features/search/store/search-results-store";
import { useCurrencyStore } from "@/features/shared/store/currency-store";
import { getErrorMessage } from "@/lib/api/error-types";
import type { Result, ResultError } from "@/lib/result";
import { mapAccommodationToHotelResult } from "./hotel-mapping";
import { HotelsEmptyState } from "./hotels-empty-state";
import {
  DEFAULT_POPULAR_DESTINATIONS,
  mapPopularDestinationsFromApiResponse,
  type PopularDestinationProps,
  readCachedPopularDestinations,
  writeCachedPopularDestinations,
} from "./popular-destinations";

/** Hotel search client component props. */
interface HotelsSearchClientProps {
  onSubmitServer: (
    params: SearchAccommodationParams
  ) => Promise<Result<SearchAccommodationParams, ResultError>>;
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
  const { clearSearchController, startSearchController } = useAbortableSearchTask();
  const filterPanelRef = useRef<HTMLDivElement | null>(null);
  const [selectedHotel, setSelectedHotel] = useState<HotelResult | null>(null);
  const [wishlistHotelIds, setWishlistHotelIds] = usePersistentStringSet(
    HOTEL_WISHLIST_STORAGE_KEY
  );
  const [isWishlistUpdating, setIsWishlistUpdating] = useState(false);
  const [popularDestinations, setPopularDestinations] = useState<
    PopularDestinationProps[]
  >(() => DEFAULT_POPULAR_DESTINATIONS.slice());
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
    const cached = readCachedPopularDestinations(window.sessionStorage, Date.now());
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
        const mapped = mapPopularDestinationsFromApiResponse(body);

        if (!controller.signal.aborted && mapped.length > 0) {
          setPopularDestinations(mapped);
          writeCachedPopularDestinations(window.sessionStorage, Date.now(), mapped);
        }
      } catch (error) {
        if (controller.signal.aborted || isAbortError(error)) {
          return;
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsPopularDestinationsLoading(false);
        }
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
      let wasPresent = false;
      setWishlistHotelIds((currentValues) => {
        const toggled = toggleStringSetValue(currentValues, hotelId);
        wasPresent = toggled.wasPresent;
        return toggled.nextValues;
      });

      toast({
        description: wasPresent ? `Removed hotel ${hotelId}` : `Saved hotel ${hotelId}`,
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
    const controller = startSearchController();
    try {
      // Merge form params with active filter payload
      const filterPayload = buildHotelApiPayload(activeFilters);
      const searchWithFilters: SearchAccommodationParams = {
        ...params,
        ...filterPayload,
      };
      const validatedParams = await onSubmitServer(searchWithFilters); // server-side telemetry and validation
      if (controller.signal.aborted) return;
      if (!validatedParams.ok) {
        toast({
          description: validatedParams.error.reason,
          title: "Search Error",
          variant: "destructive",
        });
        return;
      }

      await executeSearch(validatedParams.data, controller.signal); // client fetch/store update via orchestration
      if (controller.signal.aborted) return;
      setHasSearched(true);
    } catch (error) {
      if (controller.signal.aborted || isAbortError(error)) {
        return;
      }
      toast({
        description: getErrorMessage(error),
        title: "Search Error",
        variant: "destructive",
      });
    } finally {
      clearSearchController(controller);
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
          <div className="lg:col-span-3 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Building2Icon aria-hidden="true" className="h-5 w-5" />
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

            {searchError && (
              <Alert variant="destructive">
                <AlertCircleIcon aria-hidden="true" className="h-4 w-4" />
                <AlertTitle>Search Error</AlertTitle>
                <AlertDescription>
                  {searchError.message || "An error occurred during search"}
                </AlertDescription>
              </Alert>
            )}

            {isSearching && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <SearchIcon aria-hidden="true" className="h-5 w-5 animate-pulse" />
                    Searching for accommodations…
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

            {hasSearched && !isSearching && hasAccommodationResults && (
              <div className="space-y-6">
                <div className="flex justify-between items-center flex-wrap gap-4">
                  <h2 className="text-2xl font-semibold flex items-center gap-2">
                    <Building2Icon aria-hidden="true" className="h-6 w-6" />
                    Found accommodations
                  </h2>
                  <div className="flex gap-2">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button onClick={handleSortClick} variant="outline" size="sm">
                          <SortAscIcon aria-hidden="true" className="h-4 w-4 mr-2" />
                          Sort by Price (
                          {sortDirection === "asc" ? "Low→High" : "High→Low"})
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>Sort results by total price</TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button onClick={handleFilterClick} variant="outline" size="sm">
                          <FilterIcon aria-hidden="true" className="h-4 w-4 mr-2" />
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

            {!hasSearched && !isSearching && (
              <HotelsEmptyState
                baseCurrency={baseCurrency}
                popularDestinations={popularDestinations}
                isPopularDestinationsLoading={isPopularDestinationsLoading}
              />
            )}

            {hasSearched &&
              !isSearching &&
              !hasAccommodationResults &&
              !searchError && (
                <Card>
                  <CardContent className="text-center py-12">
                    <div className="flex flex-col items-center gap-4">
                      <div className="rounded-full bg-muted p-4">
                        <SearchIcon
                          aria-hidden="true"
                          className="h-8 w-8 text-muted-foreground"
                        />
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

          <div className="space-y-6" data-testid="filter-panel" ref={filterPanelRef}>
            <FilterPanel />
          </div>
        </div>
      </TooltipProvider>
    </SearchLayout>
  );
}
