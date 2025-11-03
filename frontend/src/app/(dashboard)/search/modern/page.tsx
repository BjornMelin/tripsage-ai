"use client";

import {
  Building2,
  Calendar,
  Clock,
  MapPin,
  Plane,
  Sparkles,
  Star,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";
import { useState, useTransition } from "react";
import type { ModernFlightSearchParams } from "@/components/features/search/flight-search-form";
import { FlightSearchForm } from "@/components/features/search/flight-search-form";
import type { ModernHotelSearchParams } from "@/components/features/search/hotel-search-form";
import { HotelSearchForm } from "@/components/features/search/hotel-search-form";
// Import the types from their source files
import type { ModernFlightResult } from "@/components/features/search/modern-flight-results";
import { ModernFlightResults } from "@/components/features/search/modern-flight-results";
import type { ModernHotelResult } from "@/components/features/search/modern-hotel-results";
import { ModernHotelResults } from "@/components/features/search/modern-hotel-results";
import { SearchLayout } from "@/components/layouts/search-layout";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

// Mock data uses the Modern types directly

// Mock data for demo purposes
const MOCK_FLIGHT_RESULTS = [
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
] as ModernFlightResult[];

const MOCK_HOTEL_RESULTS = [
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
] as ModernHotelResult[];

export default function ModernSearchPage() {
  const [isPending, startTransition] = useTransition();
  const [activeTab, setActiveTab] = useState<"flights" | "hotels">("flights");
  const [showResults, setShowResults] = useState(false);
  const [_searchData, setSearchData] = useState<Record<string, unknown> | null>(null);

  const handleFlightSearch = async (params: ModernFlightSearchParams) => {
    startTransition(() => {
      setSearchData(params as unknown as Record<string, unknown>);
      setShowResults(true);
      // Simulate API call
      setTimeout(() => {
        setShowResults(true);
      }, 1500);
    });
  };

  const handleHotelSearch = async (params: ModernHotelSearchParams) => {
    startTransition(() => {
      setSearchData(params as unknown as Record<string, unknown>);
      setShowResults(true);
      // Simulate API call
      setTimeout(() => {
        setShowResults(true);
      }, 1500);
    });
  };

  const handleFlightSelect = async (flight: ModernFlightResult) => {
    console.log("Selected flight:", flight);
    // Handle flight selection
  };

  const handleHotelSelect = async (hotel: ModernHotelResult) => {
    console.log("Selected hotel:", hotel);
    // Handle hotel selection
  };

  const handleCompareFlights = (flights: ModernFlightResult[]) => {
    console.log("Comparing flights:", flights);
    // Handle flight comparison
  };

  const handleSaveToWishlist = (hotelId: string) => {
    console.log("Saved to wishlist:", hotelId);
    // Handle wishlist save
  };

  return (
    <SearchLayout>
      <div className="space-y-6">
        {/* Hero Section */}
        <Card className="bg-linear-to-r from-blue-50 to-green-50 border-none">
          <CardContent className="p-8">
            <div className="text-center space-y-4">
              <h1 className="text-3xl font-bold">Modern Search Experience</h1>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Experience the future of travel search with AI-powered recommendations,
                real-time price tracking, and optimistic UI updates.
              </p>
              <div className="flex items-center justify-center gap-4 text-sm">
                <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                  <Zap className="h-3 w-3 mr-1" />
                  React 19 Patterns
                </Badge>
                <Badge variant="secondary" className="bg-green-100 text-green-800">
                  <Sparkles className="h-3 w-3 mr-1" />
                  AI Recommendations
                </Badge>
                <Badge variant="secondary" className="bg-purple-100 text-purple-800">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  2025 UX Patterns
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Search Interface */}
        <Tabs
          value={activeTab}
          onValueChange={(value) => setActiveTab(value as "flights" | "hotels")}
        >
          <TabsList className="grid w-full grid-cols-2 max-w-md mx-auto">
            <TabsTrigger value="flights" className="flex items-center gap-2">
              <Plane className="h-4 w-4" />
              Flights
            </TabsTrigger>
            <TabsTrigger value="hotels" className="flex items-center gap-2">
              <Building2 className="h-4 w-4" />
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
                      <Clock className="h-3 w-3 mr-1" />
                      Updated {new Date().toLocaleTimeString()}
                    </Badge>
                  </div>
                  <ModernFlightResults
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
                      <Clock className="h-3 w-3 mr-1" />
                      Updated {new Date().toLocaleTimeString()}
                    </Badge>
                  </div>
                  <ModernHotelResults
                    results={MOCK_HOTEL_RESULTS}
                    loading={isPending}
                    onSelect={handleHotelSelect}
                    onSaveToWishlist={handleSaveToWishlist}
                    showMap={true}
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
              <Sparkles className="h-5 w-5" />
              Modern Features Showcase
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              <FeatureCard
                icon={<Zap className="h-6 w-6 text-yellow-500" />}
                title="React 19 Optimistic Updates"
                description="Instant UI feedback with useOptimistic and useTransition hooks"
              />
              <FeatureCard
                icon={<TrendingUp className="h-6 w-6 text-green-500" />}
                title="AI Price Predictions"
                description="Smart recommendations with confidence scores and timing advice"
              />
              <FeatureCard
                icon={<Star className="h-6 w-6 text-blue-500" />}
                title="Personalized Rankings"
                description="AI-powered hotel and flight scoring based on your preferences"
              />
              <FeatureCard
                icon={<Users className="h-6 w-6 text-purple-500" />}
                title="Smart Bundles"
                description="Dynamic package deals with real savings calculations"
              />
              <FeatureCard
                icon={<MapPin className="h-6 w-6 text-red-500" />}
                title="Location Intelligence"
                description="Walk scores, landmark distances, and neighborhood insights"
              />
              <FeatureCard
                icon={<Calendar className="h-6 w-6 text-orange-500" />}
                title="Flexible Booking"
                description="Real-time availability with cancellation policies"
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
                  <li>• Smart Bundle savings (Expedia 2025 pattern)</li>
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

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
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
