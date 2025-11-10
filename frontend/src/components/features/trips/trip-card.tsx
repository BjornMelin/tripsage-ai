"use client";

import { differenceInDays, format } from "date-fns";
import { Calendar, DollarSign, MapPin } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useBudgetStore } from "@/stores/budget-store";
import type { Trip } from "@/stores/trip-store";

interface TripCardProps {
  trip: Trip;
  onEdit?: (trip: Trip) => void;
  onDelete?: (tripId: string) => void;
  className?: string;
}

export function TripCard({ trip, onEdit, onDelete, className }: TripCardProps) {
  const { budgetsByTrip } = useBudgetStore();
  const tripBudgets = budgetsByTrip[trip.id] || [];

  const startDate = trip.startDate ? new Date(trip.startDate) : null;
  const endDate = trip.endDate ? new Date(trip.endDate) : null;
  const duration =
    startDate && endDate ? differenceInDays(endDate, startDate) + 1 : null;

  const formatDate = (dateString?: string) => {
    if (!dateString) return "Not set";
    return format(new Date(dateString), "MMM dd, yyyy");
  };

  const getTripStatus = () => {
    if (!startDate || !endDate) return "draft";
    const now = new Date();
    if (now < startDate) return "upcoming";
    if (now > endDate) return "completed";
    return "active";
  };

  const status = getTripStatus();
  const statusColors = {
    active: "bg-green-100 text-green-700",
    completed: "bg-gray-100 text-gray-500",
    draft: "bg-gray-100 text-gray-700",
    upcoming: "bg-blue-100 text-blue-700",
  };

  return (
    <Card
      className={`group hover:shadow-lg transition-shadow duration-200 ${className || ""}`}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <Badge className={statusColors[status]}>
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </Badge>
          {trip.isPublic && <Badge variant="outline">Public</Badge>}
        </div>
        <CardTitle className="line-clamp-1">{trip.name}</CardTitle>
        {trip.description && (
          <CardDescription className="line-clamp-2">{trip.description}</CardDescription>
        )}
      </CardHeader>

      <CardContent className="space-y-3">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Calendar className="h-4 w-4" />
          <span>
            {formatDate(trip.startDate)} - {formatDate(trip.endDate)}
            {duration && <span className="ml-1">({duration} days)</span>}
          </span>
        </div>

        {trip.destinations.length > 0 && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <MapPin className="h-4 w-4" />
            <span className="line-clamp-1">
              {trip.destinations.length === 1
                ? trip.destinations[0].name
                : `${trip.destinations[0].name} + ${trip.destinations.length - 1} more`}
            </span>
          </div>
        )}

        {trip.budget && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <DollarSign className="h-4 w-4" />
            <span>
              Budget:{" "}
              {new Intl.NumberFormat("en-US", {
                currency: trip.currency || "USD",
                style: "currency",
              }).format(trip.budget)}
            </span>
          </div>
        )}

        {tripBudgets.length > 0 && (
          <div className="text-xs text-muted-foreground">
            {tripBudgets.length} budget{tripBudgets.length !== 1 ? "s" : ""} tracked
          </div>
        )}
      </CardContent>

      <CardFooter className="pt-2 gap-2">
        <Button asChild variant="default" size="sm" className="flex-1">
          <Link href={`/dashboard/trips/${trip.id}`}>View Details</Link>
        </Button>

        {onEdit && (
          <Button variant="outline" size="sm" onClick={() => onEdit(trip)}>
            Edit
          </Button>
        )}

        {onDelete && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onDelete(trip.id)}
            className="text-destructive hover:text-destructive"
          >
            Delete
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
