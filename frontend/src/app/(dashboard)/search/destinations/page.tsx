"use client";

import { DestinationCard } from "@/components/features/search/destination-card";
import { DestinationSearchForm } from "@/components/features/search/destination-search-form";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { useDestinationSearch } from "@/hooks/use-destination-search";
import { useSearchStore } from "@/stores/search-store";
import type { Destination, DestinationSearchParams } from "@/types/search";
import { AlertCircle, MapPin, Search, Star } from "lucide-react";
import { useEffect, useState } from "react";

export default function DestinationsSearchPage() {
  const { hasResults, isSearching: storeIsSearching } = useSearchStore();
  const { searchDestinationsMock, isSearching, searchError, resetSearch } =
    useDestinationSearch();

  const [selectedDestinations, setSelectedDestinations] = useState<Destination[]>([]);
  const [showComparisonModal, setShowComparisonModal] = useState(false);

  const handleSearch = async (params: DestinationSearchParams) => {
    try {
      await searchDestinationsMock(params);
    } catch (error) {
      console.error("Search failed:", error);
    }
  };

  const handleDestinationSelect = (destination: Destination) => {
    console.log("Selected destination:", destination);
    // Here you could navigate to a detailed view or booking flow
    alert(`Selected: ${destination.name}`);
  };

  const handleDestinationCompare = (destination: Destination) => {
    setSelectedDestinations((prev) => {
      const isAlreadySelected = prev.some((d) => d.id === destination.id);
      if (isAlreadySelected) {
        return prev.filter((d) => d.id !== destination.id);
      } else if (prev.length < 3) {
        return [...prev, destination];
      } else {
        alert("You can compare up to 3 destinations at once");
        return prev;
      }
    });
  };

  const handleViewDetails = (destination: Destination) => {
    console.log("View details for:", destination);
    // Here you could open a modal or navigate to details page
    alert(`View details for: ${destination.name}`);
  };

  const clearComparison = () => {
    setSelectedDestinations([]);
  };

  // For now, use mock data since we're focusing on UI testing
  const destinations: Destination[] = [];
  const hasActiveResults = hasResults;
  const hasSearched = false;

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold mb-2">Destination Search</h1>
        <p className="text-muted-foreground">
          Discover amazing destinations around the world with intelligent search and
          autocomplete
        </p>
      </div>

      {/* Search Form */}
      <DestinationSearchForm onSearch={handleSearch} />

      {/* Comparison Bar */}
      {selectedDestinations.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">
                Compare Destinations ({selectedDestinations.length}/3)
              </CardTitle>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowComparisonModal(true)}
                  disabled={selectedDestinations.length < 2}
                >
                  Compare
                </Button>
                <Button variant="outline" size="sm" onClick={clearComparison}>
                  Clear
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {selectedDestinations.map((destination) => (
                <Badge
                  key={destination.id}
                  variant="secondary"
                  className="cursor-pointer"
                  onClick={() => handleDestinationCompare(destination)}
                >
                  {destination.name} ✕
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading State */}
      {(storeIsSearching || isSearching) && (
        <div className="flex items-center justify-center py-12">
          <LoadingSpinner />
          <span className="ml-2">Searching destinations...</span>
        </div>
      )}

      {/* Error State */}
      {searchError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{searchError?.message}</span>
            <Button variant="outline" size="sm" onClick={resetSearch}>
              Try Again
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* No Results State */}
      {!storeIsSearching &&
        !isSearching &&
        hasSearched &&
        !hasActiveResults &&
        !searchError && (
          <Card>
            <CardContent className="text-center py-12">
              <Search className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">No destinations found</h3>
              <p className="text-muted-foreground mb-4">
                Try adjusting your search terms or destination types
              </p>
              <Button variant="outline" onClick={() => resetSearch()}>
                Clear Search
              </Button>
            </CardContent>
          </Card>
        )}

      {/* Results */}
      {!storeIsSearching && !isSearching && hasActiveResults && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">
              Search Results ({destinations.length} destinations)
            </h2>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <MapPin className="h-4 w-4" />
              <span>Click to compare destinations</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {destinations.map((destination) => (
              <DestinationCard
                key={destination.id}
                destination={destination}
                onSelect={handleDestinationSelect}
                onCompare={handleDestinationCompare}
                onViewDetails={handleViewDetails}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty State - Before Search */}
      {!hasSearched && !storeIsSearching && !isSearching && (
        <Card>
          <CardContent className="text-center py-12">
            <MapPin className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">
              Discover Amazing Destinations
            </h3>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              Search for cities, countries, landmarks, or regions to find your next
              travel destination. Use our smart autocomplete to get suggestions as you
              type.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl mx-auto">
              <div className="text-center">
                <div className="bg-primary/10 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-2">
                  <MapPin className="h-6 w-6 text-primary" />
                </div>
                <div className="text-sm font-medium">Cities & Towns</div>
              </div>
              <div className="text-center">
                <div className="bg-primary/10 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-2">
                  <Star className="h-6 w-6 text-primary" />
                </div>
                <div className="text-sm font-medium">Landmarks</div>
              </div>
              <div className="text-center">
                <div className="bg-primary/10 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-2">
                  <MapPin className="h-6 w-6 text-primary" />
                </div>
                <div className="text-sm font-medium">Countries</div>
              </div>
              <div className="text-center">
                <div className="bg-primary/10 rounded-full w-12 h-12 flex items-center justify-center mx-auto mb-2">
                  <MapPin className="h-6 w-6 text-primary" />
                </div>
                <div className="text-sm font-medium">Regions</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Comparison Modal Placeholder */}
      {showComparisonModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-4xl mx-4 max-h-[90vh] overflow-auto">
            <CardHeader>
              <CardTitle>Destination Comparison</CardTitle>
              <CardDescription>
                Compare key features of your selected destinations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {selectedDestinations.map((destination) => (
                  <div key={destination.id} className="border rounded-lg p-4">
                    <h3 className="font-semibold mb-2">{destination.name}</h3>
                    <div className="space-y-2 text-sm">
                      <div>
                        Rating: {destination.rating ? `${destination.rating}/5` : "N/A"}
                      </div>
                      <div>Country: {destination.country || "N/A"}</div>
                      <div>
                        Best Time:{" "}
                        {destination.bestTimeToVisit?.slice(0, 3).join(", ") ||
                          "Year-round"}
                      </div>
                      {destination.climate && (
                        <div>Avg Temp: {destination.climate.averageTemp}°C</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex justify-end gap-2 mt-6">
                <Button variant="outline" onClick={() => setShowComparisonModal(false)}>
                  Close
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
