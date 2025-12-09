/**
 * @fileoverview Destination research card for AI Elements.
 */

"use client";

import type { DestinationResearchResult } from "@schemas/agents";
import type { ComponentProps } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Source, Sources, SourcesContent, SourcesTrigger } from "./sources";

/**
 * Props for DestinationCard component.
 */
export type DestinationCardProps = ComponentProps<typeof Card> & {
  /** Destination research result to render. */
  result: DestinationResearchResult;
};

type DestinationItem = NonNullable<DestinationResearchResult["highlights"]>[number];
type SafetyScore = NonNullable<
  NonNullable<DestinationResearchResult["safety"]>["scores"]
>[number];

/**
 * Render a destination research result with overview, highlights, and sources.
 */
export function DestinationCard({ result, ...props }: DestinationCardProps) {
  const highlights: DestinationItem[] = result.highlights ?? [];
  const attractions: DestinationItem[] = result.attractions ?? [];
  const activities: DestinationItem[] = result.activities ?? [];

  return (
    <Card {...props}>
      <CardHeader>
        <CardTitle>{result.destination}</CardTitle>
        <CardDescription>Destination Research</CardDescription>
      </CardHeader>
      <CardContent>
        {result.overview ? (
          <div className="mb-4 text-sm opacity-90">{result.overview}</div>
        ) : null}
        {highlights.length > 0 ? (
          <div className="mb-4">
            <div className="mb-2 text-sm font-medium">Highlights</div>
            <ul className="list-disc space-y-1 pl-5 text-xs opacity-80">
              {highlights.slice(0, 5).map((highlight: DestinationItem) => (
                <li key={highlight.title}>{highlight.title}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {attractions.length > 0 ? (
          <div className="mb-4">
            <div className="mb-2 text-sm font-medium">Top Attractions</div>
            <div className="space-y-2">
              {attractions.slice(0, 5).map((attraction: DestinationItem) => (
                <div
                  key={attraction.title ?? attraction.url ?? String(attraction)}
                  className="text-xs"
                >
                  <div className="font-medium">{attraction.title}</div>
                  {attraction.description ? (
                    <div className="opacity-80">{attraction.description}</div>
                  ) : null}
                  {attraction.url ? (
                    <a
                      href={attraction.url}
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
          </div>
        ) : null}
        {activities.length > 0 ? (
          <div className="mb-4">
            <div className="mb-2 text-sm font-medium">Activities</div>
            <ul className="list-disc space-y-1 pl-5 text-xs opacity-80">
              {activities.slice(0, 5).map((activity: DestinationItem) => (
                <li key={activity.title}>{activity.title}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {result.safety ? (
          <div className="mb-4 rounded border p-3">
            <div className="mb-2 text-sm font-medium">Safety</div>
            {result.safety.summary ? (
              <div className="mb-2 text-xs opacity-80">{result.safety.summary}</div>
            ) : null}
            {Array.isArray(result.safety.scores) && result.safety.scores.length > 0 ? (
              <div className="space-y-1">
                {result.safety.scores.map((score: SafetyScore) => (
                  <div
                    key={score.category}
                    className="flex items-center justify-between text-xs"
                  >
                    <span>{score.category}</span>
                    <span className="font-medium">{score.value}/100</span>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
        {Array.isArray(result.sources) && result.sources.length > 0 ? (
          <div className="mt-3">
            <Sources>
              <SourcesTrigger count={result.sources.length} />
              <SourcesContent>
                <div className="space-y-1">
                  {result.sources.map((source) => (
                    <Source key={source.url} href={source.url}>
                      {source.title ?? source.url}
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
