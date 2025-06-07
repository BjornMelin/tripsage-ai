"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { type Destination, type Trip, useTripStore } from "@/stores/trip-store";
import { differenceInDays, format, parseISO } from "date-fns";
import { Calendar, Car, Clock, Edit2, MapPin, Plane, Plus, Train } from "lucide-react";
import { useMemo } from "react";

interface TripTimelineProps {
  trip: Trip;
  onEditDestination?: (destination: Destination) => void;
  onAddDestination?: () => void;
  className?: string;
  showActions?: boolean;
}

interface TimelineEvent {
  id: string;
  type: "arrival" | "departure" | "activity" | "accommodation";
  date: Date;
  title: string;
  description?: string;
  location: string;
  destination: Destination;
  icon: React.ReactNode;
}

export function TripTimeline({
  trip,
  onEditDestination,
  onAddDestination,
  className,
  showActions = true,
}: TripTimelineProps) {
  const timelineEvents = useMemo(() => {
    const events: TimelineEvent[] = [];

    trip.destinations.forEach((destination, index) => {
      const startDate = destination.startDate ? parseISO(destination.startDate) : null;
      const endDate = destination.endDate ? parseISO(destination.endDate) : null;

      // Arrival event
      if (startDate) {
        const transportIcon =
          destination.transportation?.type === "flight" ? (
            <Plane className="h-4 w-4" />
          ) : destination.transportation?.type === "car" ? (
            <Car className="h-4 w-4" />
          ) : destination.transportation?.type === "train" ? (
            <Train className="h-4 w-4" />
          ) : (
            <MapPin className="h-4 w-4" />
          );

        events.push({
          id: `arrival-${destination.id}`,
          type: "arrival",
          date: startDate,
          title: `Arrive in ${destination.name}`,
          description: destination.transportation?.details,
          location: `${destination.name}, ${destination.country}`,
          destination,
          icon: transportIcon,
        });
      }

      // Activities
      if (destination.activities && destination.activities.length > 0) {
        destination.activities.forEach((activity, activityIndex) => {
          // For activities without specific dates, distribute them across the stay
          const activityDate =
            startDate && endDate
              ? new Date(
                  startDate.getTime() +
                    ((activityIndex + 1) * (endDate.getTime() - startDate.getTime())) /
                      ((destination.activities?.length ?? 0) + 1)
                )
              : startDate || new Date();

          events.push({
            id: `activity-${destination.id}-${activityIndex}`,
            type: "activity",
            date: activityDate,
            title: activity,
            location: `${destination.name}, ${destination.country}`,
            destination,
            icon: <Calendar className="h-4 w-4" />,
          });
        });
      }

      // Departure event
      if (endDate && index < trip.destinations.length - 1) {
        const nextDestination = trip.destinations[index + 1];
        events.push({
          id: `departure-${destination.id}`,
          type: "departure",
          date: endDate,
          title: `Leave ${destination.name}`,
          description: nextDestination
            ? `Heading to ${nextDestination.name}`
            : undefined,
          location: `${destination.name}, ${destination.country}`,
          destination,
          icon: <Plane className="h-4 w-4" />,
        });
      }
    });

    return events.sort((a, b) => a.date.getTime() - b.date.getTime());
  }, [trip.destinations]);

  const formatEventDate = (date: Date) => {
    return format(date, "MMM dd, yyyy");
  };

  const formatEventTime = (date: Date) => {
    return format(date, "h:mm a");
  };

  const getEventColor = (type: TimelineEvent["type"]) => {
    switch (type) {
      case "arrival":
        return "border-green-200 bg-green-50";
      case "departure":
        return "border-red-200 bg-red-50";
      case "activity":
        return "border-blue-200 bg-blue-50";
      case "accommodation":
        return "border-purple-200 bg-purple-50";
      default:
        return "border-gray-200 bg-gray-50";
    }
  };

  const getDuration = () => {
    if (!trip.startDate || !trip.endDate) return null;
    const start = parseISO(trip.startDate);
    const end = parseISO(trip.endDate);
    return differenceInDays(end, start) + 1;
  };

  const duration = getDuration();

  if (timelineEvents.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Trip Timeline
          </CardTitle>
          <CardDescription>No destinations planned yet</CardDescription>
        </CardHeader>
        <CardContent>
          {showActions && onAddDestination && (
            <Button onClick={onAddDestination} className="w-full">
              <Plus className="h-4 w-4 mr-2" />
              Add First Destination
            </Button>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5" />
          Trip Timeline
        </CardTitle>
        <CardDescription>
          {trip.destinations.length} destination
          {trip.destinations.length !== 1 ? "s" : ""}
          {duration && ` • ${duration} days`}
        </CardDescription>
      </CardHeader>

      <CardContent>
        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-border" />

          <div className="space-y-6">
            {timelineEvents.map((event, index) => (
              <div key={event.id} className="relative flex items-start gap-4">
                {/* Timeline dot */}
                <div
                  className={`
                  relative z-10 flex h-12 w-12 items-center justify-center rounded-full border-2
                  ${getEventColor(event.type)}
                `}
                >
                  {event.icon}
                </div>

                {/* Event content */}
                <div className="flex-1 min-w-0 pb-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <h4 className="font-semibold text-sm">{event.title}</h4>
                      <Badge variant="outline" className="text-xs">
                        {event.type}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatEventDate(event.date)}
                    </div>
                  </div>

                  <div className="mt-1 space-y-1">
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <MapPin className="h-3 w-3" />
                      <span>{event.location}</span>
                    </div>

                    {event.description && (
                      <p className="text-sm text-muted-foreground">
                        {event.description}
                      </p>
                    )}

                    {/* Destination details */}
                    <div className="mt-2 space-y-1">
                      {event.destination.accommodation && (
                        <div className="text-xs text-muted-foreground">
                          Stay: {event.destination.accommodation.name}
                          {event.destination.accommodation.price && (
                            <span className="ml-1">
                              (${event.destination.accommodation.price}/night)
                            </span>
                          )}
                        </div>
                      )}

                      {event.destination.estimatedCost && (
                        <div className="text-xs text-muted-foreground">
                          Estimated cost: ${event.destination.estimatedCost}
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    {showActions && onEditDestination && (
                      <div className="mt-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onEditDestination(event.destination)}
                          className="h-6 px-2 text-xs"
                        >
                          <Edit2 className="h-3 w-3 mr-1" />
                          Edit
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Add destination button */}
        {showActions && onAddDestination && (
          <>
            <Separator className="my-4" />
            <Button variant="outline" onClick={onAddDestination} className="w-full">
              <Plus className="h-4 w-4 mr-2" />
              Add Destination
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}
