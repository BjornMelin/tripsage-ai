/**
 * @fileoverview Client-side unified search experience (renders within RSC shell).
 */

"use client";

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
import {
  type FlightResult,
  type FlightSearchFormData,
  type HotelResult,
  type HotelSearchFormData,
} from "@schemas/search";
import { type ReactNode, useState, useTransition } from "react";
import { FlightResults } from "@/components/features/search/flight-results";
import { FlightSearchForm } from "@/components/features/search/flight-search-form";
import { HotelResults } from "@/components/features/search/hotel-results";
import { HotelSearchForm } from "@/components/features/search/hotel-search-form";
import { SearchLayout } from "@/components/layouts/search-layout";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { getErrorMessage } from "@/lib/api/error-types";

// Mock data for demo purposes
const MOCK_FLIGHT_RESULTS: FlightResult[] = [
  {
    aircraft: "Boeing 787",
    airline: "Delta Airlines",
    amenities: ["wifi", "meals", "entertainment"],
    arrival: { date: "2025-06-15", time: "10:45 PM" },
    departure: { date: "2025-06-15", time: "10:30 AM" },
    destination: { city: "London", code: "LHR", terminal: "3" },
    duration: 420,
    emissions: { compared: "low" as const, kg: 850 },
    flexibility: { changeable: true, cost: 50, refundable: false },
    flightNumber: "DL 128",
    id: "flight-1",
    origin: { city: "New York", code: "JFK", terminal: "4" },
    prediction: {
      confidence: 89,
      priceAlert: "buy_now" as const,
      reason: "Prices trending up for this route",
    },
    price: {
      base: 599,
      currency: "USD",
      dealScore: 9,
      priceChange: "down" as const,
      total: 699,
    },
    promotions: {
      description: "Flash Deal - 24hrs only",
      savings: 150,
      type: "flash_deal" as const,
    },
    stops: { cities: [], count: 0 },
  },
  {
    aircraft: "Airbus A350",
    airline: "United Airlines",
    amenities: ["wifi", "entertainment"],
    arrival: { date: "2025-06-16", time: "1:35 AM" },
    departure: { date: "2025-06-15", time: "1:15 PM" },
    destination: { city: "London", code: "LHR", terminal: "2" },
    duration: 440,
    emissions: { compared: "average" as const, kg: 920 },
    flexibility: { changeable: true, cost: 0, refundable: true },
    flightNumber: "UA 901",
    id: "flight-2",
    origin: { city: "New York", code: "JFK", terminal: "7" },
    prediction: {
      confidence: 72,
      priceAlert: "neutral" as const,
      reason: "Stable pricing expected",
    },
    price: {
      base: 649,
      currency: "USD",
      dealScore: 7,
      priceChange: "stable" as const,
      total: 749,
    },
    stops: { cities: [], count: 0 },
  },
];

const MOCK_HOTEL_RESULTS: HotelResult[] = [
  {
    ai: {
      personalizedTags: ["luxury", "city-center", "business"],
      reason: "Perfect for luxury seekers with prime location",
      recommendation: 9,
    },
    allInclusive: {
      available: false,
      inclusions: [],
      tier: "basic" as const,
    },
    amenities: {
      essential: ["wifi", "breakfast", "gym", "spa"],
      premium: ["concierge", "butler"],
      unique: ["central-park-view"],
    },
    availability: {
      flexible: true,
      roomsLeft: 3,
      urgency: "high" as const,
    },
    brand: "Ritz-Carlton",
    category: "hotel" as const,
    guestExperience: {
      highlights: ["Exceptional service with Central Park views"],
      recentMentions: ["Outstanding breakfast", "Perfect location"],
      vibe: "luxury" as const,
    },
    id: "hotel-1",
    images: {
      count: 24,
      gallery: [],
      main: "/hotel-1.jpg",
    },
    location: {
      address: "50 Central Park South",
      city: "New York",
      district: "Midtown",
      landmarks: ["Central Park", "Times Square"],
      walkScore: 95,
    },
    name: "The Ritz-Carlton New York",
    pricing: {
      basePrice: 450,
      currency: "USD",
      deals: {
        description: "Early Bird - Book 30 days ahead",
        originalPrice: 525,
        savings: 75,
        type: "early_bird" as const,
      },
      priceHistory: "falling" as const,
      pricePerNight: 450,
      taxes: 85,
      totalPrice: 1350,
    },
    reviewCount: 2847,
    starRating: 5,
    sustainability: {
      certified: true,
      practices: ["solar-power", "recycling", "local-sourcing"],
      score: 8,
    },
    userRating: 4.8,
  },
  {
    ai: {
      personalizedTags: ["budget", "city-center", "modern"],
      reason: "Great value in prime location for business travelers",
      recommendation: 7,
    },
    allInclusive: {
      available: false,
      inclusions: [],
      tier: "basic" as const,
    },
    amenities: {
      essential: ["wifi", "gym"],
      premium: [],
      unique: ["pod-design", "rooftop-bar"],
    },
    availability: {
      flexible: true,
      roomsLeft: 12,
      urgency: "low" as const,
    },
    brand: "Pod Hotels",
    category: "hotel" as const,
    guestExperience: {
      highlights: ["Modern pod-style rooms in heart of Times Square"],
      recentMentions: ["Great location", "Clean and efficient"],
      vibe: "business" as const,
    },
    id: "hotel-2",
    images: {
      count: 18,
      gallery: [],
      main: "/hotel-2.jpg",
    },
    location: {
      address: "400 W 42nd St",
      city: "New York",
      district: "Times Square",
      landmarks: ["Times Square", "Broadway"],
      walkScore: 100,
    },
    name: "Pod Hotels Times Square",
    pricing: {
      basePrice: 189,
      currency: "USD",
      priceHistory: "rising" as const,
      pricePerNight: 189,
      taxes: 35,
      totalPrice: 567,
    },
    reviewCount: 1893,
    starRating: 3,
    sustainability: {
      certified: false,
      practices: ["energy-efficient"],
      score: 6,
    },
    userRating: 4.2,
  },
];

interface UnifiedSearchClientProps {
  onSearchHotels: (params: HotelSearchFormData) => Promise<HotelResult[]>;
}

export default function UnifiedSearchClient({
  onSearchHotels,
}: UnifiedSearchClientProps) {
  const [isPending, startTransition] = useTransition();
  const [activeTab, setActiveTab] = useState<"flights" | "hotels">("flights");
  const [showResults, setShowResults] = useState(false);
  const [_searchData, setSearchData] = useState<Record<string, unknown> | null>(null);
  const [hotelResults, setHotelResults] = useState<HotelResult[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { toast } = useToast();

  const handleFlightSearch = async (params: FlightSearchFormData) => {
    await new Promise<void>((resolve) => {
      startTransition(() => {
        setSearchData(params as unknown as Record<string, unknown>);
        setShowResults(true);
        // Simulate API call
        setTimeout(() => {
          setShowResults(true);
          resolve();
        }, 1500);
      });
    });
  };

  const handleHotelSearch = (params: HotelSearchFormData) =>
    new Promise<void>((resolve) => {
      startTransition(async () => {
        setSearchData(params as unknown as Record<string, unknown>);
        setErrorMessage(null);
        try {
          const results = await onSearchHotels(params);
          setHotelResults(results);
          setShowResults(true);
          setErrorMessage(null);
        } catch (error) {
          setHotelResults([]);
          setShowResults(true);
          const message = getErrorMessage(error) || "Search failed, please try again.";
          setErrorMessage(message);
          toast({
            description: message,
            title: "Search Failed",
            variant: "destructive",
          });
        } finally {
          resolve();
        }
      });
    });

  const handleFlightSelect = async (_flight: FlightResult) => {
    await Promise.resolve();
  };

  const handleHotelSelect = async (_hotel: HotelResult) => {
    await Promise.resolve();
  };

  const handleCompareFlights = (_flights: FlightResult[]) => {
    // Handle flight comparison
  };

  const handleSaveToWishlist = (_hotelId: string) => {
    // Handle wishlist save
  };

  return (
    <SearchLayout>
      <div className="space-y-6">
        {/* Hero Section */}
        <Card className="bg-linear-to-r from-blue-50 to-green-50 border-none">
          <CardContent className="p-8">
            <div className="text-center space-y-4">
              <h1 className="text-3xl font-bold">Unified Search Experience</h1>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Experience the future of travel search with AI-powered recommendations,
                real-time price tracking, and optimistic UI updates.
              </p>
              <div className="flex items-center justify-center gap-4 text-sm">
                <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                  <ZapIcon className="h-3 w-3 mr-1" />
                  React 19 Patterns
                </Badge>
                <Badge variant="secondary" className="bg-green-100 text-green-800">
                  <SparklesIcon className="h-3 w-3 mr-1" />
                  AI Recommendations
                </Badge>
                <Badge variant="secondary" className="bg-purple-100 text-purple-800">
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
                      Updated {new Date().toLocaleTimeString()}
                    </Badge>
                  </div>
                  <FlightResults
                    results={MOCK_FLIGHT_RESULTS}
                    loading={isPending}
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
                      Updated {new Date().toLocaleTimeString()}
                    </Badge>
                  </div>
                  <HotelResults
                    results={hotelResults.length ? hotelResults : MOCK_HOTEL_RESULTS}
                    loading={isPending}
                    onSelect={handleHotelSelect}
                    onSaveToWishlist={handleSaveToWishlist}
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
                icon={<ZapIcon className="h-6 w-6 text-yellow-500" />}
                title="React 19 Optimistic Updates"
                description="Instant UI feedback with useOptimistic and useTransition hooks"
              />
              <FeatureCard
                icon={<TrendingUpIcon className="h-6 w-6 text-green-500" />}
                title="AI Price Predictions"
                description="Smart recommendations with confidence scores and timing advice"
              />
              <FeatureCard
                icon={<StarIcon className="h-6 w-6 text-blue-500" />}
                title="Personalized Rankings"
                description="AI-powered hotel and flight scoring based on your preferences"
              />
              <FeatureCard
                icon={<UsersIcon className="h-6 w-6 text-purple-500" />}
                title="Smart Bundles"
                description="Dynamic package deals with real savings calculations"
              />
              <FeatureCard
                icon={<MapPinIcon className="h-6 w-6 text-red-500" />}
                title="Location Intelligence"
                description="Walk scores, landmark distances, and neighborhood insights"
              />
              <FeatureCard
                icon={<ShieldIcon className="h-6 w-6 text-orange-500" />}
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
                  <li>• useTransition() for non-blocking state updates</li>
                  <li>• useOptimistic() for instant UI feedback</li>
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
