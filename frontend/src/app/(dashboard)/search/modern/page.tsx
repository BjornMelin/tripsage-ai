"use client";

import { useState, useTransition } from "react";
import { FlightSearchForm } from "@/components/features/search/flight-search-form";
import { HotelSearchForm } from "@/components/features/search/hotel-search-form";
import { ModernFlightResults } from "@/components/features/search/modern-flight-results";
import { ModernHotelResults } from "@/components/features/search/modern-hotel-results";
import { SearchLayout } from "@/components/layouts/search-layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import {
  Plane,
  Building2,
  Calendar,
  MapPin,
  Users,
  Sparkles,
  TrendingUp,
  Zap,
  Star,
  Clock,
} from "lucide-react";

// Mock data for demo purposes
const mockFlightResults = [
  {
    id: "flight-1",
    airline: "Delta Airlines",
    flightNumber: "DL 128",
    aircraft: "Boeing 787",
    origin: { code: "JFK", city: "New York", terminal: "4" },
    destination: { code: "LHR", city: "London", terminal: "3" },
    departure: { time: "10:30 AM", date: "2025-06-15" },
    arrival: { time: "10:45 PM", date: "2025-06-15" },
    duration: 420,
    stops: { count: 0, cities: [] },
    price: {
      base: 599,
      total: 699,
      currency: "USD",
      priceChange: "down" as const,
      dealScore: 9,
    },
    amenities: ["wifi", "meals", "entertainment"],
    emissions: { kg: 850, compared: "low" as const },
    flexibility: { changeable: true, refundable: false, cost: 50 },
    prediction: {
      priceAlert: "buy_now" as const,
      confidence: 89,
      reason: "Prices trending up for this route",
    },
    promotions: {
      type: "flash_deal" as const,
      description: "Flash Deal - 24hrs only",
      savings: 150,
    },
  },
  {
    id: "flight-2",
    airline: "United Airlines",
    flightNumber: "UA 901",
    aircraft: "Airbus A350",
    origin: { code: "JFK", city: "New York", terminal: "7" },
    destination: { code: "LHR", city: "London", terminal: "2" },
    departure: { time: "1:15 PM", date: "2025-06-15" },
    arrival: { time: "1:35 AM", date: "2025-06-16" },
    duration: 440,
    stops: { count: 0, cities: [] },
    price: {
      base: 649,
      total: 749,
      currency: "USD",
      priceChange: "stable" as const,
      dealScore: 7,
    },
    amenities: ["wifi", "entertainment"],
    emissions: { kg: 920, compared: "average" as const },
    flexibility: { changeable: true, refundable: true, cost: 0 },
    prediction: {
      priceAlert: "neutral" as const,
      confidence: 72,
      reason: "Stable pricing expected",
    },
  },
] as any;

const mockHotelResults = [
  {
    id: "hotel-1",
    name: "The Ritz-Carlton New York",
    brand: "Ritz-Carlton",
    category: "hotel" as const,
    starRating: 5,
    userRating: 4.8,
    reviewCount: 2847,
    location: {
      address: "50 Central Park South",
      city: "New York",
      district: "Midtown",
      landmarks: ["Central Park", "Times Square"],
      walkScore: 95,
    },
    images: {
      main: "/hotel-1.jpg",
      gallery: [],
      count: 24,
    },
    pricing: {
      basePrice: 450,
      totalPrice: 1350,
      pricePerNight: 450,
      currency: "USD",
      taxes: 85,
      deals: {
        type: "early_bird" as const,
        description: "Early Bird - Book 30 days ahead",
        savings: 75,
        originalPrice: 525,
      },
      priceHistory: "falling" as const,
    },
    amenities: {
      essential: ["wifi", "breakfast", "gym", "spa"],
      premium: ["concierge", "butler"],
      unique: ["central-park-view"],
    },
    sustainability: {
      certified: true,
      score: 8,
      practices: ["solar-power", "recycling", "local-sourcing"],
    },
    allInclusive: {
      available: false,
      inclusions: [],
      tier: "basic" as const,
    },
    availability: {
      roomsLeft: 3,
      urgency: "high" as const,
      flexible: true,
    },
    guestExperience: {
      highlights: ["Exceptional service with Central Park views"],
      recentMentions: ["Outstanding breakfast", "Perfect location"],
      vibe: "luxury" as const,
    },
    ai: {
      recommendation: 9,
      reason: "Perfect for luxury seekers with prime location",
      personalizedTags: ["luxury", "city-center", "business"],
    },
  },
  {
    id: "hotel-2",
    name: "Pod Hotels Times Square",
    brand: "Pod Hotels",
    category: "hotel" as const,
    starRating: 3,
    userRating: 4.2,
    reviewCount: 1893,
    location: {
      address: "400 W 42nd St",
      city: "New York",
      district: "Times Square",
      landmarks: ["Times Square", "Broadway"],
      walkScore: 100,
    },
    images: {
      main: "/hotel-2.jpg",
      gallery: [],
      count: 18,
    },
    pricing: {
      basePrice: 189,
      totalPrice: 567,
      pricePerNight: 189,
      currency: "USD",
      taxes: 35,
      priceHistory: "rising" as const,
    },
    amenities: {
      essential: ["wifi", "gym"],
      premium: [],
      unique: ["pod-design", "rooftop-bar"],
    },
    sustainability: {
      certified: false,
      score: 6,
      practices: ["energy-efficient"],
    },
    allInclusive: {
      available: false,
      inclusions: [],
      tier: "basic" as const,
    },
    availability: {
      roomsLeft: 12,
      urgency: "low" as const,
      flexible: true,
    },
    guestExperience: {
      highlights: ["Modern pod-style rooms in heart of Times Square"],
      recentMentions: ["Great location", "Clean and efficient"],
      vibe: "business" as const,
    },
    ai: {
      recommendation: 7,
      reason: "Great value in prime location for business travelers",
      personalizedTags: ["budget", "city-center", "modern"],
    },
  },
] as any;

export default function ModernSearchPage() {
  const [isPending, startTransition] = useTransition();
  const [activeTab, setActiveTab] = useState<"flights" | "hotels">("flights");
  const [showResults, setShowResults] = useState(false);
  const [searchData, setSearchData] = useState<any>(null);

  const handleFlightSearch = async (params: any) => {
    startTransition(() => {
      setSearchData(params);
      setShowResults(true);
      // Simulate API call
      setTimeout(() => {
        setShowResults(true);
      }, 1500);
    });
  };

  const handleHotelSearch = async (params: any) => {
    startTransition(() => {
      setSearchData(params);
      setShowResults(true);
      // Simulate API call
      setTimeout(() => {
        setShowResults(true);
      }, 1500);
    });
  };

  const handleFlightSelect = async (flight: any) => {
    console.log("Selected flight:", flight);
    // Handle flight selection
  };

  const handleHotelSelect = async (hotel: any) => {
    console.log("Selected hotel:", hotel);
    // Handle hotel selection
  };

  const handleCompareFlights = (flights: any[]) => {
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
        <Card className="bg-gradient-to-r from-blue-50 to-green-50 border-none">
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
                    results={mockFlightResults}
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
                    results={mockHotelResults}
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
