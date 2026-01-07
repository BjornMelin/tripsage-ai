/**
 * @fileoverview Trip places panel (search + saved places) backed by canonical Places DTOs.
 */

"use client";

import type { PlaceSummary } from "@schemas/places";
import { searchPlacesResultSchema } from "@schemas/places";
import {
  BookmarkPlusIcon,
  ExternalLinkIcon,
  Loader2Icon,
  MapPinIcon,
  SearchIcon,
  StarIcon,
  Trash2Icon,
} from "lucide-react";
import Image from "next/image";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { useRemoveSavedPlace, useSavedPlaces, useSavePlace } from "@/hooks/use-trips";
import { getErrorMessage } from "@/lib/api/error-types";
import { fireAndForget } from "@/lib/utils";

type TripPlacesPanelProps = {
  tripId: number;
  userId: string;
};

function NormalizePlaceId(placeId: string): string {
  return placeId.startsWith("places/") ? placeId.slice("places/".length) : placeId;
}

function PhotoUrlForName(photoName: string): string {
  return `/api/places/photo?${new URLSearchParams({
    maxHeightPx: "400",
    maxWidthPx: "400",
    name: photoName,
  }).toString()}`;
}

export function TripPlacesPanel({ tripId, userId }: TripPlacesPanelProps) {
  const { toast } = useToast();

  const savedPlacesQuery = useSavedPlaces(tripId, { userId });
  const savePlaceMutation = useSavePlace(tripId, { userId });
  const removePlaceMutation = useRemoveSavedPlace(tripId, { userId });

  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PlaceSummary[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      abortRef.current = null;
    };
  }, []);

  const savedPlaceIds = useMemo(() => {
    const ids = new Set<string>();
    for (const item of savedPlacesQuery.data ?? []) {
      ids.add(NormalizePlaceId(item.place.placeId));
    }
    return ids;
  }, [savedPlacesQuery.data]);

  const performSearch = useCallback(async () => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setResults([]);
      setSearchError(null);
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setIsSearching(true);
    setSearchError(null);

    try {
      const response = await fetch("/api/places/search", {
        body: JSON.stringify({ maxResultCount: 10, textQuery: trimmed }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
        signal: controller.signal,
      });

      if (!response.ok) {
        const errorJson: unknown = await response.json().catch(() => null);
        const reason =
          errorJson && typeof errorJson === "object"
            ? (errorJson as { reason?: unknown }).reason
            : undefined;
        const message =
          typeof reason === "string" ? reason : `Search failed (${response.status})`;
        throw new Error(message);
      }

      const dataJson: unknown = await response.json();
      const parsed = searchPlacesResultSchema.safeParse(dataJson);
      if (!parsed.success) {
        throw new Error("Unexpected response from places search.");
      }

      setResults(parsed.data.places);
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") return;
      const message = getErrorMessage(error);
      setSearchError(message);
      setResults([]);
      toast({
        description: message,
        title: "Places search failed",
        variant: "destructive",
      });
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
      }
      setIsSearching(false);
    }
  }, [query, toast]);

  const handleSavePlace = useCallback(
    async (place: PlaceSummary) => {
      try {
        await savePlaceMutation.mutateAsync({ place });
        toast({
          description: `Saved "${place.name}" to this trip.`,
          title: "Place saved",
        });
      } catch (error) {
        toast({
          description: getErrorMessage(error),
          title: "Save failed",
          variant: "destructive",
        });
      }
    },
    [savePlaceMutation, toast]
  );

  const handleRemovePlace = useCallback(
    async (placeId: string, name?: string) => {
      try {
        await removePlaceMutation.mutateAsync({ placeId });
        toast({
          description: name
            ? `Removed "${name}" from saved places.`
            : "Removed saved place.",
          title: "Removed",
        });
      } catch (error) {
        toast({
          description: getErrorMessage(error),
          title: "Remove failed",
          variant: "destructive",
        });
      }
    },
    [removePlaceMutation, toast]
  );

  const savedPlaces = savedPlacesQuery.data ?? [];

  return (
    <div className="grid gap-4 lg:grid-cols-5">
      <Card className="lg:col-span-3 overflow-hidden border-primary/15">
        <CardHeader className="relative">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(80%_120%_at_10%_0%,hsl(var(--primary)/0.12)_0%,transparent_55%),radial-gradient(70%_100%_at_90%_20%,hsl(var(--secondary)/0.14)_0%,transparent_60%)]" />
          <CardTitle className="relative flex items-center gap-2">
            <SearchIcon className="h-5 w-5" />
            Search places
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="relative flex-1">
              <MapPinIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault();
                    fireAndForget(performSearch());
                  }
                }}
                placeholder='Try "coffee", "museum", "sushi", "bookstore"...'
                className="pl-9"
                aria-label="Search places"
              />
            </div>
            <Button
              onClick={() => fireAndForget(performSearch())}
              disabled={isSearching}
            >
              {isSearching ? (
                <>
                  <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
                  Searching
                </>
              ) : (
                "Search"
              )}
            </Button>
          </div>

          {searchError && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {searchError}
            </div>
          )}

          <Separator />

          {isSearching && results.length === 0 ? (
            <div className="space-y-3">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : results.length === 0 ? (
            <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
              Search for places to add them to your trip. Results are cached for a short
              time to keep it fast.
            </div>
          ) : (
            <div className="space-y-3">
              {results.map((place) => {
                const normalizedId = NormalizePlaceId(place.placeId);
                const isSaved = savedPlaceIds.has(normalizedId);
                const photoName = place.photoName;
                const imageSrc = photoName ? PhotoUrlForName(photoName) : null;

                return (
                  <div
                    key={normalizedId}
                    className="group flex items-stretch gap-3 rounded-lg border bg-card/40 p-3 transition-colors hover:bg-card"
                  >
                    <div className="relative h-14 w-14 shrink-0 overflow-hidden rounded-md bg-muted">
                      {imageSrc ? (
                        <Image
                          alt={place.name}
                          src={imageSrc}
                          fill
                          className="object-cover"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">
                          —
                        </div>
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                        <div className="min-w-0 font-medium leading-tight">
                          <span className="line-clamp-1">{place.name}</span>
                        </div>
                        {typeof place.rating === "number" && (
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <StarIcon className="h-3.5 w-3.5 fill-yellow-400 text-yellow-400" />
                            <span>{place.rating.toFixed(1)}</span>
                            {typeof place.userRatingCount === "number" && (
                              <span className="text-muted-foreground/70">
                                ({place.userRatingCount.toLocaleString()})
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                      {place.formattedAddress && (
                        <p className="mt-1 line-clamp-1 text-sm text-muted-foreground">
                          {place.formattedAddress}
                        </p>
                      )}
                      {place.types.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {place.types.slice(0, 3).map((type) => (
                            <Badge
                              key={`${normalizedId}:${type}`}
                              variant="secondary"
                              className="px-2 py-0 text-[11px]"
                            >
                              {type.replaceAll("_", " ")}
                            </Badge>
                          ))}
                          {place.types.length > 3 && (
                            <Badge variant="outline" className="px-2 py-0 text-[11px]">
                              +{place.types.length - 3}
                            </Badge>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="flex shrink-0 items-center gap-2">
                      {place.url && (
                        <Button asChild variant="ghost" size="icon">
                          <a
                            href={place.url}
                            target="_blank"
                            rel="noreferrer"
                            aria-label="Open in Maps"
                          >
                            <ExternalLinkIcon className="h-4 w-4" />
                          </a>
                        </Button>
                      )}
                      <Button
                        variant={isSaved ? "secondary" : "default"}
                        disabled={isSaved || savePlaceMutation.isPending}
                        onClick={() => fireAndForget(handleSavePlace(place))}
                        className="gap-2"
                      >
                        <BookmarkPlusIcon className="h-4 w-4" />
                        {isSaved ? "Saved" : "Save"}
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="lg:col-span-2 overflow-hidden border-primary/10">
        <CardHeader className="relative">
          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,hsl(var(--primary)/0.08),transparent_65%)]" />
          <CardTitle className="relative flex items-center justify-between gap-2">
            <span className="flex items-center gap-2">
              <BookmarkPlusIcon className="h-5 w-5" />
              Saved places
            </span>
            <Badge variant="secondary">{savedPlaces.length}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {savedPlacesQuery.isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-14 w-full" />
              <Skeleton className="h-14 w-full" />
              <Skeleton className="h-14 w-full" />
            </div>
          ) : savedPlacesQuery.error ? (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {savedPlacesQuery.error.message}
            </div>
          ) : savedPlaces.length === 0 ? (
            <div className="rounded-lg border border-dashed p-6 text-center text-sm text-muted-foreground">
              Save places you want to remember — restaurants, POIs, and anything you
              might build into your itinerary.
            </div>
          ) : (
            <ScrollArea className="h-[420px] pr-3">
              <div className="space-y-3">
                {savedPlaces.map((item) => {
                  const place = item.place;
                  const normalizedId = NormalizePlaceId(place.placeId);
                  const photoName = place.photoName;
                  const imageSrc = photoName ? PhotoUrlForName(photoName) : null;

                  return (
                    <div
                      key={normalizedId}
                      className="group flex items-stretch gap-3 rounded-lg border bg-card/40 p-3 transition-colors hover:bg-card"
                    >
                      <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-md bg-muted">
                        {imageSrc ? (
                          <Image
                            alt={place.name}
                            src={imageSrc}
                            fill
                            className="object-cover"
                          />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center text-xs text-muted-foreground">
                            —
                          </div>
                        )}
                      </div>

                      <div className="min-w-0 flex-1">
                        <p className="line-clamp-1 font-medium">{place.name}</p>
                        {place.formattedAddress && (
                          <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">
                            {place.formattedAddress}
                          </p>
                        )}
                        {item.savedAt && (
                          <p className="mt-1 text-[11px] text-muted-foreground/70">
                            Saved {new Date(item.savedAt).toLocaleString()}
                          </p>
                        )}
                      </div>

                      <div className="flex shrink-0 items-center gap-1">
                        {place.url && (
                          <Button asChild variant="ghost" size="icon">
                            <a
                              href={place.url}
                              target="_blank"
                              rel="noreferrer"
                              aria-label="Open in Maps"
                            >
                              <ExternalLinkIcon className="h-4 w-4" />
                            </a>
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          disabled={removePlaceMutation.isPending}
                          onClick={() =>
                            fireAndForget(handleRemovePlace(place.placeId, place.name))
                          }
                          aria-label="Remove saved place"
                        >
                          <Trash2Icon className="h-4 w-4 text-muted-foreground group-hover:text-destructive" />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
