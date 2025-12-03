/**
 * @fileoverview Client page for searching flights.
 */

"use client";

import type { FlightSearchParams } from "@schemas/search";
import { useRouter, useSearchParams } from "next/navigation";
import React from "react";
import { FilterPresets } from "@/components/features/search/filter-presets";
import { FlightSearchForm } from "@/components/features/search/flight-search-form";
import { SearchLayout } from "@/components/layouts/search-layout";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { useSearchFiltersStore } from "@/stores/search-filters-store";
import { useSearchStore } from "@/stores/search-store";

// URL search parameters are handled inline

/**
 * Client page for searching flights.
 * This page displays a flight search form and popular routes.
 *
 * @returns A React component that displays a flight search form and popular routes.
 */
export default function FlightSearchPage() {
  const { initializeSearch, executeSearch } = useSearchStore();
  const { setSearchType } = useSearchFiltersStore();
  const router = useRouter();
  const { toast } = useToast();
  const searchParams = useSearchParams();

  // Initialize flight search type on mount
  React.useEffect(() => {
    initializeSearch("flight");
    setSearchType("flight");

    // Check for search parameters in URL
    const origin = searchParams.get("origin");
    const destination = searchParams.get("destination");
    const departDate = searchParams.get("departDate");
    const returnDate = searchParams.get("returnDate");
    const passengers = searchParams.get("passengers");
    const flightClass = searchParams.get("class");

    if (origin || destination || departDate) {
      const initialParams: FlightSearchParams = {
        adults: passengers ? Number(passengers) : 1,
        cabinClass: (flightClass as FlightSearchParams["cabinClass"]) || "economy",
        departureDate: departDate || undefined,
        destination: destination || undefined,
        origin: origin || undefined,
        returnDate: returnDate || undefined,
      };
      executeSearch(initialParams);
    }
  }, [initializeSearch, executeSearch, searchParams, setSearchType]);

  const handleSearch = async (params: FlightSearchParams) => {
    try {
      const searchId = await executeSearch(params);
      if (searchId) {
        toast({
          description: "Searching for flights...",
          title: "Search Started",
        });
        // Navigate to results page or show results
        router.push(`/search/flights/results?searchId=${searchId}`);
      }
    } catch (error) {
      toast({
        description: error instanceof Error ? error.message : "An error occurred",
        title: "Search Failed",
        variant: "destructive",
      });
    }
  };

  return (
    <SearchLayout>
      <div className="grid gap-6 lg:grid-cols-4">
        {/* Main content - 3 columns */}
        <div className="lg:col-span-3 space-y-6">
          <FlightSearchForm onSearch={handleSearch} />

          {/*
           * TODO: POPULAR ROUTES - REAL DATA IMPLEMENTATION GUIDE
           * =====================================================
           * Status: Using hardcoded placeholder data
           * Priority: Medium (enhances UX but not blocking)
           *
           * CURRENT STATE:
           * - `/api/flights/popular-destinations` exists but returns destinations only (no prices/routes)
           * - Amadeus client (`domain/amadeus/client.ts`) only has hotel APIs implemented
           * - No flight pricing/offers API is currently integrated
           *
           * REQUIRED BACKEND WORK:
           *
           * 1. Extend Amadeus Client (`domain/amadeus/client.ts`):
           *    - Add `searchFlightOffers()` using `client.shopping.flightOffersSearch.get()`
           *    - Add `getFlightInspirationSearch()` using `client.shopping.flightDestinations.get()`
           *      (Returns cheapest destinations from origin - ideal for "deals")
           *
           * 2. Create New API Route (`/api/flights/popular-routes/route.ts`):
           *    ```typescript
           *    interface PopularRoute {
           *      origin: { code: string; name: string; };
           *      destination: { code: string; name: string; };
           *      price: number;
           *      currency: string;
           *      departureDate: string;
           *      returnDate?: string;
           *      airline?: string;
           *      source: 'amadeus' | 'cached' | 'user_history';
           *    }
           *    ```
           *    - Cache results in Upstash (TTL: 1 hour for prices, 24h for routes)
           *    - Support personalization based on user's search history
           *    - Fallback to curated routes if API fails
           *
           * 3. Add Zod Schema (`domain/schemas/flights.ts`):
           *    - `popularRouteSchema` for API response validation
           *    - `popularRoutesResponseSchema` for array response
           *
           * 4. Create React Query Hook (`hooks/use-popular-routes.ts`):
           *    ```typescript
           *    export function usePopularRoutes(origin?: string) {
           *      return useQuery({
           *        queryKey: ['popular-routes', origin],
           *        queryFn: () => fetch('/api/flights/popular-routes').then(r => r.json()),
           *        staleTime: 5 * 60 * 1000, // 5 minutes
           *        gcTime: 30 * 60 * 1000,   // 30 minutes
           *      });
           *    }
           *    ```
           *
           * 5. Update This Component:
           *    - Import and use `usePopularRoutes()` hook
           *    - Add loading skeleton state
           *    - Add error state with retry button
           *    - Keep hardcoded fallback for offline/error scenarios
           *
           * AMADEUS API ENDPOINTS TO INTEGRATE:
           * - Flight Offers Search: `GET /v2/shopping/flight-offers` (real-time pricing)
           * - Flight Inspiration Search: `GET /v1/shopping/flight-destinations` (cheapest routes)
           * - Flight Cheapest Date Search: `GET /v1/shopping/flight-dates` (price calendar)
           *
           * ENVIRONMENT VARIABLES NEEDED:
           * - AMADEUS_CLIENT_ID (already exists)
           * - AMADEUS_CLIENT_SECRET (already exists)
           * - AMADEUS_ENV (already exists)
           *
           * TESTING CONSIDERATIONS:
           * - Mock Amadeus responses in `test/msw/handlers/amadeus.ts`
           * - Add `popular-routes.test.ts` for the new API route
           * - E2E test for the flights page with mocked API
           *
           * COST CONSIDERATIONS:
           * - Amadeus API has rate limits and costs per call
           * - Implement aggressive caching to minimize API calls
           * - Consider background refresh vs on-demand fetching
           *
           * SEE ALSO:
           * - `/api/flights/popular-destinations/route.ts` - existing destinations API
           * - `domain/amadeus/client.ts` - Amadeus client patterns
           * - `lib/cache/upstash.ts` - caching utilities
           */}
          <Card>
            <CardHeader>
              <CardTitle>Popular Routes</CardTitle>
              <CardDescription>Trending flight routes and deals</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                <PopularRouteCard
                  origin="New York"
                  destination="London"
                  price={456}
                  date="May 28, 2025"
                />
                <PopularRouteCard
                  origin="Los Angeles"
                  destination="Tokyo"
                  price={789}
                  date="Jun 15, 2025"
                />
                <PopularRouteCard
                  origin="Chicago"
                  destination="Paris"
                  price={567}
                  date="Jun 8, 2025"
                />
                <PopularRouteCard
                  origin="Miami"
                  destination="Barcelona"
                  price={623}
                  date="Jun 22, 2025"
                />
                <PopularRouteCard
                  origin="Seattle"
                  destination="Amsterdam"
                  price={749}
                  date="Jul 10, 2025"
                />
                <PopularRouteCard
                  origin="Dallas"
                  destination="Sydney"
                  price={999}
                  date="Jul 18, 2025"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Travel Tips</CardTitle>
              <CardDescription>Tips to help you find the best flights</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <TravelTip
                  title="Book 1-3 months in advance for the best prices"
                  description="Studies show that booking domestic flights about 1-3 months in advance and international flights 2-8 months in advance typically yields the best prices."
                />
                <TravelTip
                  title="Book in Advance"
                  description="Save up to 30% by booking flights 6-8 weeks ahead."
                />
                <TravelTip
                  title="Consider nearby airports"
                  description="Flying to or from a nearby airport can sometimes save you hundreds of dollars. Our search automatically checks nearby airports too."
                />
                <TravelTip
                  title="Be flexible with dates if possible"
                  description="Prices can vary significantly from one day to the next. Use our flexible dates option to see prices across multiple days and find the best deal."
                />
                <TravelTip
                  title="Set price alerts for your routes"
                  description="If your travel dates are still far out, set up price alerts to be notified when prices drop for your specific routes."
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar - 1 column */}
        <div className="space-y-6">
          <FilterPresets />
        </div>
      </div>
    </SearchLayout>
  );
}

/**
 * Card component for displaying a popular route.
 *
 * @param origin - The origin of the route.
 * @param destination - The destination of the route.
 * @param price - The price of the route.
 * @param date - The date of the route.
 * @returns A React component that displays a popular route.
 */
function PopularRouteCard({
  origin,
  destination,
  price,
  date,
}: {
  origin: string;
  destination: string;
  price: number;
  date: string;
}) {
  return (
    <Card className="h-full hover:bg-accent/50 transition-colors cursor-pointer">
      <CardContent className="p-4">
        <div className="flex justify-between items-start mb-3">
          <div>
            <h3 className="font-medium">
              {origin} to {destination}
            </h3>
            <p className="text-xs text-muted-foreground">{date}</p>
          </div>
          <div className="text-right">
            <span className="font-semibold text-lg">${price}</span>
            <p className="text-xs text-muted-foreground">roundtrip</p>
          </div>
        </div>
        <div>
          <button type="button" className="text-xs text-primary hover:underline">
            View Deal →
          </button>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Component for displaying a travel tip.
 *
 * @param title - The title of the travel tip.
 * @param description - The description of the travel tip.
 * @returns A React component that displays a travel tip.
 */
function TravelTip({ title, description }: { title: string; description: string }) {
  return (
    <div className="p-4 border rounded-lg">
      <h3 className="font-medium mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
