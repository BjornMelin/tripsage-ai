/**
 * @fileoverview Client component for creating/editing calendar events.
 */

"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import { createEventRequestSchema } from "@/lib/schemas/calendar";

const EVENT_FORM_SCHEMA = createEventRequestSchema.extend({
  calendarId: z.string().default("primary"),
});

type EventFormData = z.infer<typeof EVENT_FORM_SCHEMA>;

/**
 * Props for CalendarEventForm component.
 */
export interface CalendarEventFormProps {
  /** Optional initial event data for editing */
  initialData?: Partial<EventFormData>;
  /** Callback when event is created/updated */
  onSuccess?: (eventId: string) => void;
  /** Callback on error */
  onError?: (error: string) => void;
  /** Optional className */
  className?: string;
}

/**
 * CalendarEventForm component.
 *
 * Form for creating or editing calendar events.
 */
export function CalendarEventForm({
  initialData,
  onSuccess,
  onError,
  className,
}: CalendarEventFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
    reset,
  } = useForm<EventFormData>({
    defaultValues: {
      calendarId: "primary",
      ...initialData,
      end: initialData?.end || {
        dateTime: new Date(Date.now() + 60 * 60 * 1000), // Default 1 hour
      },
      start: initialData?.start || {
        dateTime: new Date(),
      },
    },
    resolver: zodResolver(EVENT_FORM_SCHEMA) as never,
  });

  const startDateTime = watch("start.dateTime");
  const endDateTime = watch("end.dateTime");

  const onSubmit = async (data: EventFormData): Promise<void> => {
    setIsSubmitting(true);
    try {
      const response = await fetch("/api/calendar/events", {
        body: JSON.stringify({
          ...data,
          end: {
            date: data.end.date,
            dateTime: data.end.dateTime?.toISOString(),
            timeZone: data.end.timeZone,
          },
          start: {
            date: data.start.date,
            dateTime: data.start.dateTime?.toISOString(),
            timeZone: data.start.timeZone,
          },
        }),
        headers: {
          "Content-Type": "application/json",
        },
        method: "POST",
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to create event");
      }

      const result = await response.json();
      onSuccess?.(result.id);
      // Reset form after successful submission
      reset();
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown error";
      // Only show toast if parent didn't provide onError callback
      // Parent can handle error display (e.g., CalendarPage shows toast)
      if (onError) {
        onError(message);
      } else {
        toast({
          description: message,
          title: "Failed to create event",
          variant: "destructive",
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Create Calendar Event</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label htmlFor="summary">Title</Label>
            <Input id="summary" {...register("summary")} placeholder="Event title" />
            {errors.summary && (
              <p className="text-sm text-red-600">{errors.summary.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...register("description")}
              placeholder="Event description"
              rows={3}
            />
            {errors.description && (
              <p className="text-sm text-red-600">{errors.description.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="location">Location</Label>
            <Input
              id="location"
              {...register("location")}
              placeholder="Event location"
            />
            {errors.location && (
              <p className="text-sm text-red-600">{errors.location.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="start">Start</Label>
              <Input
                id="start"
                type="datetime-local"
                value={
                  startDateTime instanceof Date
                    ? startDateTime.toISOString().slice(0, 16)
                    : ""
                }
                onChange={(e) => {
                  const date = e.target.value ? new Date(e.target.value) : null;
                  if (date) {
                    setValue("start.dateTime", date, { shouldValidate: true });
                  }
                }}
              />
              {errors.start && (
                <p className="text-sm text-red-600">{errors.start.message}</p>
              )}
            </div>

            <div>
              <Label htmlFor="end">End</Label>
              <Input
                id="end"
                type="datetime-local"
                value={
                  endDateTime instanceof Date
                    ? endDateTime.toISOString().slice(0, 16)
                    : ""
                }
                onChange={(e) => {
                  const date = e.target.value ? new Date(e.target.value) : null;
                  if (date) {
                    setValue("end.dateTime", date, { shouldValidate: true });
                  }
                }}
              />
              {errors.end && (
                <p className="text-sm text-red-600">{errors.end.message}</p>
              )}
            </div>
          </div>

          <Button type="submit" disabled={isSubmitting} className="w-full sm:w-auto">
            {isSubmitting ? (
              <>
                <LoadingSpinner size="sm" className="mr-2" />
                Creating...
              </>
            ) : (
              "Create Event"
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
