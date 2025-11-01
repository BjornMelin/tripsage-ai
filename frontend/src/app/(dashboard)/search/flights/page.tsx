"use client";

import { useRouter, useSearchParams } from "next/navigation";
import React from "react";
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
import { useSearchStore } from "@/stores/search-store";
import type { FlightSearchParams } from "@/types/search";

// URL search parameters are handled inline

export default function FlightSearchPage() {
  const { initializeSearch, executeSearch } = useSearchStore();
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
        origin: origin || undefined,
        destination: destination || undefined,
        departureDate: departDate || undefined,
        returnDate: returnDate || undefined,
        adults: passengers ? Number(passengers) : 1,
        cabinClass: (flightClass as FlightSearchParams["cabinClass"]) || "economy",
      };
      executeSearch(initialParams);
    }
  }, [initializeSearch, executeSearch, searchParams]);

  const handleSearch = async (params: FlightSearchParams) => {
    try {
      const searchId = await executeSearch(params);
      if (searchId) {
        toast({
          title: "Search Started",
          description: "Searching for flights...",
        });
        // Navigate to results page or show results
        router.push(`/search/flights/results?searchId=${searchId}`);
      }
    } catch (error) {
      toast({
        title: "Search Failed",
        description: error instanceof Error ? error.message : "An error occurred",
        variant: "destructive",
      });
    }
  };

  return (
    <SearchLayout>
      <div className="grid gap-6">
        <FlightSearchForm onSearch={handleSearch} />

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
                price={499}
                date="Dec 2025"
              />
              <PopularRouteCard
                origin="Los Angeles"
                destination="Tokyo"
                price={799}
                date="Nov 2025"
              />
              <PopularRouteCard
                origin="Chicago"
                destination="Paris"
                price={649}
                date="Aug 2025"
              />
              <PopularRouteCard
                origin="Miami"
                destination="Cancun"
                price={299}
                date="Sep 2025"
              />
              <PopularRouteCard
                origin="Seattle"
                destination="Amsterdam"
                price={749}
                date="Oct 2025"
              />
              <PopularRouteCard
                origin="Dallas"
                destination="Sydney"
                price={999}
                date="Nov 2025"
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
    </SearchLayout>
  );
}

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

function TravelTip({ title, description }: { title: string; description: string }) {
  return (
    <div className="p-4 border rounded-lg">
      <h3 className="font-medium mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
