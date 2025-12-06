/**
 * @fileoverview Modal component for selecting a trip to add an activity to.
 */

"use client";

import type { Activity } from "@schemas/search";
import type { UiTrip } from "@schemas/trips";
import { CalendarIcon, MapPinIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { ScrollArea } from "@/components/ui/scroll-area";

interface TripSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  activity: Activity;
  trips: UiTrip[];
  onAddToTrip: (tripId: string) => Promise<void>;
  isAdding: boolean;
}

/**
 * Modal dialog for selecting a trip from a list.
 *
 * Displays a list of user trips and allows selecting one to add an activity to.
 * Handles empty states and loading states.
 *
 * @param props - Component props.
 * @param props.isOpen - Whether the modal is open.
 * @param props.onClose - Callback to close the modal.
 * @param props.activity - The activity being added.
 * @param props.trips - List of available trips.
 * @param props.onAddToTrip - Callback when a trip is selected and confirmed.
 * @param props.isAdding - Whether the add operation is in progress.
 */
export function TripSelectionModal({
  isOpen,
  onClose,
  activity,
  trips,
  onAddToTrip,
  isAdding,
}: TripSelectionModalProps) {
  const router = useRouter();
  const [selectedTripId, setSelectedTripId] = useState<string | null>(null);

  const handleClose = () => {
    setSelectedTripId(null);
    onClose();
  };

  const handleConfirm = async () => {
    if (selectedTripId) {
      await onAddToTrip(selectedTripId);
    }
  };

  // biome-ignore lint/correctness/useExhaustiveDependencies: reset selection when modal or activity changes
  useEffect(() => {
    setSelectedTripId(null);
  }, [activity.id, isOpen]);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Add to Trip</DialogTitle>
          <DialogDescription>
            Choose a trip to add "{activity.name}" to.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          {trips.length === 0 ? (
            <div className="text-center py-4 text-muted-foreground">
              No active or planning trips found.
              <br />
              <Button
                variant="link"
                className="mt-2"
                onClick={() => {
                  onClose();
                  router.push("/trips");
                }}
              >
                Create a new trip
              </Button>
            </div>
          ) : (
            <ScrollArea className="h-[300px] pr-4">
              <RadioGroup
                value={selectedTripId ?? ""}
                onValueChange={(value) =>
                  setSelectedTripId(value === "" ? null : value)
                }
                className="space-y-4"
              >
                {trips.map((trip) => (
                  <div
                    key={trip.id}
                    className={`flex items-start space-x-3 space-y-0 rounded-md border p-4 transition-colors ${
                      selectedTripId === trip.id
                        ? "border-primary bg-accent"
                        : "hover:bg-accent/50"
                    }`}
                  >
                    <RadioGroupItem
                      value={trip.id}
                      id={`trip-${trip.id}`}
                      className="mt-1 cursor-pointer"
                    />
                    <Label
                      htmlFor={`trip-${trip.id}`}
                      className="flex-1 cursor-pointer grid gap-1.5"
                    >
                      <span className="font-semibold text-base">{trip.title}</span>
                      <div className="flex items-center text-sm text-muted-foreground gap-2">
                        <MapPinIcon className="h-3 w-3" />
                        <span>{trip.destination}</span>
                      </div>
                      {trip.startDate && (
                        <div className="flex items-center text-sm text-muted-foreground gap-2">
                          <CalendarIcon className="h-3 w-3" />
                          <span>{new Date(trip.startDate).toLocaleDateString()}</span>
                        </div>
                      )}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            </ScrollArea>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isAdding}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={!selectedTripId || isAdding}>
            {isAdding ? "Adding..." : "Add to Trip"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
