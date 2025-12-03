/**
 * @fileoverview Client-side hotel search experience (renders within RSC shell).
 */

"use client";

import type { SearchAccommodationParams } from "@schemas/search";
import {
  AlertCircleIcon,
  Building2Icon,
  FilterIcon,
  InfoIcon,
  LightbulbIcon,
  MapPinIcon,
  SearchIcon,
  SortAscIcon,
  StarIcon,
} from "lucide-react";
import { useState } from "react";
import { HotelSearchForm } from "@/components/features/search/hotel-search-form";
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
import { useAccommodationSearch } from "@/hooks/search/use-accommodation-search";
import { useSearchOrchestration } from "@/hooks/search/use-search-orchestration";

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
  const { search, isSearching, searchError } = useAccommodationSearch();
  const { hasResults } = useSearchOrchestration();
  const { toast } = useToast();
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (params: SearchAccommodationParams) => {
    setHasSearched(true);
    try {
      await onSubmitServer(params); // server-side telemetry and validation
      await search(params); // client fetch/store update
    } catch (error) {
      toast({
        description: error instanceof Error ? error.message : "Search failed",
        title: "Search Error",
        variant: "destructive",
      });
    }
  };

  return (
    <SearchLayout>
      <TooltipProvider>
        <div className="grid gap-6">
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
          {hasSearched && !isSearching && hasResults && (
            <div className="space-y-6">
              <div className="flex justify-between items-center flex-wrap gap-4">
                <h2 className="text-2xl font-semibold flex items-center gap-2">
                  <Building2Icon className="h-6 w-6" />
                  Found accommodations
                </h2>
                <div className="flex gap-2">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="outline" size="sm">
                        <SortAscIcon className="h-4 w-4 mr-2" />
                        Sort by Price
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Sort results by price</TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="outline" size="sm">
                        <FilterIcon className="h-4 w-4 mr-2" />
                        Filter
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Filter results</TooltipContent>
                  </Tooltip>
                </div>
              </div>

              <Card className="bg-muted/50">
                <CardContent className="text-center py-8 text-muted-foreground">
                  <InfoIcon className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>Search results would appear here</p>
                </CardContent>
              </Card>
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
          {hasSearched && !isSearching && !hasResults && !searchError && (
            <Card>
              <CardContent className="text-center py-12">
                <div className="flex flex-col items-center gap-4">
                  <div className="rounded-full bg-muted p-4">
                    <SearchIcon className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-lg font-semibold">No accommodations found</h3>
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
    <Card className="h-full overflow-hidden transition-colors hover:bg-accent/50 cursor-pointer group">
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
