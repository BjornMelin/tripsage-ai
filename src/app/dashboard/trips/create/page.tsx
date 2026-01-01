/**
 * @fileoverview Trip creation entrypoint for the dashboard “Plan New Trip” flow.
 */

"use client";

import { ISO_DATE_STRING } from "@schemas/shared/time";
import type { TripCreateInput, TripSuggestion } from "@schemas/trips";
import {
  ArrowLeftIcon,
  CalendarIcon,
  CheckIcon,
  Loader2Icon,
  MapPinIcon,
  SparklesIcon,
} from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { z } from "zod";
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
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { useCreateTrip } from "@/hooks/use-trips";
import { useZodForm } from "@/hooks/use-zod-form";
import { getErrorMessage } from "@/lib/api/error-types";
import { DateUtils } from "@/lib/dates/unified-date-utils";

const OPTIONAL_ISO_DATE_STRING = z.union([ISO_DATE_STRING, z.literal("")]).optional();

const PLAN_TRIP_FORM_SCHEMA = z
  .strictObject({
    description: z.string().max(1000, { error: "Notes too long" }).optional(),
    destination: z
      .string()
      .min(1, { error: "Destination is required" })
      .max(200, { error: "Destination too long" }),
    endDate: OPTIONAL_ISO_DATE_STRING,
    startDate: OPTIONAL_ISO_DATE_STRING,
    title: z.string().max(200, { error: "Title too long" }).optional(),
  })
  .refine(
    (value) => {
      if (!value.startDate || !value.endDate) return true;
      // YYYY-MM-DD sorts lexicographically in chronological order.
      return value.endDate > value.startDate;
    },
    { error: "End date must be after start date", path: ["endDate"] }
  );

type PlanTripFormData = z.infer<typeof PLAN_TRIP_FORM_SCHEMA>;

const DEFAULT_SUGGESTION_LIMIT = 12;

function computeDefaultDates(): { startDate: string; endDate: string } {
  const start = DateUtils.add(new Date(), 1, "days");
  const end = DateUtils.add(start, 7, "days");
  return {
    endDate: DateUtils.format(end, "yyyy-MM-dd"),
    startDate: DateUtils.format(start, "yyyy-MM-dd"),
  };
}

function isoDateToIsoDateTime(value: string): string {
  return DateUtils.formatForApi(DateUtils.parse(value));
}

function computeDefaultTripTitle(destination: string): string {
  const clean = destination.trim();
  if (!clean) return "New Trip";
  return `Trip to ${clean}`;
}

function makeCreatePayload(
  values: PlanTripFormData,
  defaults: { startDate: string; endDate: string },
  suggestion: TripSuggestion | null
): TripCreateInput {
  const destination = values.destination.trim();
  const title =
    values.title?.trim() ||
    suggestion?.title?.trim() ||
    computeDefaultTripTitle(destination);

  const durationDays =
    suggestion?.duration && suggestion.duration > 0 ? suggestion.duration : 7;
  const requestedStartIsoDate = values.startDate?.trim() ?? "";
  const requestedEndIsoDate = values.endDate?.trim() ?? "";

  let startIsoDate = requestedStartIsoDate || defaults.startDate;
  let endIsoDate = requestedEndIsoDate;

  if (!endIsoDate) {
    endIsoDate = DateUtils.format(
      DateUtils.add(DateUtils.parse(startIsoDate), durationDays, "days"),
      "yyyy-MM-dd"
    );
  }

  if (!requestedStartIsoDate && requestedEndIsoDate) {
    startIsoDate = DateUtils.format(
      DateUtils.subtract(DateUtils.parse(requestedEndIsoDate), durationDays, "days"),
      "yyyy-MM-dd"
    );
    endIsoDate = requestedEndIsoDate;
  }
  const startDate = isoDateToIsoDateTime(startIsoDate);
  const endDate = isoDateToIsoDateTime(endIsoDate);

  const description =
    values.description?.trim() || suggestion?.description?.trim() || undefined;

  return {
    currency: suggestion?.currency ?? "USD",
    description,
    destination,
    endDate,
    startDate,
    status: "planning",
    title,
    travelers: 1,
    tripType: "leisure",
    visibility: "private",
  };
}

export default function CreateTripPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const suggestionId = searchParams.get("suggestion") ?? undefined;

  const { authenticatedApi, cancelRequests } = useAuthenticatedApi();
  const { toast } = useToast();
  const createTripMutation = useCreateTrip();

  const defaultDates = useMemo(() => computeDefaultDates(), []);

  const form = useZodForm({
    defaultValues: {
      description: "",
      destination: "",
      endDate: defaultDates.endDate,
      startDate: defaultDates.startDate,
      title: "",
    },
    schema: PLAN_TRIP_FORM_SCHEMA,
    validateMode: "onChange",
  });

  const [suggestionState, setSuggestionState] = useState<
    | { kind: "idle" }
    | { kind: "loading"; id: string }
    | { kind: "loaded"; id: string; suggestion: TripSuggestion | null }
    | { kind: "error"; id: string }
  >({ kind: "idle" });

  const suggestion =
    suggestionState.kind === "loaded" ? suggestionState.suggestion : null;

  useEffect(() => {
    if (!suggestionId) {
      setSuggestionState({ kind: "idle" });
      return;
    }

    setSuggestionState({ id: suggestionId, kind: "loading" });

    authenticatedApi
      .get<TripSuggestion[]>("/api/trips/suggestions", {
        params: { limit: DEFAULT_SUGGESTION_LIMIT },
      })
      .then((suggestions) => {
        const match = suggestions.find((item) => item.id === suggestionId) ?? null;
        setSuggestionState({ id: suggestionId, kind: "loaded", suggestion: match });
      })
      .catch(() => {
        setSuggestionState({ id: suggestionId, kind: "error" });
      });

    return () => {
      cancelRequests();
    };
  }, [authenticatedApi, cancelRequests, suggestionId]);

  useEffect(() => {
    if (!suggestion) return;

    const currentDestination = form.getValues("destination").trim();
    const currentTitle = form.getValues("title")?.trim() ?? "";
    const currentStart = form.getValues("startDate");
    const currentEnd = form.getValues("endDate");

    if (!currentDestination) {
      form.setValue("destination", suggestion.destination, { shouldValidate: true });
    }

    if (!currentTitle) {
      form.setValue("title", suggestion.title, { shouldValidate: true });
    }

    // Keep user edits, but adjust default dates to match suggested duration.
    if (
      suggestion.duration > 0 &&
      currentStart === defaultDates.startDate &&
      currentEnd === defaultDates.endDate
    ) {
      const start = DateUtils.parse(defaultDates.startDate);
      const end = DateUtils.add(start, suggestion.duration, "days");
      form.setValue("endDate", DateUtils.format(end, "yyyy-MM-dd"), {
        shouldValidate: true,
      });
    }
  }, [defaultDates, form, suggestion]);

  const isSubmitting = createTripMutation.isPending;
  const canSubmit = form.formState.isValid && !isSubmitting;

  const onSubmit = form.handleSubmitSafe(async (values) => {
    try {
      const payload = makeCreatePayload(values, defaultDates, suggestion);
      const created = await createTripMutation.mutateAsync(payload);
      toast({
        description: suggestionId
          ? "Draft created from your suggestion. You can refine details next."
          : "Draft created. You can refine details next.",
        title: "Trip created",
      });
      router.push(`/dashboard/trips/${created.id}`);
    } catch (error) {
      toast({
        description: getErrorMessage(error),
        title: "Unable to create trip",
        variant: "destructive",
      });
    }
  });

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2">
            <h2 className="text-3xl font-bold tracking-tight">Plan New Trip</h2>
            {suggestionId && (
              <Badge variant="secondary" className="gap-1">
                <SparklesIcon className="h-3.5 w-3.5" />
                Using suggestion
              </Badge>
            )}
          </div>
          <p className="text-muted-foreground">
            Start with a destination. We’ll create a draft trip you can refine later.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link href="/dashboard">
              <ArrowLeftIcon className="mr-2 h-4 w-4" />
              Dashboard
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <Link href="/dashboard/trips">My Trips</Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Trip basics</CardTitle>
            <CardDescription>
              Provide the minimum details. Dates are optional and can be adjusted later.
            </CardDescription>
          </CardHeader>

          <CardContent className="space-y-5">
            {suggestionId && (
              <div className="rounded-lg border bg-muted/20 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <SparklesIcon className="h-4 w-4 text-primary" />
                    <span>Suggestion</span>
                    <span className="font-mono text-xs text-muted-foreground">
                      {suggestionId}
                    </span>
                  </div>

                  {suggestionState.kind === "loading" && (
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Loader2Icon className="h-3.5 w-3.5 animate-spin" />
                      Loading details…
                    </div>
                  )}

                  {suggestionState.kind === "error" && (
                    <div className="text-xs text-muted-foreground">
                      Couldn’t load suggestion details. You can still create the trip.
                    </div>
                  )}
                </div>

                {suggestion && (
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    <div className="text-sm">
                      <div className="text-xs text-muted-foreground">Destination</div>
                      <div className="font-medium">{suggestion.destination}</div>
                    </div>
                    <div className="text-sm">
                      <div className="text-xs text-muted-foreground">Duration</div>
                      <div className="font-medium">{suggestion.duration} days</div>
                    </div>
                    <div className="text-sm sm:col-span-2">
                      <div className="text-xs text-muted-foreground">Why this trip</div>
                      <div className="text-muted-foreground line-clamp-2">
                        {suggestion.description}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            <Form {...form}>
              <form onSubmit={onSubmit} className="space-y-5">
                <div className="grid gap-4 sm:grid-cols-2">
                  <FormField
                    control={form.control}
                    name="destination"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Destination</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <MapPinIcon className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input
                              {...field}
                              className="pl-9"
                              autoComplete="off"
                              placeholder="Tokyo, Japan"
                            />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="title"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Trip title (optional)</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            autoComplete="off"
                            placeholder={computeDefaultTripTitle(
                              form.watch("destination") || "your destination"
                            )}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <div className="grid gap-4 sm:grid-cols-2">
                  <FormField
                    control={form.control}
                    name="startDate"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Start date (optional)</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <CalendarIcon className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input {...field} className="pl-9" type="date" />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="endDate"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>End date (optional)</FormLabel>
                        <FormControl>
                          <div className="relative">
                            <CalendarIcon className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                            <Input {...field} className="pl-9" type="date" />
                          </div>
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>

                <FormField
                  control={form.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Notes (optional)</FormLabel>
                      <FormControl>
                        <Textarea
                          {...field}
                          placeholder="Anything to keep in mind? (budget, pace, must‑see spots)"
                          rows={4}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div className="text-xs text-muted-foreground">
                    {suggestionId ? (
                      <span>
                        We’ll seed this draft from your suggestion and take you to the
                        trip workspace.
                      </span>
                    ) : (
                      <span>
                        We’ll create a draft trip now. You can refine details next.
                      </span>
                    )}
                  </div>

                  <Button type="submit" disabled={!canSubmit} className="sm:min-w-40">
                    {isSubmitting ? (
                      <>
                        <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
                        Creating…
                      </>
                    ) : (
                      <>
                        <CheckIcon className="mr-2 h-4 w-4" />
                        Create Trip
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </Form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>What happens next</CardTitle>
            <CardDescription>
              Your trip starts as a draft you can refine.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg border bg-muted/20 p-4">
              <div className="space-y-3 text-sm">
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <span className="text-xs font-semibold">1</span>
                  </div>
                  <div>
                    <div className="font-medium">Create the trip</div>
                    <div className="text-muted-foreground">
                      We’ll save a draft to your account.
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <span className="text-xs font-semibold">2</span>
                  </div>
                  <div>
                    <div className="font-medium">Add details</div>
                    <div className="text-muted-foreground">
                      Adjust dates, destinations, budgets, and collaborators.
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-primary">
                    <span className="text-xs font-semibold">3</span>
                  </div>
                  <div>
                    <div className="font-medium">Build your itinerary</div>
                    <div className="text-muted-foreground">
                      Start adding activities and booking items.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
          <CardFooter className="justify-between">
            <Button variant="outline" asChild>
              <Link href="/dashboard/trips">Browse trips</Link>
            </Button>
            <Button variant="secondary" asChild>
              <Link href="/dashboard/search/unified">Search first</Link>
            </Button>
          </CardFooter>
        </Card>
      </div>
    </div>
  );
}
