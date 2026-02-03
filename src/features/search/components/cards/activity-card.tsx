/**
 * @fileoverview Activity card component for rendering search results with actions.
 */

"use client";

import type { Activity } from "@schemas/search";
import { ClockIcon, MapPinIcon } from "lucide-react";
import Image from "next/image";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import {
  buildImageProxyUrl,
  isAbsoluteHttpUrl,
  normalizeNextImageSrc,
} from "@/lib/images/image-proxy";
import { formatCurrency, formatDurationHours } from "../common/format";
import { RatingStars } from "./rating-stars";

interface ActivityCardProps {
  activity: Activity;
  onSelect?: (activity: Activity) => void;
  onCompare?: (activity: Activity) => void;
  /** Optional source label to display (e.g., "Verified via Google Places" or "AI suggestion"). */
  sourceLabel?: string;
}

export function ActivityCard({
  activity,
  onSelect,
  onCompare,
  sourceLabel,
}: ActivityCardProps) {
  const normalizedPrimaryImage = normalizeNextImageSrc(activity.images?.[0]);
  const imageSrc =
    normalizedPrimaryImage && isAbsoluteHttpUrl(normalizedPrimaryImage)
      ? buildImageProxyUrl(normalizedPrimaryImage)
      : normalizedPrimaryImage;

  const durationLabel =
    Number.isFinite(activity.duration) && activity.duration >= 0
      ? formatDurationHours(activity.duration)
      : "N/A";

  return (
    <Card className="overflow-hidden hover:shadow-lg transition-shadow">
      <div className="relative">
        {imageSrc ? (
          <Image
            src={imageSrc}
            alt={activity.name}
            width={1200}
            height={480}
            className="w-full h-48 object-cover"
            sizes="(max-width: 768px) 100vw, 600px"
          />
        ) : (
          <div className="w-full h-48 bg-muted flex items-center justify-center">
            <MapPinIcon className="h-12 w-12 text-muted-foreground" />
          </div>
        )}
        <div className="absolute top-2 left-2 flex flex-col gap-1">
          <Badge variant="secondary" className="bg-background/90">
            {activity.type}
          </Badge>
          {sourceLabel && (
            <Badge
              variant={activity.id.startsWith("ai_fallback:") ? "outline" : "default"}
              className="bg-background/90 text-xs"
            >
              {sourceLabel}
            </Badge>
          )}
        </div>
        <div className="absolute top-2 right-2">
          <Badge variant="outline" className="bg-background/90">
            {formatCurrency(activity.price)}
          </Badge>
        </div>
      </div>

      <CardContent className="p-4">
        <div className="space-y-2">
          <h3 className="font-semibold text-lg line-clamp-1">{activity.name}</h3>

          <div className="flex items-center gap-1">
            <RatingStars value={activity.rating} />
            <span className="text-sm text-muted-foreground ml-1">
              ({activity.rating})
            </span>
          </div>

          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <ClockIcon className="h-4 w-4" />
              <span>{durationLabel}</span>
            </div>
            <div className="flex items-center gap-1">
              <MapPinIcon className="h-4 w-4" />
              <span className="line-clamp-1">{activity.location}</span>
            </div>
          </div>

          <p className="text-sm text-muted-foreground line-clamp-2">
            {activity.description}
          </p>

          <div className="pt-2">
            <div className="text-lg font-semibold text-primary">
              {formatCurrency(activity.price)}
              <span className="text-sm font-normal text-muted-foreground">
                {" "}
                per person
              </span>
            </div>
          </div>
        </div>
      </CardContent>

      <CardFooter className="p-4 pt-0 gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onCompare?.(activity)}
          className="flex-1"
        >
          Compare
        </Button>
        <Button size="sm" onClick={() => onSelect?.(activity)} className="flex-1">
          Select
        </Button>
      </CardFooter>
    </Card>
  );
}
