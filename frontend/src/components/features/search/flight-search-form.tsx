"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import type { FlightSearchParams } from "@/types/search";
import {
  ArrowRight,
  Calendar,
  Clock,
  Loader2,
  MapPin,
  Plane,
  Search,
  Sparkles,
  TrendingDown,
  Users,
} from "lucide-react";
import { useOptimistic, useState, useTransition } from "react";

// React 19 optimistic update types
interface ModernFlightSearchParams {
  from: string;
  to: string;
  departDate: string;
  returnDate?: string;
  passengers: number;
  class: "economy" | "premium" | "business" | "first";
  tripType: "roundtrip" | "oneway" | "multicity";
}

interface SearchSuggestion {
  id: string;
  type: "city" | "airport";
  name: string;
  code: string;
  country: string;
  popular?: boolean;
}

interface FlightSearchFormProps {
  onSearch: (params: ModernFlightSearchParams) => Promise<void>;
  suggestions?: SearchSuggestion[];
  className?: string;
  showSmartBundles?: boolean;
}

export function FlightSearchForm({
  onSearch,
  suggestions = [],
  className,
  showSmartBundles = true,
}: FlightSearchFormProps) {
  const [isPending, startTransition] = useTransition();

  // Form state with React 19 patterns
  const [searchParams, setSearchParams] = useState<ModernFlightSearchParams>({
    from: "",
    to: "",
    departDate: "",
    returnDate: "",
    passengers: 1,
    class: "economy",
    tripType: "roundtrip",
  });

  // Optimistic search state
  const [optimisticSearching, setOptimisticSearching] = useOptimistic(
    false,
    (state, isSearching: boolean) => isSearching
  );

  // Mock data for demo - would come from backend
  const popularDestinations = [
    { code: "NYC", name: "New York", savings: "$127" },
    { code: "LAX", name: "Los Angeles", savings: "$89" },
    { code: "LHR", name: "London", savings: "$234" },
    { code: "NRT", name: "Tokyo", savings: "$298" },
  ];

  const smartBundles = {
    hotel: "$156",
    car: "$89",
    total: "$245",
  };

  const handleInputChange = (
    field: keyof ModernFlightSearchParams,
    value: string | number
  ) => {
    setSearchParams((prev) => ({ ...prev, [field]: value }));
  };

  const handleSearch = () => {
    startTransition(async () => {
      setOptimisticSearching(true);
      try {
        await onSearch(searchParams);
      } catch (error) {
        console.error("Search failed:", error);
      } finally {
        setOptimisticSearching(false);
      }
    });
  };

  const handleSwapAirports = () => {
    setSearchParams((prev) => ({
      ...prev,
      from: prev.to,
      to: prev.from,
    }));
  };

  const handleQuickFill = (destination: { code: string; name: string }) => {
    setSearchParams((prev) => ({
      ...prev,
      to: destination.code,
    }));
  };

  return (
    <Card className={cn("w-full max-w-4xl mx-auto", className)}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
              <Plane className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <CardTitle className="text-xl">Find Flights</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                Search and compare flights from top airlines
              </p>
            </div>
          </div>

          {showSmartBundles && (
            <div className="hidden md:flex items-center gap-2">
              <Badge
                variant="secondary"
                className="bg-green-50 text-green-700 border-green-200"
              >
                <Sparkles className="h-3 w-3 mr-1" />
                Smart Bundle: Save up to {smartBundles.total}
              </Badge>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Trip Type Selector */}
        <div className="flex gap-2">
          {(["roundtrip", "oneway", "multicity"] as const).map((type) => (
            <Button
              key={type}
              variant={searchParams.tripType === type ? "default" : "outline"}
              size="sm"
              onClick={() => handleInputChange("tripType", type)}
              className="capitalize"
            >
              {type === "roundtrip"
                ? "Round Trip"
                : type === "oneway"
                  ? "One Way"
                  : "Multi-City"}
            </Button>
          ))}
        </div>

        {/* Main Search Form */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* From/To Section */}
          <div className="lg:col-span-6 grid grid-cols-1 md:grid-cols-2 gap-4 relative">
            <div className="space-y-2">
              <Label htmlFor="from" className="text-sm font-medium">
                From
              </Label>
              <div className="relative">
                <MapPin className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="from"
                  placeholder="Departure city or airport"
                  value={searchParams.from}
                  onChange={(e) => handleInputChange("from", e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            {/* Swap Button */}
            <div className="hidden md:flex absolute left-1/2 top-8 transform -translate-x-1/2 z-10">
              <Button
                variant="outline"
                size="icon"
                onClick={handleSwapAirports}
                className="rounded-full bg-background border-2 shadow-md hover:shadow-lg transition-shadow"
              >
                <ArrowRight className="h-4 w-4" />
              </Button>
            </div>

            <div className="space-y-2">
              <Label htmlFor="to" className="text-sm font-medium">
                To
              </Label>
              <div className="relative">
                <MapPin className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="to"
                  placeholder="Destination city or airport"
                  value={searchParams.to}
                  onChange={(e) => handleInputChange("to", e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </div>

          {/* Dates Section */}
          <div className="lg:col-span-4 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="depart" className="text-sm font-medium">
                Departure
              </Label>
              <div className="relative">
                <Calendar className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="depart"
                  type="date"
                  value={searchParams.departDate}
                  onChange={(e) => handleInputChange("departDate", e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            {searchParams.tripType === "roundtrip" && (
              <div className="space-y-2">
                <Label htmlFor="return" className="text-sm font-medium">
                  Return
                </Label>
                <div className="relative">
                  <Calendar className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="return"
                    type="date"
                    value={searchParams.returnDate}
                    onChange={(e) => handleInputChange("returnDate", e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Passengers & Class */}
          <div className="lg:col-span-2 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="passengers" className="text-sm font-medium">
                Passengers
              </Label>
              <div className="relative">
                <Users className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Select
                  value={searchParams.passengers.toString()}
                  onValueChange={(value) =>
                    handleInputChange("passengers", Number.parseInt(value))
                  }
                >
                  <SelectTrigger className="pl-10">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[1, 2, 3, 4, 5, 6].map((num) => (
                      <SelectItem key={num} value={num.toString()}>
                        {num} {num === 1 ? "Passenger" : "Passengers"}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="class" className="text-sm font-medium">
                Class
              </Label>
              <Select
                value={searchParams.class}
                onValueChange={(value: ModernFlightSearchParams["class"]) =>
                  handleInputChange("class", value)
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="economy">Economy</SelectItem>
                  <SelectItem value="premium">Premium Economy</SelectItem>
                  <SelectItem value="business">Business</SelectItem>
                  <SelectItem value="first">First Class</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </div>

        {/* Popular Destinations */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <TrendingDown className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Popular destinations</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {popularDestinations.map((dest) => (
              <Button
                key={dest.code}
                variant="outline"
                size="sm"
                onClick={() => handleQuickFill(dest)}
                className="h-auto py-2 px-3 flex flex-col items-start"
              >
                <span className="font-medium">{dest.name}</span>
                <span className="text-xs text-green-600">Save {dest.savings}</span>
              </Button>
            ))}
          </div>
        </div>

        {/* Smart Bundle Preview */}
        {showSmartBundles && (
          <>
            <Separator />
            <div className="bg-gradient-to-r from-blue-50 to-green-50 p-4 rounded-lg border">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-blue-600" />
                  <h3 className="font-semibold text-sm">Smart Trip Bundle</h3>
                  <Badge variant="secondary" className="bg-green-100 text-green-700">
                    Save {smartBundles.total}
                  </Badge>
                </div>
                <span className="text-xs text-muted-foreground">
                  vs booking separately
                </span>
              </div>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="text-center">
                  <div className="font-medium">Flight + Hotel</div>
                  <div className="text-green-600 font-semibold">
                    Save {smartBundles.hotel}
                  </div>
                </div>
                <div className="text-center">
                  <div className="font-medium">+ Car Rental</div>
                  <div className="text-green-600 font-semibold">
                    Save {smartBundles.car}
                  </div>
                </div>
                <div className="text-center">
                  <div className="font-medium">Total Savings</div>
                  <div className="text-green-600 font-semibold text-lg">
                    {smartBundles.total}
                  </div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Search Button */}
        <div className="flex gap-3 pt-2">
          <Button
            onClick={handleSearch}
            disabled={
              isPending ||
              optimisticSearching ||
              !searchParams.from ||
              !searchParams.to ||
              !searchParams.departDate
            }
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
            size="lg"
          >
            {isPending || optimisticSearching ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Searching flights...
              </>
            ) : (
              <>
                <Search className="h-4 w-4 mr-2" />
                Search Flights
              </>
            )}
          </Button>

          <Button variant="outline" size="lg" className="px-6">
            <Clock className="h-4 w-4 mr-2" />
            Flexible Dates
          </Button>
        </div>

        {/* Progress indicator for optimistic updates */}
        {(isPending || optimisticSearching) && (
          <div className="space-y-2">
            <Progress value={66} className="h-2" />
            <p className="text-xs text-muted-foreground text-center">
              Searching 500+ airlines for the best deals...
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
