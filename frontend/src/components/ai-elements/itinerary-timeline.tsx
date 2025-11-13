/**
 * @fileoverview Itinerary timeline component for AI Elements.
 */

"use client";

import type { ComponentProps } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { ItineraryPlanResult } from "@/lib/schemas/agents";
import { Source, Sources, SourcesContent, SourcesTrigger } from "./sources";

/**
 * Props for ItineraryTimeline component.
 */
export type ItineraryTimelineProps = ComponentProps<typeof Card> & {
  /** Itinerary plan result to render. */
  result: ItineraryPlanResult;
};

/**
 * Render an itinerary plan with day-by-day timeline.
 */
export function ItineraryTimeline({ result, ...props }: ItineraryTimelineProps) {
  const days = result.days ?? [];

  return (
    <Card {...props}>
      <CardHeader>
        <CardTitle>{result.destination} Itinerary</CardTitle>
        <CardDescription>
          {days.length} days · {result.overview ? "Overview included" : ""}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {result.overview ? (
          <div className="mb-4 text-sm opacity-90">{result.overview}</div>
        ) : null}
        <div className="space-y-4">
          {days.map((day) => (
            <div key={`day-${day.day}`} className="border-l-2 border-primary pl-4">
              <div className="mb-2">
                <div className="text-sm font-semibold">
                  Day {day.day}
                  {day.title ? `: ${day.title}` : ""}
                </div>
                {day.date ? <div className="text-xs opacity-70">{day.date}</div> : null}
                {day.summary ? (
                  <div className="mt-1 text-xs opacity-80">{day.summary}</div>
                ) : null}
              </div>
              {Array.isArray(day.activities) && day.activities.length > 0 ? (
                <div className="mt-2 space-y-2">
                  {day.activities.map((activity) => (
                    <div
                      key={activity.name ?? activity.url ?? String(activity)}
                      className="rounded border p-2 text-xs"
                    >
                      <div className="font-medium">{activity.name}</div>
                      {activity.time ? (
                        <div className="mt-1 opacity-70">Time: {activity.time}</div>
                      ) : null}
                      {activity.location ? (
                        <div className="mt-1 opacity-70">
                          Location: {activity.location}
                        </div>
                      ) : null}
                      {activity.description ? (
                        <div className="mt-1 opacity-80">{activity.description}</div>
                      ) : null}
                      {activity.url ? (
                        <a
                          href={activity.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-1 block underline"
                        >
                          Learn more
                        </a>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
        {Array.isArray(result.recommendations) && result.recommendations.length > 0 ? (
          <div className="mt-4">
            <div className="mb-2 text-sm font-medium">Recommendations</div>
            <ul className="list-disc space-y-1 pl-5 text-xs opacity-80">
              {result.recommendations.map((rec) => (
                <li key={rec.title}>{rec.title}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {Array.isArray(result.sources) && result.sources.length > 0 ? (
          <div className="mt-3">
            <Sources>
              <SourcesTrigger count={result.sources.length} />
              <SourcesContent>
                <div className="space-y-1">
                  {result.sources.map((s) => (
                    <Source key={s.url} href={s.url}>
                      {s.title ?? s.url}
                    </Source>
                  ))}
                </div>
              </SourcesContent>
            </Sources>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
