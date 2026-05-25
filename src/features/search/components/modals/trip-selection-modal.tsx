/**
 * @fileoverview Modal component for selecting a trip to add an activity to.
 */

"use client";

import type { Activity } from "@schemas/search";
import type { UiTrip } from "@schemas/trips";
import { CalendarIcon, MapPinIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
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

const TRIP_DATE_FORMATTER = new Intl.DateTimeFormat(undefined, {
  day: "numeric",
  month: "short",
  timeZone: "UTC",
  year: "numeric",
});

/**
 * Formats date-only trip starts without shifting the displayed day by local timezone.
 *
 * @param value - ISO date or datetime string from the trip summary.
 */
const FORMAT_TRIP_START_DATE = (value: string): string => {
  const dateParts = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  const date = dateParts
    ? new Date(
        Date.UTC(Number(dateParts[1]), Number(dateParts[2]) - 1, Number(dateParts[3]))
      )
    : new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return TRIP_DATE_FORMATTER.format(date);
};

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
  const resetKey = `${isOpen ? "open" : "closed"}:${activity.id}`;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <TripSelectionModalContent
        key={resetKey}
        activity={activity}
        trips={trips}
        onAddToTrip={onAddToTrip}
        onClose={onClose}
        isAdding={isAdding}
      />
    </Dialog>
  );
}

type TripSelectionModalContentProps = Omit<TripSelectionModalProps, "isOpen">;

/**
 * Stateful dialog body that resets selection when React remounts it for a new trip flow.
 *
 * @param props - Component props without the open state owned by the parent dialog.
 */
function TripSelectionModalContent({
  onClose,
  activity,
  trips,
  onAddToTrip,
  isAdding,
}: TripSelectionModalContentProps) {
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

  return (
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
            <Button variant="link" className="mt-2" asChild>
              <Link href="/trips" onClick={onClose}>
                Create a new trip
              </Link>
            </Button>
          </div>
        ) : (
          <ScrollArea className="h-[300px] pr-4">
            <RadioGroup
              value={selectedTripId ?? ""}
              onValueChange={(value) => setSelectedTripId(value === "" ? null : value)}
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
                      <MapPinIcon aria-hidden="true" className="h-3 w-3" />
                      <span>{trip.destination}</span>
                    </div>
                    {trip.startDate && (
                      <div className="flex items-center text-sm text-muted-foreground gap-2">
                        <CalendarIcon aria-hidden="true" className="h-3 w-3" />
                        <span>{FORMAT_TRIP_START_DATE(trip.startDate)}</span>
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
          {isAdding ? "Adding…" : "Add to Trip"}
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}
