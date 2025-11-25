/**
 * @fileoverview Modal component for comparing selected activities side-by-side.
 */

"use client";

import type { Activity } from "@schemas/search";
import { MapPin, Star, X } from "lucide-react";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface ActivityComparisonModalProps {
  isOpen: boolean;
  onClose: () => void;
  activities: Activity[];
  onRemove: (activityId: string) => void;
  onAddToTrip: (activity: Activity) => void;
}

/**
 * Modal dialog for comparing activities.
 *
 * Displays a side-by-side comparison of selected activities including
 * details like price, rating, location, and type.
 *
 * @param props - Component props.
 * @param props.isOpen - Whether the modal is open.
 * @param props.onClose - Callback to close the modal.
 * @param props.activities - List of activities to compare.
 * @param props.onRemove - Callback to remove an activity from comparison.
 * @param props.onAddToTrip - Callback to initiate adding an activity to a trip.
 */
export function ActivityComparisonModal({
  isOpen,
  onClose,
  activities,
  onRemove,
  onAddToTrip,
}: ActivityComparisonModalProps) {
  if (!activities.length) return null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl w-full max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Compare Activities</DialogTitle>
          <DialogDescription>
            Compare up to 3 activities side-by-side to make the best choice.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="flex-1 mt-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[150px]">Feature</TableHead>
                {activities.map((activity) => (
                  <TableHead key={activity.id} className="min-w-[250px] relative">
                    <div className="flex items-center justify-between">
                      <span className="truncate font-bold">{activity.name}</span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 rounded-full"
                        onClick={() => onRemove(activity.id)}
                        aria-label={`Remove ${activity.name} from comparison`}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {/* Image Row */}
              <TableRow>
                <TableCell className="font-medium">Image</TableCell>
                {activities.map((activity) => (
                  <TableCell key={activity.id}>
                    <div className="relative h-32 w-full rounded-md overflow-hidden bg-muted">
                      {activity.images?.[0] ? (
                        <Image
                          src={activity.images[0]}
                          alt={activity.name}
                          fill
                          className="object-cover"
                          sizes="(max-width: 768px) 100vw, 33vw"
                        />
                      ) : (
                        <div className="flex items-center justify-center h-full text-muted-foreground text-xs">
                          No image
                        </div>
                      )}
                    </div>
                  </TableCell>
                ))}
              </TableRow>

              {/* Price Row */}
              <TableRow>
                <TableCell className="font-medium">Price</TableCell>
                {activities.map((activity) => (
                  <TableCell key={activity.id}>
                    {activity.price ? (
                      <span className="font-semibold">
                        {activity.price.toLocaleString("en-US", {
                          currency: "USD", // Assuming USD for now, ideally from activity
                          style: "currency",
                        })}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">Free / Unknown</span>
                    )}
                  </TableCell>
                ))}
              </TableRow>

              {/* Rating Row */}
              <TableRow>
                <TableCell className="font-medium">Rating</TableCell>
                {activities.map((activity) => (
                  <TableCell key={activity.id}>
                    <div className="flex items-center gap-1">
                      <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                      <span>{activity.rating ?? "N/A"}</span>
                    </div>
                  </TableCell>
                ))}
              </TableRow>

              {/* Location Row */}
              <TableRow>
                <TableCell className="font-medium">Location</TableCell>
                {activities.map((activity) => (
                  <TableCell key={activity.id}>
                    <div className="flex items-start gap-1">
                      <MapPin className="h-4 w-4 mt-0.5 shrink-0 text-muted-foreground" />
                      <span className="text-sm line-clamp-2">
                        {activity.location ?? "Unknown location"}
                      </span>
                    </div>
                  </TableCell>
                ))}
              </TableRow>

              {/* Type/Category Row */}
              <TableRow>
                <TableCell className="font-medium">Type</TableCell>
                {activities.map((activity) => (
                  <TableCell key={activity.id}>
                    <span className="capitalize">{activity.type}</span>
                  </TableCell>
                ))}
              </TableRow>

              {/* Actions Row */}
              <TableRow>
                <TableCell className="font-medium">Actions</TableCell>
                {activities.map((activity) => (
                  <TableCell key={activity.id}>
                    <Button className="w-full" onClick={() => onAddToTrip(activity)}>
                      Add to Trip
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
