/**
 * @fileoverview Selection dialog for a chosen activity.
 */

"use client";

import type { Activity } from "@schemas/search";
import { TicketIcon, XIcon } from "lucide-react";
import type { RefObject } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type ActivitiesSelectionDialogProps = {
  closeButtonRef: RefObject<HTMLButtonElement | null>;
  isPending: boolean;
  isOpen: boolean;
  onAddToTrip: () => void;
  onBookActivity: () => void;
  onClose: () => void;
  primaryActionRef: RefObject<HTMLButtonElement | null>;
  selectedActivity: Activity | null;
};

export function ActivitiesSelectionDialog({
  closeButtonRef,
  isOpen,
  isPending,
  onAddToTrip,
  onBookActivity,
  onClose,
  primaryActionRef,
  selectedActivity,
}: ActivitiesSelectionDialogProps) {
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <TicketIcon className="h-5 w-5" />
            Activity Selected
          </DialogTitle>
          <DialogDescription>{selectedActivity?.name}</DialogDescription>
        </DialogHeader>
        <div className="py-4">
          <p className="text-sm text-muted-foreground">
            What would you like to do with this activity?
          </p>
        </div>
        <DialogFooter className="flex-col sm:flex-row gap-2">
          <Button
            variant="outline"
            ref={closeButtonRef}
            onClick={onClose}
            className="flex-1"
          >
            <XIcon className="h-4 w-4 mr-2" />
            Close
          </Button>
          <Button
            ref={primaryActionRef}
            onClick={onAddToTrip}
            disabled={isPending}
            className="flex-1"
          >
            {isPending ? "Loading..." : "Add to Trip"}
          </Button>
          <Button variant="secondary" onClick={onBookActivity} className="flex-1">
            Book Now
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
