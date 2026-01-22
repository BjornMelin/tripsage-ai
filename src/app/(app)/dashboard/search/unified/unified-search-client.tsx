/**
 * @fileoverview Client-side unified search experience (renders within RSC shell).
 */

"use client";

import type {
  FlightResult,
  FlightSearchFormData,
  HotelResult,
  HotelSearchFormData,
} from "@schemas/search";
import { formatDistanceToNow } from "date-fns";
import {
  Building2Icon,
  ClockIcon,
  MapPinIcon,
  PlaneIcon,
  ShieldIcon,
  SparklesIcon,
  StarIcon,
  TrendingUpIcon,
  UsersIcon,
  ZapIcon,
} from "lucide-react";
import Link from "next/link";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { SearchLayout } from "@/components/layouts/search-layout";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { FlightSearchForm } from "@/features/search/components/forms/flight-search-form";
import { HotelSearchForm } from "@/features/search/components/forms/hotel-search-form";
import { FlightResults } from "@/features/search/components/results/flight-results";
import { HotelResults } from "@/features/search/components/results/hotel-results";
import { getErrorMessage } from "@/lib/api/error-types";
import type { Result, ResultError } from "@/lib/result";
import { ROUTES } from "@/lib/routes";
import { statusVariants } from "@/lib/variants/status";

interface UnifiedSearchClientProps {
  onSearchFlights?: (
    params: FlightSearchFormData,
    signal?: AbortSignal
  ) => Promise<FlightResult[]>;
  onSearchHotels: (
    params: HotelSearchFormData,
    signal?: AbortSignal
  ) => Promise<Result<HotelResult[], ResultError>>;
}

export default function UnifiedSearchClient({
  onSearchFlights,
  onSearchHotels,
}: UnifiedSearchClientProps) {
  const [isSearching, setIsSearching] = useState(false);
  const [activeTab, setActiveTab] = useState<"flights" | "hotels">("flights");
  const [showResults, setShowResults] = useState(false);
  const [flightResults, setFlightResults] = useState<FlightResult[]>([]);
  const [hotelResults, setHotelResults] = useState<HotelResult[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [selectedFlight, setSelectedFlight] = useState<FlightResult | null>(null);
  const [selectedHotel, setSelectedHotel] = useState<HotelResult | null>(null);
  const [comparisonFlights, setComparisonFlights] = useState<FlightResult[]>([]);
  const [isComparisonOpen, setIsComparisonOpen] = useState(false);
  const [wishlistHotelIds, setWishlistHotelIds] = useState<Set<string>>(new Set());
  const { toast } = useToast();
  const currentSearchController = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      currentSearchController.current?.abort();
      currentSearchController.current = null;
    };
  }, []);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem("unifiedSearch:wishlistHotels");
      if (!stored) return;
      const parsed: unknown = JSON.parse(stored);
      if (Array.isArray(parsed) && parsed.every((value) => typeof value === "string")) {
        setWishlistHotelIds(new Set(parsed));
      }
    } catch {
      // ignore
    }
  }, []);

  const isAbortError = (error: unknown): boolean =>
    error instanceof Error && error.name === "AbortError";

  const handleFlightSearch = async (params: FlightSearchFormData): Promise<void> => {
    currentSearchController.current?.abort();
    const controller = new AbortController();
    currentSearchController.current = controller;
    setIsSearching(true);
    setErrorMessage(null);
    try {
      if (!onSearchFlights) {
        throw new Error("Flight search is not implemented yet.");
      }
      const results = await onSearchFlights(params, controller.signal);
      setFlightResults(results);
      setLastUpdated(new Date());
      setShowResults(true);
    } catch (error) {
      if (isAbortError(error)) {
        return;
      }
      const message =
        getErrorMessage(error) || "Unable to fetch flights. Please try again.";
      setFlightResults([]);
      setLastUpdated(null);
      setShowResults(false);
      setErrorMessage(message);
      toast({
        description: message,
        title: "Search error",
        variant: "destructive",
      });
    } finally {
      if (currentSearchController.current === controller) {
        currentSearchController.current = null;
        setIsSearching(false);
      }
    }
  };

  const handleLoadDemoResults = async () => {
    if (process.env.NODE_ENV !== "development") return;
    const mocks = await import("@/mocks/unified-search-mocks");
    setFlightResults(mocks.MOCK_FLIGHT_RESULTS.map((result) => ({ ...result })));
    setHotelResults(mocks.MOCK_HOTEL_RESULTS.map((result) => ({ ...result })));
    setErrorMessage(null);
    setLastUpdated(new Date());
    setShowResults(true);
  };

  const handleHotelSearch = async (params: HotelSearchFormData): Promise<void> => {
    currentSearchController.current?.abort();
    const controller = new AbortController();
    currentSearchController.current = controller;
    setIsSearching(true);
    setErrorMessage(null);
    try {
      const results = await onSearchHotels(params, controller.signal);
      if (!results.ok) {
        setHotelResults([]);
        setLastUpdated(null);
        setShowResults(false);
        const message = results.error.reason || "Search failed, please try again.";
        setErrorMessage(message);
        toast({
          description: message,
          title: "Search Failed",
          variant: "destructive",
        });
        return;
      }

      setHotelResults(results.data);
      setLastUpdated(new Date());
      setShowResults(true);
    } catch (error) {
      if (isAbortError(error)) {
        return;
      }
      setHotelResults([]);
      setLastUpdated(null);
      setShowResults(false);
      const message = getErrorMessage(error) || "Search failed, please try again.";
      setErrorMessage(message);
      toast({
        description: message,
        title: "Search Failed",
        variant: "destructive",
      });
    } finally {
      if (currentSearchController.current === controller) {
        currentSearchController.current = null;
        setIsSearching(false);
      }
    }
  };

  const handleFlightSelect = (flight: FlightResult): void => {
    setSelectedFlight(flight);
    toast({
      description: `${flight.airline} • ${flight.origin.code} → ${flight.destination.code}`,
      title: "Flight selected",
    });
  };

  const handleHotelSelect = (hotel: HotelResult): void => {
    setSelectedHotel(hotel);
    toast({
      description: hotel.location.city
        ? `${hotel.name} • ${hotel.location.city}`
        : hotel.name,
      title: "Hotel selected",
    });
  };

  const handleCompareFlights = (flights: FlightResult[]) => {
    setComparisonFlights(flights);
    setIsComparisonOpen(true);
  };

  const handleSaveToWishlist = (hotelId: string) => {
    let isNowSaved = false;
    setWishlistHotelIds((prev) => {
      const next = new Set(prev);
      if (next.has(hotelId)) {
        next.delete(hotelId);
        isNowSaved = false;
      } else {
        next.add(hotelId);
        isNowSaved = true;
      }
      try {
        window.localStorage.setItem(
          "unifiedSearch:wishlistHotels",
          JSON.stringify([...next])
        );
      } catch {
        // ignore
      }
      return next;
    });
    toast({
      description: isNowSaved ? "Saved to wishlist" : "Removed from wishlist",
      title: "Wishlist updated",
    });
  };

  return (
    <SearchLayout>
      <div className="space-y-6">
        <Dialog
          open={selectedFlight !== null}
          onOpenChange={(open) => !open && setSelectedFlight(null)}
        >
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Flight details</DialogTitle>
              <DialogDescription>
                {selectedFlight
                  ? `${selectedFlight.airline} • ${selectedFlight.flightNumber}`
                  : null}
              </DialogDescription>
            </DialogHeader>
            {selectedFlight ? (
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Route</span>
                  <span className="font-medium">
                    {selectedFlight.origin.code} → {selectedFlight.destination.code}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Departure</span>
                  <span className="font-medium">
                    {selectedFlight.departure.date} {selectedFlight.departure.time}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Arrival</span>
                  <span className="font-medium">
                    {selectedFlight.arrival.date} {selectedFlight.arrival.time}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Price</span>
                  <span className="font-medium">
                    {selectedFlight.price.currency}{" "}
                    {selectedFlight.price.total.toFixed(2)}
                  </span>
                </div>
                <div className="pt-2 flex justify-end">
                  <Button type="button" variant="outline" asChild>
                    <Link href={`${ROUTES.dashboard.search}/flights`}>
                      Open flight search
                    </Link>
                  </Button>
                </div>
              </div>
            ) : null}
          </DialogContent>
        </Dialog>

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
                <div className="pt-2 flex justify-end">
                  <Button type="button" variant="outline" asChild>
                    <Link href={`${ROUTES.dashboard.search}/hotels`}>
                      Open hotel search
                    </Link>
                  </Button>
                </div>
              </div>
            ) : null}
          </DialogContent>
        </Dialog>

        <Dialog open={isComparisonOpen} onOpenChange={setIsComparisonOpen}>
          <DialogContent className="max-w-4xl">
            <DialogHeader>
              <DialogTitle>Compare flights</DialogTitle>
              <DialogDescription>
                {comparisonFlights.length > 0
                  ? `Comparing ${comparisonFlights.length} flights`
                  : "Select flights to compare"}
              </DialogDescription>
            </DialogHeader>
            {comparisonFlights.length > 0 ? (
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {comparisonFlights.map((flight) => (
                  <Card key={flight.id}>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-base">{flight.airline}</CardTitle>
                    </CardHeader>
                    <CardContent className="text-sm space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Route</span>
                        <span className="font-medium">
                          {flight.origin.code} → {flight.destination.code}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Stops</span>
                        <span className="font-medium">{flight.stops.count}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Price</span>
                        <span className="font-medium">
                          {flight.price.currency} {flight.price.total.toFixed(2)}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : null}
          </DialogContent>
        </Dialog>

        {/* Hero Section */}
        <Card className="bg-linear-to-r from-info/10 to-success/10 border-none">
          <CardContent className="p-8">
            <div className="text-center space-y-4">
              <h1 className="text-3xl font-bold">Unified Search Experience</h1>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Experience the future of travel search with AI-powered recommendations,
                real-time price tracking, and optimistic UI updates.
              </p>
              <div className="flex items-center justify-center gap-4 text-sm">
                <Badge className={statusVariants({ status: "info" })}>
                  <ZapIcon className="h-3 w-3 mr-1" />
                  React 19 Patterns
                </Badge>
                <Badge className={statusVariants({ status: "active" })}>
                  <SparklesIcon className="h-3 w-3 mr-1" />
                  AI Recommendations
                </Badge>
                <Badge className={statusVariants({ action: "explore" })}>
                  <TrendingUpIcon className="h-3 w-3 mr-1" />
                  2025 UX Patterns
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {errorMessage ? (
          <Alert variant="destructive" role="status">
            <AlertTitle>Search error</AlertTitle>
            <AlertDescription>{errorMessage}</AlertDescription>
          </Alert>
        ) : null}

        {process.env.NODE_ENV === "development" ? (
          <div className="flex justify-center">
            <Button
              type="button"
              variant="outline"
              onClick={handleLoadDemoResults}
              disabled={isSearching}
            >
              Load Demo Results
            </Button>
          </div>
        ) : null}

        {/* Search Interface */}
        <Tabs
          value={activeTab}
          onValueChange={(value) => setActiveTab(value as "flights" | "hotels")}
        >
          <TabsList className="grid w-full grid-cols-2 max-w-md mx-auto">
            <TabsTrigger value="flights" className="flex items-center gap-2">
              <PlaneIcon className="h-4 w-4" />
              Flights
            </TabsTrigger>
            <TabsTrigger value="hotels" className="flex items-center gap-2">
              <Building2Icon className="h-4 w-4" />
              Hotels
            </TabsTrigger>
          </TabsList>

          <div className="mt-6">
            <TabsContent value="flights" className="space-y-6">
              <FlightSearchForm onSearch={handleFlightSearch} showSmartBundles={true} />

              {activeTab === "flights" && showResults && (
                <div className="space-y-4">
                  <Separator />
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold">Flight Results</h2>
                    <Badge variant="outline">
                      <ClockIcon className="h-3 w-3 mr-1" />
                      Updated{" "}
                      {lastUpdated
                        ? formatDistanceToNow(lastUpdated, { addSuffix: true })
                        : "just now"}
                    </Badge>
                  </div>
                  <FlightResults
                    results={flightResults}
                    loading={isSearching}
                    onSelect={handleFlightSelect}
                    onCompare={handleCompareFlights}
                  />
                </div>
              )}
            </TabsContent>

            <TabsContent value="hotels" className="space-y-6">
              <HotelSearchForm
                onSearch={handleHotelSearch}
                showRecommendations={true}
              />

              {activeTab === "hotels" && showResults && (
                <div className="space-y-4">
                  <Separator />
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-semibold">Hotel Results</h2>
                    <Badge variant="outline">
                      <ClockIcon className="h-3 w-3 mr-1" />
                      Updated{" "}
                      {lastUpdated
                        ? formatDistanceToNow(lastUpdated, { addSuffix: true })
                        : "just now"}
                    </Badge>
                  </div>
                  <HotelResults
                    results={hotelResults}
                    loading={isSearching}
                    onSelect={handleHotelSelect}
                    onSaveToWishlist={handleSaveToWishlist}
                    wishlistHotelIds={wishlistHotelIds}
                    showMap
                  />
                </div>
              )}
            </TabsContent>
          </div>
        </Tabs>

        {/* Features Showcase */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <SparklesIcon className="h-5 w-5" />
              Features Showcase
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              <FeatureCard
                icon={<ZapIcon className="h-6 w-6 text-warning" />}
                title="React 19 Optimistic Updates"
                description="Instant UI feedback with optimistic UI patterns"
              />
              <FeatureCard
                icon={<TrendingUpIcon className="h-6 w-6 text-success" />}
                title="AI Price Predictions"
                description="Smart recommendations with confidence scores and timing advice"
              />
              <FeatureCard
                icon={<StarIcon className="h-6 w-6 text-info" />}
                title="Personalized Rankings"
                description="AI-powered hotel and flight scoring based on your preferences"
              />
              <FeatureCard
                icon={<UsersIcon className="h-6 w-6 text-highlight" />}
                title="Smart Bundles"
                description="Dynamic package deals with real savings calculations"
              />
              <FeatureCard
                icon={<MapPinIcon className="h-6 w-6 text-destructive" />}
                title="Location Intelligence"
                description="Walk scores, landmark distances, and neighborhood insights"
              />
              <FeatureCard
                icon={<ShieldIcon className="h-6 w-6 text-warning" />}
                title="Price Protection"
                description="Free cancellation and price matching guarantees"
              />
            </div>
          </CardContent>
        </Card>

        {/* Implementation Notes */}
        <Card className="bg-muted/50">
          <CardHeader>
            <CardTitle>Implementation Highlights</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-semibold mb-2">React 19 Features Used:</h4>
                <ul className="text-sm space-y-1 text-muted-foreground">
                  <li>• Concurrent rendering for smooth interactions</li>
                  <li>• Server Components with streaming SSR</li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold mb-2">2025 UX Patterns:</h4>
                <ul className="text-sm space-y-1 text-muted-foreground">
                  <li>• Smart Bundle savings (Amadeus hybrid pattern)</li>
                  <li>• All-Inclusive Era highlighting</li>
                  <li>• AI price prediction with confidence</li>
                  <li>• Progressive disclosure for complexity</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </SearchLayout>
  );
}

interface FeatureCardProps {
  icon: ReactNode;
  title: string;
  description: string;
}

/**
 * Feature card highlighting unified experience capabilities.
 */
function FeatureCard({ icon, title, description }: FeatureCardProps) {
  return (
    <div className="p-4 border rounded-lg space-y-3">
      <div className="flex items-center gap-3">
        {icon}
        <h3 className="font-medium">{title}</h3>
      </div>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
