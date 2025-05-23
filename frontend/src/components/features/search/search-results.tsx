"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AccommodationCard } from "./accommodation-card";
import type {
  SearchType,
  Flight,
  Accommodation,
  Activity,
  SearchResults as SearchResultsType,
  SearchResult,
} from "@/types/search";

interface SearchResultsProps {
  type?: SearchType;
  results: SearchResultsType | Flight[] | Accommodation[] | Activity[];
  loading?: boolean;
  onFilter?: (filters: Record<string, any>) => void;
  onSort?: (sortBy: string, direction: "asc" | "desc") => void;
  onSelectResult?: (result: SearchResult) => void;
}

export function SearchResults({
  type,
  results,
  loading = false,
  onFilter,
  onSort,
  onSelectResult,
}: SearchResultsProps) {
  const [sortBy, setSortBy] = useState<string>("price");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [activeView, setActiveView] = useState<"list" | "grid" | "map">("list");

  // Extract the actual results array based on the type
  const getResultsArray = (): SearchResult[] => {
    if (!results) return [];
    
    // If results is already an array
    if (Array.isArray(results)) return results;
    
    // If results is SearchResultsType, extract based on type
    if (type === "accommodation" && "accommodations" in results) {
      return results.accommodations || [];
    }
    if (type === "flight" && "flights" in results) {
      return results.flights || [];
    }
    if (type === "activity" && "activities" in results) {
      return results.activities || [];
    }
    
    return [];
  };

  const resultsArray = getResultsArray();

  const handleSort = (field: string) => {
    const newDirection =
      sortBy === field && sortDirection === "asc" ? "desc" : "asc";
    setSortBy(field);
    setSortDirection(newDirection);

    if (onSort) {
      onSort(field, newDirection);
    }
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <CardTitle>
            {loading ? "Searching..." : `${resultsArray.length} Results`}
          </CardTitle>
          <div className="flex space-x-2">
            <Button
              variant={activeView === "list" ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveView("list")}
            >
              List
            </Button>
            <Button
              variant={activeView === "grid" ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveView("grid")}
            >
              Grid
            </Button>
            <Button
              variant={activeView === "map" ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveView("map")}
            >
              Map
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex mb-4">
          <div className="flex space-x-2 text-sm">
            <Button
              variant="ghost"
              size="sm"
              className="h-8"
              onClick={() => handleSort("price")}
            >
              Price
              {sortBy === "price" && (
                <span className="ml-1">
                  {sortDirection === "asc" ? "↑" : "↓"}
                </span>
              )}
            </Button>
            {type === "flight" && (
              <>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8"
                  onClick={() => handleSort("duration")}
                >
                  Duration
                  {sortBy === "duration" && (
                    <span className="ml-1">
                      {sortDirection === "asc" ? "↑" : "↓"}
                    </span>
                  )}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8"
                  onClick={() => handleSort("stops")}
                >
                  Stops
                  {sortBy === "stops" && (
                    <span className="ml-1">
                      {sortDirection === "asc" ? "↑" : "↓"}
                    </span>
                  )}
                </Button>
              </>
            )}
            {(type === "accommodation" || type === "activity") && (
              <Button
                variant="ghost"
                size="sm"
                className="h-8"
                onClick={() => handleSort("rating")}
              >
                Rating
                {sortBy === "rating" && (
                  <span className="ml-1">
                    {sortDirection === "asc" ? "↑" : "↓"}
                  </span>
                )}
              </Button>
            )}
          </div>
        </div>

        {loading ? (
          <div className="py-8 flex justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : resultsArray.length === 0 ? (
          <div className="py-8 text-center">
            <p className="text-muted-foreground">
              No results found. Try adjusting your search criteria.
            </p>
          </div>
        ) : (
          <div
            className={
              activeView === "grid"
                ? "grid md:grid-cols-2 lg:grid-cols-3 gap-4"
                : "space-y-4"
            }
          >
            {type === "flight" &&
              (resultsArray as Flight[]).map((flight) => (
                <FlightResultCard
                  key={flight.id}
                  flight={flight}
                  view={activeView}
                />
              ))}
            {type === "accommodation" &&
              (resultsArray as Accommodation[]).map((accommodation) => (
                <AccommodationCard
                  key={accommodation.id}
                  accommodation={accommodation}
                  onSelect={onSelectResult}
                />
              ))}
            {type === "activity" &&
              (resultsArray as Activity[]).map((activity) => (
                <ActivityResultCard
                  key={activity.id}
                  activity={activity}
                  view={activeView}
                />
              ))}
          </div>
        )}

        {!loading && resultsArray.length > 0 && (
          <div className="mt-4 flex justify-center">
            <Button variant="outline">Load More</Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function FlightResultCard({
  flight,
  view,
}: { flight: Flight; view: "list" | "grid" | "map" }) {
  return (
    <Card
      className={`hover:bg-accent/50 transition-colors cursor-pointer ${view === "list" ? "flex" : ""}`}
    >
      <CardContent className={`p-4 ${view === "list" ? "flex flex-1" : ""}`}>
        {view === "list" ? (
          <>
            <div className="flex-1">
              <div className="flex justify-between mb-2">
                <div>
                  <p className="font-medium">
                    {flight.airline} {flight.flightNumber}
                  </p>
                  <div className="text-sm text-muted-foreground">
                    {flight.stops === 0
                      ? "Nonstop"
                      : `${flight.stops} stop${flight.stops > 1 ? "s" : ""}`}
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-medium">${flight.price}</p>
                  <p className="text-xs text-muted-foreground">per person</p>
                </div>
              </div>
              <div className="flex items-center space-x-4 mt-2">
                <div>
                  <p className="font-medium">{flight.departureTime}</p>
                  <p className="text-sm">{flight.origin}</p>
                </div>
                <div className="flex-1 flex items-center px-2">
                  <div className="h-0.5 w-full bg-muted relative">
                    <div className="absolute top-1/2 left-1/2 transform -translate-y-1/2 -translate-x-1/2 text-xs text-muted-foreground whitespace-nowrap">
                      {Math.floor(flight.duration / 60)}h {flight.duration % 60}
                      m
                    </div>
                  </div>
                </div>
                <div>
                  <p className="font-medium">{flight.arrivalTime}</p>
                  <p className="text-sm">{flight.destination}</p>
                </div>
              </div>
            </div>
            <div className="ml-4 flex items-center">
              <Button>Select</Button>
            </div>
          </>
        ) : (
          <>
            <div className="mb-2">
              <p className="font-medium">
                {flight.airline} {flight.flightNumber}
              </p>
              <div className="text-sm text-muted-foreground mb-2">
                {flight.stops === 0
                  ? "Nonstop"
                  : `${flight.stops} stop${flight.stops > 1 ? "s" : ""}`}
              </div>
              <div className="flex justify-between items-center mb-2">
                <div>
                  <p className="font-medium">{flight.departureTime}</p>
                  <p className="text-sm">{flight.origin}</p>
                </div>
                <div>
                  <p className="font-medium">{flight.arrivalTime}</p>
                  <p className="text-sm">{flight.destination}</p>
                </div>
              </div>
              <div className="h-0.5 w-full bg-muted relative mb-3">
                <div className="absolute top-1/2 left-1/2 transform -translate-y-1/2 -translate-x-1/2 text-xs text-muted-foreground">
                  {Math.floor(flight.duration / 60)}h {flight.duration % 60}m
                </div>
              </div>
            </div>
            <div className="flex justify-between items-center mt-2">
              <p className="font-medium">${flight.price}</p>
              <Button size="sm">Select</Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function AccommodationResultCard({
  accommodation,
  view,
}: { accommodation: Accommodation; view: "list" | "grid" | "map" }) {
  return (
    <Card
      className={`overflow-hidden hover:bg-accent/50 transition-colors cursor-pointer ${view === "list" ? "flex" : ""}`}
    >
      <div
        className={`${view === "list" ? "w-1/3 bg-muted flex items-center justify-center" : "h-40 bg-muted flex items-center justify-center"}`}
      >
        <span className="text-muted-foreground">Image Placeholder</span>
      </div>
      <CardContent className={`p-4 ${view === "list" ? "flex-1" : ""}`}>
        {view === "list" ? (
          <div className="flex flex-col h-full">
            <div className="flex justify-between mb-2">
              <div>
                <p className="font-medium">{accommodation.name}</p>
                <p className="text-sm text-muted-foreground">
                  {accommodation.location}
                </p>
                <div className="flex items-center mt-1">
                  <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full mr-2">
                    {accommodation.rating} ★
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {accommodation.type}
                  </span>
                </div>
              </div>
              <div className="text-right">
                <p className="font-medium">${accommodation.pricePerNight}</p>
                <p className="text-xs text-muted-foreground">per night</p>
                <p className="text-sm font-medium mt-1">
                  ${accommodation.totalPrice}
                </p>
                <p className="text-xs text-muted-foreground">total</p>
              </div>
            </div>
            <div className="mt-2">
              <div className="flex flex-wrap gap-1 mb-2">
                {accommodation.amenities.slice(0, 3).map((amenity, index) => (
                  <span
                    key={index}
                    className="text-xs bg-muted px-2 py-0.5 rounded-full"
                  >
                    {amenity}
                  </span>
                ))}
                {accommodation.amenities.length > 3 && (
                  <span className="text-xs bg-muted px-2 py-0.5 rounded-full">
                    +{accommodation.amenities.length - 3} more
                  </span>
                )}
              </div>
            </div>
            <div className="mt-auto pt-2">
              <Button>View Details</Button>
            </div>
          </div>
        ) : (
          <>
            <div className="mb-2">
              <p className="font-medium">{accommodation.name}</p>
              <p className="text-sm text-muted-foreground">
                {accommodation.location}
              </p>
              <div className="flex items-center mt-1 mb-2">
                <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full mr-2">
                  {accommodation.rating} ★
                </span>
                <span className="text-xs text-muted-foreground">
                  {accommodation.type}
                </span>
              </div>
              <div className="flex flex-wrap gap-1 mb-2">
                {accommodation.amenities.slice(0, 2).map((amenity, index) => (
                  <span
                    key={index}
                    className="text-xs bg-muted px-2 py-0.5 rounded-full"
                  >
                    {amenity}
                  </span>
                ))}
                {accommodation.amenities.length > 2 && (
                  <span className="text-xs bg-muted px-2 py-0.5 rounded-full">
                    +{accommodation.amenities.length - 2} more
                  </span>
                )}
              </div>
            </div>
            <div className="flex justify-between items-center mt-2">
              <div>
                <p className="font-medium">${accommodation.pricePerNight}</p>
                <p className="text-xs text-muted-foreground">per night</p>
              </div>
              <Button size="sm">View</Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function ActivityResultCard({
  activity,
  view,
}: { activity: Activity; view: "list" | "grid" | "map" }) {
  return (
    <Card
      className={`overflow-hidden hover:bg-accent/50 transition-colors cursor-pointer ${view === "list" ? "flex" : ""}`}
    >
      <div
        className={`${view === "list" ? "w-1/3 bg-muted flex items-center justify-center" : "h-40 bg-muted flex items-center justify-center"}`}
      >
        <span className="text-muted-foreground">Image Placeholder</span>
      </div>
      <CardContent className={`p-4 ${view === "list" ? "flex-1" : ""}`}>
        {view === "list" ? (
          <div className="flex flex-col h-full">
            <div className="flex justify-between mb-2">
              <div>
                <p className="font-medium">{activity.name}</p>
                <p className="text-sm text-muted-foreground">
                  {activity.location}
                </p>
                <div className="flex items-center mt-1">
                  <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full mr-2">
                    {activity.rating} ★
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {activity.type}
                  </span>
                </div>
              </div>
              <div className="text-right">
                <p className="font-medium">${activity.price}</p>
                <p className="text-xs text-muted-foreground">per person</p>
              </div>
            </div>
            <div className="mt-2">
              <p className="text-sm line-clamp-2">{activity.description}</p>
              <p className="text-xs text-muted-foreground mt-1">
                Duration: {Math.floor(activity.duration / 60)}h{" "}
                {activity.duration % 60}m
              </p>
            </div>
            <div className="mt-auto pt-2">
              <Button>View Details</Button>
            </div>
          </div>
        ) : (
          <>
            <div className="mb-2">
              <p className="font-medium">{activity.name}</p>
              <p className="text-sm text-muted-foreground">
                {activity.location}
              </p>
              <div className="flex items-center mt-1 mb-2">
                <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full mr-2">
                  {activity.rating} ★
                </span>
                <span className="text-xs text-muted-foreground">
                  {activity.type}
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                Duration: {Math.floor(activity.duration / 60)}h{" "}
                {activity.duration % 60}m
              </p>
            </div>
            <div className="flex justify-between items-center mt-2">
              <p className="font-medium">${activity.price}</p>
              <Button size="sm">View</Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
