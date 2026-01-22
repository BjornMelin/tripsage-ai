/**
 * @fileoverview Trip itinerary tab panel (table + empty/loading states).
 */

"use client";

import type { ItineraryItem } from "@schemas/trips";
import { Loader2Icon, PlusIcon, Trash2Icon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  bookingStatusLabel,
  formatItineraryTimestamp,
} from "@/lib/trips/trip-detail-utils";

type TripItineraryPanelProps = {
  items: ItineraryItem[];
  isLoading: boolean;
  error: Error | null;
  onAdd: () => void;
  onEdit: (item: ItineraryItem) => void;
  onDelete: (itemId: number) => void;
  isDeleting: boolean;
};

export function TripItineraryPanel({
  items,
  isLoading,
  error,
  onAdd,
  onEdit,
  onDelete,
  isDeleting,
}: TripItineraryPanelProps) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold">Itinerary</h2>
          <p className="text-sm text-muted-foreground">
            Add activities, meals, transport, accommodations, and more.
          </p>
        </div>
        <Button type="button" onClick={onAdd}>
          <PlusIcon aria-hidden="true" className="mr-2 h-4 w-4" />
          Add item
        </Button>
      </div>

      <Card>
        <CardContent className="pt-6">
          {isLoading ? (
            <div className="flex items-center justify-center gap-2 py-10 text-muted-foreground">
              <Loader2Icon aria-hidden="true" className="h-5 w-5 animate-spin" />
              Loading itinerary…
            </div>
          ) : error ? (
            <div className="py-10 text-center text-sm text-muted-foreground">
              Unable to load itinerary items.
            </div>
          ) : items.length === 0 ? (
            <div className="py-10 text-center text-sm text-muted-foreground">
              No itinerary items yet. Add your first item to get started.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Title</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="min-w-[190px]">
                      <div className="space-y-1">
                        <div className="text-sm font-medium">
                          {formatItineraryTimestamp(item.startAt)}
                        </div>
                        {item.endAt ? (
                          <div className="text-xs text-muted-foreground">
                            → {formatItineraryTimestamp(item.endAt)}
                          </div>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell className="capitalize">{item.itemType}</TableCell>
                    <TableCell className="min-w-[220px]">
                      <div className="space-y-1">
                        <div className="font-medium">{item.title}</div>
                        {item.location ? (
                          <div className="text-xs text-muted-foreground">
                            {item.location}
                          </div>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">
                        {bookingStatusLabel(item.bookingStatus)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => onEdit(item)}
                        >
                          Edit
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          className="text-destructive hover:text-destructive"
                          onClick={() => onDelete(item.id)}
                          disabled={isDeleting}
                        >
                          <Trash2Icon aria-hidden="true" className="h-4 w-4" />
                          <span className="sr-only">Delete</span>
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
