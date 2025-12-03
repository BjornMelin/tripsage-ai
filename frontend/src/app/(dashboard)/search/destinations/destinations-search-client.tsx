/**
 * @fileoverview Client-side destination search experience (renders within RSC shell).
 */

"use client";

import type { Destination, DestinationSearchParams } from "@schemas/search";
import {
  AlertCircleIcon,
  CalendarIcon,
  GlobeIcon,
  MapPinIcon,
  SearchIcon,
  StarIcon,
  ThermometerIcon,
  XIcon,
} from "lucide-react";
import { useState } from "react";
import { DestinationCard } from "@/components/features/search/destination-card";
import { DestinationSearchForm } from "@/components/features/search/destination-search-form";
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
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { DestinationSkeleton } from "@/components/ui/travel-skeletons";
import { useToast } from "@/components/ui/use-toast";
import type { DestinationResult } from "@/hooks/search/use-destination-search";
import { useDestinationSearch } from "@/hooks/search/use-destination-search";
import { useSearchOrchestration } from "@/hooks/search/use-search-orchestration";
import { getErrorMessage } from "@/lib/api/error-types";
import { formatDestinationTypes } from "@/lib/google/places-format";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";

/** The destinations search client component props. */
interface DestinationsSearchClientProps {
  onSubmitServer: (params: DestinationSearchParams) => Promise<DestinationSearchParams>;
}

/** Maximum number of items allowed in comparison views. */
const MAX_COMPARISON_ITEMS = 3;

/** The destinations search client component. */
export default function DestinationsSearchClient({
  onSubmitServer,
}: DestinationsSearchClientProps) {
  const { hasResults, isSearching: storeIsSearching } = useSearchOrchestration();
  const { searchDestinations, isSearching, searchError, resetSearch, results } =
    useDestinationSearch();
  const { toast } = useToast();

  const [selectedDestinations, setSelectedDestinations] = useState<Destination[]>([]);
  const [showComparisonModal, setShowComparisonModal] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  /** Handles the search for destinations. */
  const handleSearch = async (params: DestinationSearchParams) => {
    try {
      await onSubmitServer(params); // server-side telemetry and validation
      await searchDestinations(params); // client fetch/store update
      setHasSearched(true);
    } catch (error) {
      const normalizedError =
        error instanceof Error ? error : new Error(getErrorMessage(error));
      recordClientErrorOnActiveSpan(normalizedError, {
        action: "handleSearch",
        context: "DestinationsSearchClient",
      });
      // errors surfaced via searchError/alert
      setHasSearched(true);
    }
  };

  /** Handles the selection of a destination. */
  const handleDestinationSelect = (destination: Destination) => {
    toast({
      description: `You can view more details about ${destination.name} or add it to your trip.`,
      title: `Selected: ${destination.name}`,
    });
  };

  /** Handles the comparison toggle for a destination. */
  const handleDestinationCompare = (destination: Destination) => {
    setSelectedDestinations((prev) => {
      const isAlreadySelected = prev.some((d) => d.id === destination.id);
      if (isAlreadySelected) {
        toast({
          description: `${destination.name} removed from comparison.`,
          title: "Removed from comparison",
        });
        return prev.filter((d) => d.id !== destination.id);
      }
      if (prev.length >= MAX_COMPARISON_ITEMS) {
        toast({
          description: `You can compare up to ${MAX_COMPARISON_ITEMS} destinations at once.`,
          title: "Comparison limit reached",
          variant: "destructive",
        });
        return prev;
      }
      toast({
        description: `${destination.name} added to comparison.`,
        title: "Added to comparison",
      });
      return [...prev, destination];
    });
  };

  /** Handles removing a destination from comparison. */
  const handleRemoveFromComparison = (destinationId: string) => {
    setSelectedDestinations((prev) => {
      const removed = prev.find((d) => d.id === destinationId);
      if (removed) {
        toast({
          description: `${removed.name} removed from comparison.`,
          title: "Removed",
        });
      }
      return prev.filter((d) => d.id !== destinationId);
    });
  };

  /** Handles viewing details for a destination from comparison. */
  const handleViewDetailsFromComparison = (destination: Destination) => {
    setShowComparisonModal(false);
    toast({
      description: `Viewing details for ${destination.name}`,
      title: "View Details",
    });
  };

  /** Handles the viewing of details for a destination. */
  const handleViewDetails = (destination: Destination) => {
    toast({
      description: `Opening details for ${destination.name}...`,
      title: "Destination Details",
    });
  };

  /** Clears the comparison of destinations. */
  const clearComparison = () => {
    setSelectedDestinations([]);
    toast({
      description: "All destinations removed from comparison.",
      title: "Comparison cleared",
    });
  };

  /** The destinations to display. */
  const destinations: Destination[] = results
    .filter(
      (
        result
      ): result is DestinationResult & { location: { lat: number; lng: number } } =>
        Number.isFinite(result.location?.lat) && Number.isFinite(result.location?.lng)
    )
    .map((result) => ({
      attractions: [],
      bestTimeToVisit: undefined,
      climate: undefined,
      coordinates: {
        lat: result.location.lat,
        lng: result.location.lng,
      },
      country: undefined,
      description: result.address || result.name,
      formattedAddress: result.address || result.name,
      id: result.placeId,
      name: result.name,
      photos: undefined,
      placeId: result.placeId,
      popularityScore: undefined,
      rating: undefined,
      region: undefined,
      types: result.types,
    }));

  const isLoading = storeIsSearching || isSearching;
  const hasActiveResults = destinations.length > 0 || hasResults;

  return (
    <SearchLayout>
      <TooltipProvider>
        <div className="space-y-6">
          {/* Search Form Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <GlobeIcon className="h-5 w-5" />
                Discover Destinations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <DestinationSearchForm onSearch={handleSearch} />
            </CardContent>
          </Card>

          {/* Comparison Bar */}
          {selectedDestinations.length > 0 && (
            <Card className="border-primary/50 bg-primary/5">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <MapPinIcon className="h-5 w-5" />
                    Compare Destinations ({selectedDestinations.length}/
                    {MAX_COMPARISON_ITEMS})
                  </CardTitle>
                  <div className="flex gap-2">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          variant="default"
                          size="sm"
                          onClick={() => setShowComparisonModal(true)}
                          disabled={selectedDestinations.length < 2}
                        >
                          Compare Now
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>
                        {selectedDestinations.length < 2
                          ? "Select at least 2 destinations to compare"
                          : "Open comparison view"}
                      </TooltipContent>
                    </Tooltip>
                    <Button variant="outline" size="sm" onClick={clearComparison}>
                      Clear All
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
                      className="cursor-pointer hover:bg-destructive/20 transition-colors px-3 py-1.5 text-sm"
                      onClick={() => handleDestinationCompare(destination)}
                    >
                      {destination.name}
                      <XIcon className="h-3 w-3 ml-2" />
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {["sk-1", "sk-2", "sk-3", "sk-4", "sk-5", "sk-6"].map((id) => (
                <Card key={id} className="overflow-hidden">
                  <DestinationSkeleton />
                </Card>
              ))}
            </div>
          )}

          {/* Error State */}
          {searchError && (
            <Alert variant="destructive">
              <AlertCircleIcon className="h-4 w-4" />
              <AlertTitle>Search Error</AlertTitle>
              <AlertDescription className="flex items-center justify-between">
                <span>{searchError.message}</span>
                <Button variant="outline" size="sm" onClick={resetSearch}>
                  Try Again
                </Button>
              </AlertDescription>
            </Alert>
          )}

          {/* Empty State */}
          {!isLoading && hasSearched && !hasActiveResults && !searchError && (
            <Card>
              <CardContent className="text-center py-12">
                <div className="flex flex-col items-center gap-4">
                  <div className="rounded-full bg-muted p-4">
                    <SearchIcon className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-lg font-semibold">No destinations found</h3>
                    <p className="text-muted-foreground max-w-md">
                      Try adjusting your search terms, selecting different destination
                      types, or searching for a broader location.
                    </p>
                  </div>
                  <Button variant="outline" onClick={resetSearch}>
                    Clear Search
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Results Grid */}
          {!isLoading && !searchError && hasActiveResults && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">
                  {destinations.length} Destination{destinations.length !== 1 && "s"}{" "}
                  Found
                </h2>
                {destinations.length > 0 && (
                  <p className="text-sm text-muted-foreground">
                    Click &quot;Compare&quot; to add destinations to your comparison
                  </p>
                )}
              </div>

              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
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

          {/* Initial State */}
          {!isLoading && !hasSearched && !searchError && (
            <Card className="bg-muted/50">
              <CardContent className="text-center py-12">
                <div className="flex flex-col items-center gap-4">
                  <div className="rounded-full bg-background p-4 shadow-sm">
                    <GlobeIcon className="h-8 w-8 text-primary" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-lg font-semibold">
                      Discover Your Next Adventure
                    </h3>
                    <p className="text-muted-foreground max-w-md">
                      Search for cities, countries, landmarks, and more. Compare
                      destinations side-by-side to find your perfect travel spot.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Floating Compare Button */}
          {selectedDestinations.length > 0 && (
            <div className="fixed bottom-6 right-6 z-40">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="lg"
                    onClick={() => setShowComparisonModal(true)}
                    disabled={selectedDestinations.length < 2}
                    className="shadow-lg"
                  >
                    <MapPinIcon className="h-4 w-4 mr-2" />
                    Compare ({selectedDestinations.length})
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="left">
                  {selectedDestinations.length < 2
                    ? `Select ${2 - selectedDestinations.length} more to compare`
                    : "Open comparison view"}
                </TooltipContent>
              </Tooltip>
            </div>
          )}

          {/* Comparison Modal */}
          <DestinationComparisonModal
            isOpen={showComparisonModal}
            onClose={() => setShowComparisonModal(false)}
            destinations={selectedDestinations}
            onRemove={handleRemoveFromComparison}
            onViewDetails={handleViewDetailsFromComparison}
          />
        </div>
      </TooltipProvider>
    </SearchLayout>
  );
}

/** Props for the DestinationComparisonModal. */
interface DestinationComparisonModalProps {
  isOpen: boolean;
  onClose: () => void;
  destinations: Destination[];
  onRemove: (destinationId: string) => void;
  onViewDetails: (destination: Destination) => void;
}

/**
 * Modal dialog for comparing destinations side-by-side.
 */
function DestinationComparisonModal({
  isOpen,
  onClose,
  destinations,
  onRemove,
  onViewDetails,
}: DestinationComparisonModalProps) {
  if (!destinations.length) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl w-full max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MapPinIcon className="h-5 w-5" />
            Compare Destinations
          </DialogTitle>
          <DialogDescription>
            Compare up to {MAX_COMPARISON_ITEMS} destinations side-by-side to find your
            perfect travel spot.
          </DialogDescription>
        </DialogHeader>

        <Separator className="my-2" />

        <ScrollArea className="flex-1 mt-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[150px]">Feature</TableHead>
                {destinations.map((destination) => (
                  <TableHead key={destination.id} className="min-w-[200px]">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold truncate">{destination.name}</span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 rounded-full shrink-0"
                        onClick={() => onRemove(destination.id)}
                        aria-label={`Remove ${destination.name} from comparison`}
                      >
                        <XIcon className="h-3 w-3" />
                      </Button>
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {/* Type Row */}
              <TableRow>
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    <GlobeIcon className="h-4 w-4 text-muted-foreground" />
                    Type
                  </div>
                </TableCell>
                {destinations.map((destination) => (
                  <TableCell key={destination.id}>
                    <Badge variant="secondary">
                      {formatDestinationTypes(destination.types)}
                    </Badge>
                  </TableCell>
                ))}
              </TableRow>

              {/* Location Row */}
              <TableRow>
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    <MapPinIcon className="h-4 w-4 text-muted-foreground" />
                    Location
                  </div>
                </TableCell>
                {destinations.map((destination) => (
                  <TableCell key={destination.id}>
                    <span className="text-sm line-clamp-2">
                      {destination.formattedAddress || "Unknown location"}
                    </span>
                  </TableCell>
                ))}
              </TableRow>

              {/* Rating Row */}
              <TableRow>
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    <StarIcon className="h-4 w-4 text-muted-foreground" />
                    Rating
                  </div>
                </TableCell>
                {destinations.map((destination) => (
                  <TableCell key={destination.id}>
                    {destination.rating ? (
                      <div className="flex items-center gap-1">
                        <StarIcon className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                        <span className="font-medium">
                          {destination.rating.toFixed(1)}
                        </span>
                      </div>
                    ) : (
                      <span className="text-muted-foreground">N/A</span>
                    )}
                  </TableCell>
                ))}
              </TableRow>

              {/* Climate Row */}
              <TableRow>
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    <ThermometerIcon className="h-4 w-4 text-muted-foreground" />
                    Climate
                  </div>
                </TableCell>
                {destinations.map((destination) => (
                  <TableCell key={destination.id}>
                    {destination.climate ? (
                      <span className="text-sm">
                        {destination.climate.averageTemp}°C avg
                      </span>
                    ) : (
                      <span className="text-muted-foreground">N/A</span>
                    )}
                  </TableCell>
                ))}
              </TableRow>

              {/* Best Time Row */}
              <TableRow>
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    <CalendarIcon className="h-4 w-4 text-muted-foreground" />
                    Best Time
                  </div>
                </TableCell>
                {destinations.map((destination) => (
                  <TableCell key={destination.id}>
                    {destination.bestTimeToVisit?.length ? (
                      <span className="text-sm">
                        {destination.bestTimeToVisit.slice(0, 3).join(", ")}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">Year-round</span>
                    )}
                  </TableCell>
                ))}
              </TableRow>

              {/* Popularity Row */}
              <TableRow>
                <TableCell className="font-medium">Popularity</TableCell>
                {destinations.map((destination) => (
                  <TableCell key={destination.id}>
                    {destination.popularityScore ? (
                      <div className="flex items-center gap-2">
                        <div className="h-2 flex-1 bg-muted rounded-full overflow-hidden max-w-24">
                          <div
                            className="h-full bg-primary transition-all"
                            style={{ width: `${destination.popularityScore}%` }}
                          />
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {destination.popularityScore}/100
                        </span>
                      </div>
                    ) : (
                      <span className="text-muted-foreground">N/A</span>
                    )}
                  </TableCell>
                ))}
              </TableRow>

              {/* Actions Row */}
              <TableRow>
                <TableCell className="font-medium">Actions</TableCell>
                {destinations.map((destination) => (
                  <TableCell key={destination.id}>
                    <Button
                      className="w-full"
                      onClick={() => onViewDetails(destination)}
                    >
                      View Details
                    </Button>
                  </TableCell>
                ))}
              </TableRow>
            </TableBody>
          </Table>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
