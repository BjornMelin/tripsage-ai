/**
 * @fileoverview Trip detail client shell (itinerary, collaborators, settings).
 */

"use client";

import type {
  ItineraryItem,
  ItineraryItemUpsertInput,
  TripSettingsFormData,
} from "@schemas/trips";
import { itineraryItemUpsertSchema, tripSettingsFormSchema } from "@schemas/trips";
import {
  ChevronLeftIcon,
  Loader2Icon,
  PlusIcon,
  SettingsIcon,
  UsersIcon,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { z } from "zod";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";
import { ItineraryItemDialog } from "@/features/trips/components/itinerary-item-dialog";
import { TripCollaboratorsPanel } from "@/features/trips/components/trip-collaborators-panel";
import { TripDetailHeader } from "@/features/trips/components/trip-detail-header";
import { TripItineraryPanel } from "@/features/trips/components/trip-itinerary-panel";
import { TripSettingsPanel } from "@/features/trips/components/trip-settings-panel";
import { useTripCollaborators } from "@/hooks/use-trip-collaborators";
import {
  useDeleteTrip,
  useDeleteTripItineraryItem,
  useTrip,
  useTripItinerary,
  useUpdateTrip,
  useUpsertTripItineraryItem,
} from "@/hooks/use-trips";
import {
  DEFAULT_ITINERARY_DRAFT,
  type ItineraryDraft,
  itineraryDraftFromItem,
} from "@/lib/trips/itinerary-draft";
import { buildPayload, toIsoDateTimeOrUndefined } from "@/lib/trips/trip-detail-utils";

type TripDetailClientProps = {
  tripId: number;
  userId: string;
};

export function TripDetailClient({ tripId, userId }: TripDetailClientProps) {
  const router = useRouter();
  const { toast } = useToast();

  const tripQuery = useTrip(tripId, { userId });
  const itineraryQuery = useTripItinerary(tripId, { userId });
  const collaboratorsQuery = useTripCollaborators(tripId, { userId });

  const updateTripMutation = useUpdateTrip({ userId });
  const deleteTripMutation = useDeleteTrip({ userId });
  const upsertItineraryMutation = useUpsertTripItineraryItem(tripId, { userId });
  const deleteItineraryMutation = useDeleteTripItineraryItem(tripId, { userId });

  const trip = tripQuery.data ?? null;
  const itineraryItems = itineraryQuery.data ?? [];

  const [isDeleteTripOpen, setIsDeleteTripOpen] = useState(false);
  const [isItineraryDialogOpen, setIsItineraryDialogOpen] = useState(false);
  const [draft, setDraft] = useState<ItineraryDraft>(DEFAULT_ITINERARY_DRAFT);
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<
    "itinerary" | "collaborators" | "settings"
  >("itinerary");

  const [settings, setSettings] = useState<TripSettingsFormData>({ title: "" });
  const [settingsInitialized, setSettingsInitialized] = useState(false);

  useEffect(() => {
    if (!trip || settingsInitialized) return;
    setSettings({
      description: trip.description,
      destination: trip.destination,
      endDate: trip.endDate,
      startDate: trip.startDate,
      title: trip.title ?? "",
    });
    setSettingsInitialized(true);
  }, [settingsInitialized, trip]);

  const openNewItineraryDialog = () => {
    setEditingItemId(null);
    setDraft(DEFAULT_ITINERARY_DRAFT);
    setIsItineraryDialogOpen(true);
  };

  const openEditItineraryDialog = (item: ItineraryItem) => {
    setEditingItemId(item.id);
    setDraft(itineraryDraftFromItem(item));
    setIsItineraryDialogOpen(true);
  };

  const closeItineraryDialog = () => {
    setIsItineraryDialogOpen(false);
    setEditingItemId(null);
  };

  const handleUpsertItinerary = async () => {
    const payload = buildPayload(draft.payload);
    const parsedPriceRaw = draft.price.trim()
      ? Number.parseFloat(draft.price)
      : undefined;
    const price =
      parsedPriceRaw !== undefined && Number.isFinite(parsedPriceRaw)
        ? parsedPriceRaw
        : undefined;

    const candidate: ItineraryItemUpsertInput = {
      bookingStatus: draft.bookingStatus,
      currency: draft.currency || "USD",
      description: draft.description.trim() ? draft.description.trim() : undefined,
      endAt: toIsoDateTimeOrUndefined(draft.endAtLocal),
      id: draft.id,
      itemType: draft.itemType,
      location: draft.location.trim() ? draft.location.trim() : undefined,
      payload,
      price,
      startAt: toIsoDateTimeOrUndefined(draft.startAtLocal),
      title: draft.title.trim(),
      tripId,
    };

    const validation = itineraryItemUpsertSchema.safeParse(candidate);
    if (!validation.success) {
      toast({
        description: z.prettifyError(validation.error),
        title: "Invalid itinerary item",
        variant: "destructive",
      });
      return;
    }

    try {
      await upsertItineraryMutation.mutateAsync(validation.data);
      toast({
        description: editingItemId
          ? "Itinerary item updated."
          : "Itinerary item added.",
        title: "Saved",
      });
      closeItineraryDialog();
    } catch (error) {
      toast({
        description:
          error instanceof Error ? error.message : "Unable to save itinerary item",
        title: "Save failed",
        variant: "destructive",
      });
    }
  };

  const handleDeleteItineraryItem = async (itemId: number) => {
    try {
      await deleteItineraryMutation.mutateAsync({ itemId });
      toast({ description: "Itinerary item removed.", title: "Deleted" });
    } catch (error) {
      toast({
        description: error instanceof Error ? error.message : "Unable to delete item",
        title: "Delete failed",
        variant: "destructive",
      });
    }
  };

  const handleSaveTripSettings = async () => {
    const validation = tripSettingsFormSchema.safeParse(settings);
    if (!validation.success) {
      toast({
        description: z.prettifyError(validation.error),
        title: "Invalid trip settings",
        variant: "destructive",
      });
      return;
    }

    try {
      const normalized = {
        description: validation.data.description?.trim() || undefined,
        destination: validation.data.destination?.trim() || undefined,
        endDate: validation.data.endDate,
        startDate: validation.data.startDate,
        title: validation.data.title.trim(),
      };

      await updateTripMutation.mutateAsync({ data: normalized, tripId });
      toast({ description: "Trip updated.", title: "Saved" });
    } catch (error) {
      toast({
        description: error instanceof Error ? error.message : "Unable to update trip",
        title: "Save failed",
        variant: "destructive",
      });
    }
  };

  const handleDeleteTrip = async () => {
    try {
      await deleteTripMutation.mutateAsync(tripId);
      toast({ description: "Trip deleted.", title: "Deleted" });
      setIsDeleteTripOpen(false);
      router.push("/dashboard/trips");
    } catch (error) {
      toast({
        description: error instanceof Error ? error.message : "Unable to delete trip",
        title: "Delete failed",
        variant: "destructive",
      });
    }
  };

  if (tripQuery.isLoading && !trip) {
    return (
      <div className="container mx-auto py-10">
        <Card>
          <CardContent className="flex items-center justify-center gap-2 py-12 text-muted-foreground">
            <Loader2Icon className="h-5 w-5 animate-spin" />
            Loading trip…
          </CardContent>
        </Card>
      </div>
    );
  }

  if (tripQuery.error) {
    return (
      <div className="container mx-auto py-10">
        <Card>
          <CardHeader>
            <CardTitle>Unable to load trip</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>{tripQuery.error.message}</p>
            <Button asChild variant="outline">
              <Link href="/dashboard/trips">
                <ChevronLeftIcon className="mr-2 h-4 w-4" />
                Back to trips
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!trip) {
    return (
      <div className="container mx-auto py-10">
        <Card>
          <CardHeader>
            <CardTitle>Trip not found</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>The trip may have been deleted or you no longer have access.</p>
            <Button asChild variant="outline">
              <Link href="/dashboard/trips">
                <ChevronLeftIcon className="mr-2 h-4 w-4" />
                Back to trips
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const collaboratorCount = collaboratorsQuery.data?.collaborators.length ?? 0;
  const ownerId = collaboratorsQuery.data?.ownerId ?? trip.userId ?? "";
  const isOwner =
    collaboratorsQuery.data?.isOwner ?? (trip.userId ? trip.userId === userId : false);

  return (
    <div className="container mx-auto space-y-6 py-8">
      <TripDetailHeader
        trip={trip}
        collaboratorCount={collaboratorCount}
        isDeleting={deleteTripMutation.isPending}
        onDeleteClick={() => setIsDeleteTripOpen(true)}
      />

      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as typeof activeTab)}
      >
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="itinerary" className="gap-2">
            <PlusIcon className="h-4 w-4" />
            Itinerary
          </TabsTrigger>
          <TabsTrigger value="collaborators" className="gap-2">
            <UsersIcon className="h-4 w-4" />
            Collaborators
          </TabsTrigger>
          <TabsTrigger value="settings" className="gap-2">
            <SettingsIcon className="h-4 w-4" />
            Settings
          </TabsTrigger>
        </TabsList>

        <TabsContent value="itinerary" className="mt-6 space-y-4">
          <TripItineraryPanel
            items={itineraryItems}
            isLoading={itineraryQuery.isLoading}
            error={itineraryQuery.error}
            onAdd={openNewItineraryDialog}
            onEdit={openEditItineraryDialog}
            onDelete={handleDeleteItineraryItem}
            isDeleting={deleteItineraryMutation.isPending}
          />
        </TabsContent>

        <TabsContent value="collaborators" className="mt-6 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Collaborators</CardTitle>
            </CardHeader>
            <CardContent>
              {collaboratorsQuery.isLoading ? (
                <div className="flex items-center justify-center gap-2 py-10 text-muted-foreground">
                  <Loader2Icon className="h-5 w-5 animate-spin" />
                  Loading collaborators…
                </div>
              ) : collaboratorsQuery.error ? (
                <div className="py-10 text-center text-sm text-muted-foreground">
                  Unable to load collaborators.
                </div>
              ) : collaboratorsQuery.data ? (
                <TripCollaboratorsPanel
                  tripId={tripId}
                  ownerId={ownerId}
                  currentUserId={userId}
                  collaborators={collaboratorsQuery.data.collaborators}
                  isOwner={isOwner}
                />
              ) : (
                <div className="py-10 text-center text-sm text-muted-foreground">
                  No collaborators found.
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings" className="mt-6 space-y-4">
          <TripSettingsPanel
            settings={settings}
            setSettings={setSettings}
            isSaving={updateTripMutation.isPending}
            onReset={() => {
              setSettingsInitialized(false);
              toast({ description: "Reset to saved values.", title: "Reset" });
            }}
            onSave={handleSaveTripSettings}
          />
        </TabsContent>
      </Tabs>

      <AlertDialog open={isDeleteTripOpen} onOpenChange={setIsDeleteTripOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this trip?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently deletes the trip and its itinerary. This action cannot be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteTrip}
              className="bg-destructive text-destructive-foreground"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <ItineraryItemDialog
        open={isItineraryDialogOpen}
        onOpenChange={(open) => {
          setIsItineraryDialogOpen(open);
          if (!open) {
            setEditingItemId(null);
          }
        }}
        draft={draft}
        setDraft={setDraft}
        editingItemId={editingItemId}
        onCancel={closeItineraryDialog}
        onSave={handleUpsertItinerary}
        isSaving={upsertItineraryMutation.isPending}
      />
    </div>
  );
}
