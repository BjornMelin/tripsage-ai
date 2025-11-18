"use client";

import { ArrowRight, Filter, Plane } from "lucide-react";
import { useSearchParams } from "next/navigation";
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
import { Separator } from "@/components/ui/separator";
import { useSearchResultsStore } from "@/stores/search-results-store";

export default function FlightResultsPage() {
  const searchParams = useSearchParams();
  const searchId = searchParams.get("searchId");
  const {
    results: _results,
    status,
    currentContext,
    searchProgress,
  } = useSearchResultsStore();

  // Mock flight results for demo
  const mockFlights = [
    {
      airline: "British Airways",
      arrival: { airport: "LHR", city: "London", time: "20:45" },
      cabin: "Economy",
      departure: { airport: "JFK", city: "New York", time: "08:30" },
      duration: "7h 15m",
      flightNumber: "BA 178",
      id: "flight-1",
      price: 599,
      stops: 0,
    },
    {
      airline: "Virgin Atlantic",
      arrival: { airport: "LHR", city: "London", time: "23:20" },
      cabin: "Economy",
      departure: { airport: "JFK", city: "New York", time: "11:45" },
      duration: "7h 35m",
      flightNumber: "VS 3",
      id: "flight-2",
      price: 649,
      stops: 0,
    },
    {
      airline: "American Airlines",
      arrival: { airport: "LHR", city: "London", time: "10:30+1" },
      cabin: "Economy",
      departure: { airport: "JFK", city: "New York", time: "22:00" },
      duration: "7h 30m",
      flightNumber: "AA 106",
      id: "flight-3",
      price: 579,
      stops: 0,
    },
  ];

  if (!searchId) {
    return (
      <SearchLayout>
        <Card>
          <CardHeader>
            <CardTitle>Invalid Search</CardTitle>
            <CardDescription>No search ID provided.</CardDescription>
          </CardHeader>
        </Card>
      </SearchLayout>
    );
  }

  return (
    <SearchLayout>
      <div className="space-y-6">
        {/* Search Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plane className="h-5 w-5" />
              Flight Search Results
            </CardTitle>
            <CardDescription>
              {currentContext
                ? `Searching flights from ${currentContext.searchParams?.from || "Unknown"} to ${currentContext.searchParams?.to || "Unknown"}`
                : `Search ID: ${searchId}`}
            </CardDescription>
          </CardHeader>
          {currentContext && (
            <CardContent>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">
                  {(() => {
                    const passengers =
                      Number(currentContext.searchParams?.passengers) || 1;
                    return `${passengers} passenger${passengers > 1 ? "s" : ""}`;
                  })()}
                </Badge>
                <Badge variant="outline">
                  {String(currentContext.searchParams?.class || "Economy")}
                </Badge>
                <Badge variant="outline">
                  {String(currentContext.searchParams?.tripType || "Round trip")}
                </Badge>
              </div>
            </CardContent>
          )}
        </Card>

        {/* Search Status */}
        {status === "searching" && (
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <span>Searching for flights...</span>
                <span>{searchProgress}%</span>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Results */}
        <div className="flex gap-6">
          {/* Filters Sidebar */}
          <div className="w-64 space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Filter className="h-4 w-4" />
                  Filters
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="font-medium mb-2">Price Range</h4>
                  <div className="text-sm text-muted-foreground">$579 - $649</div>
                </div>
                <Separator />
                <div>
                  <h4 className="font-medium mb-2">Airlines</h4>
                  <div className="space-y-1 text-sm">
                    <div>British Airways (1)</div>
                    <div>Virgin Atlantic (1)</div>
                    <div>American Airlines (1)</div>
                  </div>
                </div>
                <Separator />
                <div>
                  <h4 className="font-medium mb-2">Stops</h4>
                  <div className="text-sm">
                    <div>Direct (3)</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Flight Results */}
          <div className="flex-1 space-y-4">
            {mockFlights.map((flight) => (
              <Card key={flight.id} className="hover:shadow-md transition-shadow">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-6">
                      {/* Airline Info */}
                      <div>
                        <div className="font-semibold">{flight.airline}</div>
                        <div className="text-sm text-muted-foreground">
                          {flight.flightNumber}
                        </div>
                      </div>

                      {/* Flight Route */}
                      <div className="flex items-center gap-4">
                        <div className="text-center">
                          <div className="font-semibold text-lg">
                            {flight.departure.time}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {flight.departure.airport}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {flight.departure.city}
                          </div>
                        </div>

                        <div className="flex flex-col items-center gap-1">
                          <div className="text-xs text-muted-foreground">
                            {flight.duration}
                          </div>
                          <div className="flex items-center">
                            <div className="w-16 h-px bg-border" />
                            <ArrowRight className="h-3 w-3 mx-1 text-muted-foreground" />
                            <div className="w-16 h-px bg-border" />
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {flight.stops === 0
                              ? "Direct"
                              : `${flight.stops} stop${flight.stops > 1 ? "s" : ""}`}
                          </div>
                        </div>

                        <div className="text-center">
                          <div className="font-semibold text-lg">
                            {flight.arrival.time}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {flight.arrival.airport}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {flight.arrival.city}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Price and Book */}
                    <div className="text-right">
                      <div className="text-2xl font-bold text-green-600">
                        ${flight.price}
                      </div>
                      <div className="text-sm text-muted-foreground mb-3">
                        per person
                      </div>
                      <Button className="w-24">Select</Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}

            {/* Load More */}
            <div className="text-center pt-4">
              <Button variant="outline">Load More Results</Button>
            </div>
          </div>
        </div>
      </div>
    </SearchLayout>
  );
}
