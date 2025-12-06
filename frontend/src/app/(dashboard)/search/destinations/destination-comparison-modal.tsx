/**
 * @fileoverview DestinationComparisonModal component for comparing multiple destinations side-by-side.
 */

import type { Destination } from "@schemas/search";
import {
  CalendarIcon,
  GlobeIcon,
  MapPinIcon,
  StarIcon,
  ThermometerIcon,
  XIcon,
} from "lucide-react";
import { useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { formatDestinationTypes } from "@/lib/google/places-format";

const clampPopularity = (score: number): number => Math.max(0, Math.min(100, score));

/**
 * Props for the destination comparison modal component.
 *
 * @public
 */
export interface DestinationComparisonModalProps {
  /** Whether the modal dialog is currently open. */
  isOpen: boolean;
  /** Callback invoked when the modal should be closed. */
  onClose: () => void;
  /** Array of destinations to display in the comparison table. */
  destinations: Destination[];
  /**
   * Callback invoked when a destination should be removed from comparison.
   *
   * @param destinationId - The unique identifier of the destination to remove.
   */
  onRemove: (destinationId: string) => void;
  /**
   * Callback invoked when viewing detailed information for a destination.
   *
   * @param destination - The destination object to view details for.
   */
  onViewDetails: (destination: Destination) => void;
  /** Maximum number of destinations that can be compared simultaneously. */
  maxItems: number;
}

/**
 * Modal dialog component for comparing multiple destinations side-by-side.
 *
 * Displays a table comparing destinations across multiple attributes including:
 * type, location, rating, climate, best time to visit, and popularity score.
 * Each destination column includes a remove button and an action button to view
 * detailed information.
 *
 * The component renders nothing if the destinations array is empty.
 *
 * @param props - Component props.
 * @param props.isOpen - Whether the modal dialog is currently open.
 * @param props.onClose - Callback invoked when the modal should be closed.
 * @param props.destinations - Array of destinations to display in the comparison table.
 * @param props.onRemove - Callback invoked when a destination should be removed from comparison.
 * @param props.onViewDetails - Callback invoked when viewing detailed information for a destination.
 * @param props.maxItems - Maximum number of destinations that can be compared simultaneously.
 * @returns The modal dialog component, or null if no destinations are provided.
 */
export function DestinationComparisonModal({
  isOpen,
  onClose,
  destinations,
  onRemove,
  onViewDetails,
  maxItems,
}: DestinationComparisonModalProps) {
  useEffect(() => {
    if (isOpen && destinations.length === 0) {
      onClose();
    }
  }, [destinations.length, isOpen, onClose]);

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
            Compare up to {maxItems} destinations side-by-side to find your perfect
            travel spot.
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

              <TableRow>
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    <ThermometerIcon className="h-4 w-4 text-muted-foreground" />
                    Climate
                  </div>
                </TableCell>
                {destinations.map((destination) => (
                  <TableCell key={destination.id}>
                    {typeof destination.climate?.averageTemp === "number" &&
                    Number.isFinite(destination.climate.averageTemp) ? (
                      <span className="text-sm">
                        {destination.climate.averageTemp}°C avg
                      </span>
                    ) : (
                      <span className="text-muted-foreground">N/A</span>
                    )}
                  </TableCell>
                ))}
              </TableRow>

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

              <TableRow>
                <TableCell className="font-medium">Popularity</TableCell>
                {destinations.map((destination) => {
                  const clampedPopularity =
                    destination.popularityScore != null
                      ? clampPopularity(destination.popularityScore)
                      : null;
                  return (
                    <TableCell key={destination.id}>
                      {clampedPopularity != null ? (
                        <div className="flex items-center gap-2">
                          <div className="h-2 flex-1 bg-muted rounded-full overflow-hidden max-w-24">
                            <div
                              className="h-full bg-primary transition-all"
                              style={{
                                width: `${clampedPopularity}%`,
                              }}
                            />
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {clampedPopularity}/100
                          </span>
                        </div>
                      ) : (
                        <span className="text-muted-foreground">N/A</span>
                      )}
                    </TableCell>
                  );
                })}
              </TableRow>

              <TableRow>
                <TableCell className="font-medium">Actions</TableCell>
                {destinations.map((destination) => (
                  <TableCell key={destination.id}>
                    <Button
                      className="w-full"
                      aria-label={`View details for ${destination.name ?? "destination"}`}
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
