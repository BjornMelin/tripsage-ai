/**
 * @fileoverview Utilities for exporting trip itineraries to calendar events.
 */

import type { CalendarEvent } from "@/lib/schemas/calendar";
import { calendarEventSchema } from "@/lib/schemas/calendar";
import type { Trip } from "@/stores/trip-store";
import { DateUtils } from "@/lib/dates/unified-date-utils";

/**
 * Convert a trip to calendar events for export.
 *
 * Creates calendar events from trip destinations, activities, and transportation.
 *
 * @param trip - Trip to convert
 * @returns Array of calendar events
 */
export function tripToCalendarEvents(trip: Trip): CalendarEvent[] {
  const events: CalendarEvent[] = [];

  // Trip start event
  if (trip.startDate || trip.start_date) {
    const startDate = DateUtils.parse(trip.startDate || trip.start_date || "");
    const endDate =
      trip.endDate || trip.end_date
        ? DateUtils.parse(trip.endDate || trip.end_date || "")
        : DateUtils.add(startDate, 1, "days");

    events.push(
      calendarEventSchema.parse({
        description: trip.description || undefined,
        end: {
          dateTime: endDate,
        },
        location: trip.destinations[0]?.name || undefined,
        start: {
          dateTime: startDate,
        },
        summary: trip.name || trip.title || "Trip",
        travelMetadata: {
          tripId: trip.id,
          type: "trip",
        },
      })
    );
  }

  // Destination events
  trip.destinations.forEach((destination) => {
    if (destination.startDate) {
      const startDate = DateUtils.parse(destination.startDate);

      // Arrival event
      events.push(
        calendarEventSchema.parse({
          description: destination.transportation?.details || undefined,
          end: {
            dateTime: DateUtils.add(startDate, 1, "hours"),
          },
          location: `${destination.name}, ${destination.country}`,
          start: {
            dateTime: startDate,
          },
          summary: `Arrive in ${destination.name}`,
          travelMetadata: {
            destinationId: destination.id,
            tripId: trip.id,
            type: "arrival",
          },
        })
      );

      // Activities
      if (destination.activities && destination.activities.length > 0) {
        destination.activities.forEach((activity, index) => {
          const activityDate = DateUtils.add(startDate, index, "days");

          events.push(
            calendarEventSchema.parse({
              end: {
                dateTime: DateUtils.add(activityDate, 2, "hours"),
              },
              location: `${destination.name}, ${destination.country}`,
              start: {
                dateTime: activityDate,
              },
              summary: activity,
              travelMetadata: {
                destinationId: destination.id,
                tripId: trip.id,
                type: "activity",
              },
            })
          );
        });
      }

      // Departure event
      if (destination.endDate) {
        const departureDate = DateUtils.parse(destination.endDate);
        events.push(
          calendarEventSchema.parse({
            description: destination.transportation?.details || undefined,
            end: {
              dateTime: DateUtils.add(departureDate, 1, "hours"),
            },
            location: `${destination.name}, ${destination.country}`,
            start: {
              dateTime: departureDate,
            },
            summary: `Depart from ${destination.name}`,
            travelMetadata: {
              destinationId: destination.id,
              tripId: trip.id,
              type: "departure",
            },
          })
        );
      }
    }
  });

  return events;
}

/**
 * Export trip to ICS file.
 *
 * @param trip - Trip to export
 * @param calendarName - Name for the calendar (default: trip name)
 * @returns Promise resolving to ICS file content
 */
export async function exportTripToIcs(
  trip: Trip,
  calendarName?: string
): Promise<string> {
  const events = tripToCalendarEvents(trip);

  const response = await fetch("/api/calendar/ics/export", {
    body: JSON.stringify({
      calendarName: calendarName || trip.name || trip.title || "TripSage Itinerary",
      events,
    }),
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });

  if (!response.ok) {
    throw new Error(`Failed to export trip: ${response.status}`);
  }

  return response.text();
}
