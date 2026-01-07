/**
 * @fileoverview Dialog for creating or editing itinerary items (typed payloads).
 */

"use client";

import { itineraryItemTypeSchema } from "@schemas/trips";
import { Loader2Icon } from "lucide-react";
import type { Dispatch, SetStateAction } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import type { ItineraryDraft } from "@/lib/trips/itinerary-draft";
import type { BookingStatus } from "@/lib/trips/trip-detail-utils";

type ItineraryItemDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  draft: ItineraryDraft;
  setDraft: Dispatch<SetStateAction<ItineraryDraft>>;
  editingItemId: number | null;
  onCancel: () => void;
  onSave: () => void;
  isSaving: boolean;
};

export function ItineraryItemDialog({
  open,
  onOpenChange,
  draft,
  setDraft,
  editingItemId,
  onCancel,
  onSave,
  isSaving,
}: ItineraryItemDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>
            {editingItemId ? "Edit itinerary item" : "Add itinerary item"}
          </DialogTitle>
          <DialogDescription>
            Keep the details lightweight. You can refine later while planning.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>Type</Label>
              <Select
                value={draft.itemType}
                onValueChange={(value) => {
                  const parsed = itineraryItemTypeSchema.safeParse(value);
                  if (!parsed.success) return;
                  setDraft((prev) => ({ ...prev, itemType: parsed.data }));
                }}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="activity">Activity</SelectItem>
                  <SelectItem value="meal">Meal</SelectItem>
                  <SelectItem value="transport">Transport</SelectItem>
                  <SelectItem value="accommodation">Accommodation</SelectItem>
                  <SelectItem value="event">Event</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Status</Label>
              <Select
                value={draft.bookingStatus}
                onValueChange={(value) =>
                  setDraft((prev) => ({
                    ...prev,
                    bookingStatus: value as BookingStatus,
                  }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="planned">Planned</SelectItem>
                  <SelectItem value="reserved">Reserved</SelectItem>
                  <SelectItem value="booked">Booked</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="it-title">Title</Label>
            <Input
              id="it-title"
              value={draft.title}
              onChange={(e) => setDraft((prev) => ({ ...prev, title: e.target.value }))}
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="it-start">Start</Label>
              <Input
                id="it-start"
                type="datetime-local"
                value={draft.startAtLocal}
                onChange={(e) =>
                  setDraft((prev) => ({ ...prev, startAtLocal: e.target.value }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="it-end">End</Label>
              <Input
                id="it-end"
                type="datetime-local"
                value={draft.endAtLocal}
                onChange={(e) =>
                  setDraft((prev) => ({ ...prev, endAtLocal: e.target.value }))
                }
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="it-location">Location</Label>
              <Input
                id="it-location"
                value={draft.location}
                onChange={(e) =>
                  setDraft((prev) => ({ ...prev, location: e.target.value }))
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="it-price">Price</Label>
              <Input
                id="it-price"
                type="number"
                min={0}
                value={draft.price}
                onChange={(e) =>
                  setDraft((prev) => ({ ...prev, price: e.target.value }))
                }
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="it-description">Description</Label>
            <Textarea
              id="it-description"
              value={draft.description}
              onChange={(e) =>
                setDraft((prev) => ({ ...prev, description: e.target.value }))
              }
              rows={3}
            />
          </div>

          <Separator />

          <div className="space-y-3">
            <div className="space-y-1">
              <div className="text-sm font-medium">Typed details</div>
              <div className="text-xs text-muted-foreground">
                Optional fields that power structured itinerary payloads.
              </div>
            </div>

            {draft.itemType === "transport" ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label>Mode</Label>
                  <Select
                    value={draft.payload.mode ?? ""}
                    onValueChange={(value) =>
                      setDraft((prev) => ({
                        ...prev,
                        payload: { ...prev.payload, mode: value },
                      }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select mode" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="flight">Flight</SelectItem>
                      <SelectItem value="train">Train</SelectItem>
                      <SelectItem value="car">Car</SelectItem>
                      <SelectItem value="bus">Bus</SelectItem>
                      <SelectItem value="ferry">Ferry</SelectItem>
                      <SelectItem value="walk">Walk</SelectItem>
                      <SelectItem value="rideshare">Rideshare</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="it-transport-ref">Booking reference</Label>
                  <Input
                    id="it-transport-ref"
                    value={draft.payload.bookingReference ?? ""}
                    onChange={(e) =>
                      setDraft((prev) => ({
                        ...prev,
                        payload: { ...prev.payload, bookingReference: e.target.value },
                      }))
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="it-transport-from">From</Label>
                  <Input
                    id="it-transport-from"
                    value={draft.payload.from ?? ""}
                    onChange={(e) =>
                      setDraft((prev) => ({
                        ...prev,
                        payload: { ...prev.payload, from: e.target.value },
                      }))
                    }
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="it-transport-to">To</Label>
                  <Input
                    id="it-transport-to"
                    value={draft.payload.to ?? ""}
                    onChange={(e) =>
                      setDraft((prev) => ({
                        ...prev,
                        payload: { ...prev.payload, to: e.target.value },
                      }))
                    }
                  />
                </div>
              </div>
            ) : draft.itemType === "activity" ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="it-activity-provider">Provider</Label>
                  <Input
                    id="it-activity-provider"
                    value={draft.payload.provider ?? ""}
                    onChange={(e) =>
                      setDraft((prev) => ({
                        ...prev,
                        payload: { ...prev.payload, provider: e.target.value },
                      }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="it-activity-place">Place id</Label>
                  <Input
                    id="it-activity-place"
                    value={draft.payload.placeId ?? ""}
                    onChange={(e) =>
                      setDraft((prev) => ({
                        ...prev,
                        payload: { ...prev.payload, placeId: e.target.value },
                      }))
                    }
                  />
                </div>
              </div>
            ) : draft.itemType === "accommodation" ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="it-accommodation-name">Property name</Label>
                  <Input
                    id="it-accommodation-name"
                    value={draft.payload.propertyName ?? ""}
                    onChange={(e) =>
                      setDraft((prev) => ({
                        ...prev,
                        payload: { ...prev.payload, propertyName: e.target.value },
                      }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="it-accommodation-provider">Provider</Label>
                  <Input
                    id="it-accommodation-provider"
                    value={draft.payload.provider ?? ""}
                    onChange={(e) =>
                      setDraft((prev) => ({
                        ...prev,
                        payload: { ...prev.payload, provider: e.target.value },
                      }))
                    }
                  />
                </div>
              </div>
            ) : draft.itemType === "event" ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="it-event-organizer">Organizer</Label>
                  <Input
                    id="it-event-organizer"
                    value={draft.payload.organizer ?? ""}
                    onChange={(e) =>
                      setDraft((prev) => ({
                        ...prev,
                        payload: { ...prev.payload, organizer: e.target.value },
                      }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="it-event-id">Event id</Label>
                  <Input
                    id="it-event-id"
                    value={draft.payload.eventId ?? ""}
                    onChange={(e) =>
                      setDraft((prev) => ({
                        ...prev,
                        payload: { ...prev.payload, eventId: e.target.value },
                      }))
                    }
                  />
                </div>
              </div>
            ) : draft.itemType === "meal" ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="it-meal-cuisine">Cuisine</Label>
                  <Input
                    id="it-meal-cuisine"
                    value={draft.payload.cuisine ?? ""}
                    onChange={(e) =>
                      setDraft((prev) => ({
                        ...prev,
                        payload: { ...prev.payload, cuisine: e.target.value },
                      }))
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="it-meal-reservation">Reservation name</Label>
                  <Input
                    id="it-meal-reservation"
                    value={draft.payload.reservationName ?? ""}
                    onChange={(e) =>
                      setDraft((prev) => ({
                        ...prev,
                        payload: { ...prev.payload, reservationName: e.target.value },
                      }))
                    }
                  />
                </div>
              </div>
            ) : null}

            <div className="space-y-2">
              <Label htmlFor="it-url">Link</Label>
              <Input
                id="it-url"
                placeholder="https://…"
                value={
                  draft.itemType === "event"
                    ? (draft.payload.ticketsUrl ?? "")
                    : (draft.payload.url ?? "")
                }
                onChange={(e) => {
                  const nextValue = e.target.value;
                  setDraft((prev) => ({
                    ...prev,
                    payload: {
                      ...prev.payload,
                      ...(prev.itemType === "event"
                        ? { ticketsUrl: nextValue }
                        : { url: nextValue }),
                    },
                  }));
                }}
              />
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="button" onClick={onSave} disabled={isSaving}>
            {isSaving ? <Loader2Icon className="mr-2 h-4 w-4 animate-spin" /> : null}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
