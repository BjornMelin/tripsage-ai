"use client";

import { Clock, MapPin, Star } from "lucide-react";
import Image from "next/image";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import type { Activity } from "@/types/search";

interface ActivityCardProps {
  activity: Activity;
  onSelect?: (activity: Activity) => void;
  onCompare?: (activity: Activity) => void;
}

export function ActivityCard({ activity, onSelect, onCompare }: ActivityCardProps) {
  const formatDuration = (hours: number) => {
    if (hours < 1) {
      return `${Math.round(hours * 60)} mins`;
    }
    if (hours === 1) {
      return "1 hour";
    }
    if (hours < 24) {
      return `${hours} hours`;
    }
    const days = Math.floor(hours / 24);
    const remainingHours = hours % 24;
    if (remainingHours === 0) {
      return `${days} ${days === 1 ? "day" : "days"}`;
    }
    return `${days}d ${remainingHours}h`;
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(price);
  };

  const renderStars = (rating: number) => {
    const stars = [];
    for (let i = 0; i < 5; i++) {
      stars.push(
        <Star
          key={`star-${i}`}
          className={`h-4 w-4 ${
            i < Math.floor(rating) ? "fill-yellow-400 text-yellow-400" : "text-gray-300"
          }`}
        />
      );
    }
    return stars;
  };

  return (
    <Card className="overflow-hidden hover:shadow-lg transition-shadow">
      <div className="relative">
        {activity.images && activity.images.length > 0 ? (
          <Image
            src={activity.images[0]}
            alt={activity.name}
            width={1200}
            height={480}
            className="w-full h-48 object-cover"
          />
        ) : (
          <div className="w-full h-48 bg-gray-200 flex items-center justify-center">
            <MapPin className="h-12 w-12 text-gray-400" />
          </div>
        )}
        <div className="absolute top-2 left-2">
          <Badge variant="secondary" className="bg-white/90">
            {activity.type}
          </Badge>
        </div>
        <div className="absolute top-2 right-2">
          <Badge variant="outline" className="bg-white/90">
            {formatPrice(activity.price)}
          </Badge>
        </div>
      </div>

      <CardContent className="p-4">
        <div className="space-y-2">
          <h3 className="font-semibold text-lg line-clamp-1">{activity.name}</h3>

          <div className="flex items-center gap-1">
            {renderStars(activity.rating)}
            <span className="text-sm text-muted-foreground ml-1">
              ({activity.rating})
            </span>
          </div>

          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1">
              <Clock className="h-4 w-4" />
              <span>{formatDuration(activity.duration)}</span>
            </div>
            <div className="flex items-center gap-1">
              <MapPin className="h-4 w-4" />
              <span className="line-clamp-1">{activity.location}</span>
            </div>
          </div>

          <p className="text-sm text-muted-foreground line-clamp-2">
            {activity.description}
          </p>

          <div className="pt-2">
            <div className="text-lg font-semibold text-primary">
              {formatPrice(activity.price)}
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
