/**
 * @fileoverview Modal component for selecting a trip to add an activity to.
 */

"use client";

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
import { ScrollArea } from "@/components/ui/scroll-area";
import type { Activity } from "@schemas/search";
import type { UiTrip } from "@schemas/trips";
import { Calendar, MapPin } from "lucide-react";
import { useState } from "react";

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
  const [selectedTripId, setSelectedTripId] = useState<string | null>(null);

  const handleConfirm = async () => {
    if (selectedTripId) {
      await onAddToTrip(selectedTripId);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
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
              <Button variant="link" className="mt-2">
                Create a new trip
              </Button>
            </div>
          ) : (
            <ScrollArea className="h-[300px] pr-4">
              <div className="space-y-4">
                {trips.map((trip) => (
                  <div
                    key={trip.id}
                    className={`flex items-start space-x-3 space-y-0 rounded-md border p-4 cursor-pointer transition-colors ${
                      selectedTripId === trip.id
                        ? "border-primary bg-accent"
                        : "hover:bg-accent/50"
                    }`}
                    onClick={() => setSelectedTripId(trip.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        setSelectedTripId(trip.id);
                      }
                    }}
                  >
                    <div
                      className={`mt-1 h-4 w-4 rounded-full border border-primary flex items-center justify-center ${
                        selectedTripId === trip.id ? "bg-primary" : ""
                      }`}
                    >
                      {selectedTripId === trip.id && (
                        <div className="h-2 w-2 rounded-full bg-primary-foreground" />
                      )}
                    </div>
                    <div className="grid gap-1.5 w-full">
                      <Label className="font-semibold cursor-pointer text-base">
                        {trip.title}
                      </Label>
                      <div className="flex items-center text-sm text-muted-foreground gap-2">
                        <MapPin className="h-3 w-3" />
                        <span>{trip.destination}</span>
                      </div>
                      {trip.startDate && (
                        <div className="flex items-center text-sm text-muted-foreground gap-2">
                          <Calendar className="h-3 w-3" />
                          <span>
                            {new Date(trip.startDate).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isAdding}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirm}
            disabled={!selectedTripId || isAdding}
          >
            {isAdding ? "Adding..." : "Add to Trip"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
