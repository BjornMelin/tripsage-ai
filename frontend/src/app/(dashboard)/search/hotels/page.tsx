/**
 * @fileoverview Client page for hotel search with optimistic loading states and curated content.
 */
"use client";

import type { SearchAccommodationParams } from "@schemas/search";
import { useState } from "react";
import { HotelSearchForm } from "@/components/features/search/hotel-search-form";
import { SearchLayout } from "@/components/layouts/search-layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAccommodationSearch } from "@/hooks/use-accommodation-search";
import { useSearchOrchestration } from "@/hooks/use-search-orchestration";

/**
 * Render the hotel search experience with simple loading and empty states.
 *
 * @returns The rendered hotel search page.
 */
export default function HotelSearchPage() {
  const { search, isSearching } = useAccommodationSearch();
  const { hasResults } = useSearchOrchestration();
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (params: SearchAccommodationParams) => {
    setHasSearched(true);
    try {
      await search(params);
    } catch (error) {
      // DecisionFramework§2.1(L1): Surface errors via forthcoming UI; console preserves debugging signal.
      console.error("Accommodation search failed", error);
    }
  };

  return (
    <SearchLayout>
      <div className="grid gap-6">
        <HotelSearchForm onSearch={handleSearch} />

        {/* Error handling removed for MVP testing */}

        {isSearching && (
          <Card>
            <CardHeader>
              <CardTitle>Searching for accommodations...</CardTitle>
              <CardDescription>
                Please wait while we find the best options for you
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex gap-4">
                    <Skeleton className="h-32 w-48" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-6 w-3/4" />
                      <Skeleton className="h-4 w-1/2" />
                      <Skeleton className="h-4 w-1/3" />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {hasSearched && !isSearching && hasResults && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-semibold">Found accommodations</h2>
              <div className="flex gap-2">
                <Button variant="outline" size="sm">
                  Sort by Price
                </Button>
                <Button variant="outline" size="sm">
                  Filter
                </Button>
              </div>
            </div>

            {/* Results component removed for MVP testing */}
            <div className="text-center py-8 text-muted-foreground">
              Search results would appear here
            </div>
          </div>
        )}

        {!hasSearched && !isSearching && (
          <>
            <Card>
              <CardHeader>
                <CardTitle>Popular Destinations</CardTitle>
                <CardDescription>Trending hotel destinations and deals</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <PopularDestinationCard
                    destination="New York"
                    priceFrom={199}
                    image="/placeholder.jpg"
                    rating={4.8}
                  />
                  <PopularDestinationCard
                    destination="Paris"
                    priceFrom={229}
                    image="/placeholder.jpg"
                    rating={4.7}
                  />
                  <PopularDestinationCard
                    destination="Tokyo"
                    priceFrom={179}
                    image="/placeholder.jpg"
                    rating={4.9}
                  />
                  <PopularDestinationCard
                    destination="London"
                    priceFrom={249}
                    image="/placeholder.jpg"
                    rating={4.6}
                  />
                  <PopularDestinationCard
                    destination="Barcelona"
                    priceFrom={189}
                    image="/placeholder.jpg"
                    rating={4.8}
                  />
                  <PopularDestinationCard
                    destination="Rome"
                    priceFrom={219}
                    image="/placeholder.jpg"
                    rating={4.7}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Accommodation Tips</CardTitle>
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
                  <AccommodationTip
                    title="Consider location carefully"
                    description="A slightly higher price for a central location can save you time and transportation costs. Use the map view to see where properties are located relative to attractions."
                  />
                  <AccommodationTip
                    title="Check cancellation policies"
                    description="For maximum flexibility, filter for properties with free cancellation. This allows you to lock in a good rate while still keeping your options open."
                  />
                  <AccommodationTip
                    title="Read recent reviews"
                    description="Look at reviews from the last 3-6 months to get the most accurate picture of the current state of the property. Pay special attention to reviews from travelers similar to you."
                  />
                </div>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </SearchLayout>
  );
}

interface PopularDestinationProps {
  destination: string;
  priceFrom: number;
  image: string;
  rating: number;
}

/**
 * Present a highlighted destination card with pricing and rating metadata.
 *
 * @param props - Destination details to display.
 * @returns A rendered destination card element.
 */
function PopularDestinationCard({
  destination,
  priceFrom,
  image,
  rating,
}: PopularDestinationProps) {
  return (
    <Card className="h-full overflow-hidden transition-colors hover:bg-accent/50 cursor-pointer">
      <div
        className="h-40 bg-muted flex items-center justify-center bg-cover bg-center"
        style={{ backgroundImage: `url(${image})` }}
        role="img"
        aria-label={`${destination} destination preview`}
      >
        <span className="text-muted-foreground bg-background/80 px-2 py-1 rounded">
          Image preview
        </span>
      </div>
      <CardContent className="p-4">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="font-medium">{destination}</h3>
            <div className="flex items-center mt-1">
              <Badge variant="secondary" className="text-xs">
                {rating} ★
              </Badge>
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-muted-foreground">from</p>
            <span className="font-semibold">${priceFrom}</span>
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
 *
 * @param props - The tip content to render.
 * @returns Structured tip content.
 */
function AccommodationTip({ title, description }: AccommodationTipProps) {
  return (
    <div className="p-4 border rounded-lg">
      <h3 className="font-medium mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
