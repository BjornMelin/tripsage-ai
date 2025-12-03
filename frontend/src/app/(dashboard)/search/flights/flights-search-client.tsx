/**
 * @fileoverview Client-side flight search experience (renders within RSC shell).
 */

"use client";

import type { FlightSearchParams } from "@schemas/search";
import {
  ArrowRightIcon,
  InfoIcon,
  LightbulbIcon,
  PlaneIcon,
  TrendingUpIcon,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import React from "react";
import { FilterPanel } from "@/components/features/search/filter-panel";
import { FilterPresets } from "@/components/features/search/filter-presets";
import { FlightSearchForm } from "@/components/features/search/flight-search-form";
import { SearchLayout } from "@/components/layouts/search-layout";
import { Badge } from "@/components/ui/badge";
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
import { useToast } from "@/components/ui/use-toast";
import { useSearchOrchestration } from "@/hooks/search/use-search-orchestration";

/** Flight search client component props. */
interface FlightsSearchClientProps {
  onSubmitServer: (params: FlightSearchParams) => Promise<FlightSearchParams>;
}

/** Flight search client component. */
export default function FlightsSearchClient({
  onSubmitServer,
}: FlightsSearchClientProps) {
  const { initializeSearch, executeSearch } = useSearchOrchestration();
  const router = useRouter();
  const { toast } = useToast();
  const searchParams = useSearchParams();

  // Initialize flight search type on mount
  React.useEffect(() => {
    initializeSearch("flight");

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
      // Server-side telemetry then client execution
      onSubmitServer(initialParams)
        .then(() => executeSearch(initialParams))
        .catch(() => {
          // Errors surfaced via toast
        });
    }
  }, [initializeSearch, executeSearch, searchParams, onSubmitServer]);

  const handleSearch = async (params: FlightSearchParams) => {
    try {
      await onSubmitServer(params); // server-side telemetry and validation
      const searchId = await executeSearch(params);
      if (searchId) {
        toast({
          description: "Searching for flights...",
          title: "Search Started",
        });
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
      <TooltipProvider>
        <div className="grid gap-6 lg:grid-cols-4">
          {/* Main content - 3 columns */}
          <div className="lg:col-span-3 space-y-6">
            {/* Search Form */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <PlaneIcon className="h-5 w-5" />
                  Search Flights
                </CardTitle>
                <CardDescription>
                  Find the best flight deals to your destination
                </CardDescription>
              </CardHeader>
              <CardContent>
                <FlightSearchForm onSearch={handleSearch} />
              </CardContent>
            </Card>

            {/* Popular Routes */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUpIcon className="h-5 w-5" />
                  Popular Routes
                </CardTitle>
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

            {/* Travel Tips */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <LightbulbIcon className="h-5 w-5" />
                  Travel Tips
                </CardTitle>
                <CardDescription>
                  Tips to help you find the best flights
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <TravelTip
                    title="Book 1-3 months in advance for the best prices"
                    description="Studies show that booking domestic flights about 1-3 months in advance and international flights 2-8 months in advance typically yields the best prices."
                  />
                  <Separator />
                  <TravelTip
                    title="Consider nearby airports"
                    description="Flying to or from a nearby airport can sometimes save you hundreds of dollars. Our search automatically checks nearby airports too."
                  />
                  <Separator />
                  <TravelTip
                    title="Be flexible with dates if possible"
                    description="Prices can vary significantly from one day to the next. Use our flexible dates option to see prices across multiple days and find the best deal."
                  />
                  <Separator />
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
            <FilterPanel />
            <FilterPresets />
          </div>
        </div>
      </TooltipProvider>
    </SearchLayout>
  );
}

/** Card component for displaying a popular route. */
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
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Card className="h-full hover:bg-accent/50 transition-colors cursor-pointer group">
            <CardContent className="p-4">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="font-medium flex items-center gap-2">
                    {origin}
                    <ArrowRightIcon className="h-4 w-4 text-muted-foreground" />
                    {destination}
                  </h3>
                  <p className="text-xs text-muted-foreground mt-1">{date}</p>
                </div>
                <div className="text-right">
                  <span className="font-semibold text-lg">${price}</span>
                  <p className="text-xs text-muted-foreground">roundtrip</p>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <Badge variant="secondary" className="text-xs">
                  <PlaneIcon className="h-3 w-3 mr-1" />
                  Deal
                </Badge>
                <span className="text-xs text-primary font-medium group-hover:underline">
                  View Deal →
                </span>
              </div>
            </CardContent>
          </Card>
        </TooltipTrigger>
        <TooltipContent>
          Click to search {origin} to {destination}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/**
 * Component for displaying a travel tip.
 */
function TravelTip({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex gap-4">
      <div className="shrink-0">
        <div className="rounded-full bg-primary/10 p-2">
          <InfoIcon className="h-4 w-4 text-primary" />
        </div>
      </div>
      <div>
        <h3 className="font-medium mb-1">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}
