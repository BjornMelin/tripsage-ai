/**
 * @fileoverview Accommodation stay card for AI Elements.
 */

"use client";

import type { AccommodationSearchResult } from "@schemas/agents";
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
 * Props for StayCard component.
 */
export type StayCardProps = ComponentProps<typeof Card> & {
  /** Accommodation search result */
  result: AccommodationSearchResult;
};

type Stay = AccommodationSearchResult["stays"][number];
type StaySource = NonNullable<AccommodationSearchResult["sources"]>[number];

/**
 * Render a compact list of stays with price and links.
 */
export function StayCard({ result, ...props }: StayCardProps) {
  const stays: Stay[] = (result.stays ?? []).slice(0, 3);
  return (
    <Card {...props}>
      <CardHeader>
        <CardTitle>Places to Stay</CardTitle>
        <CardDescription>{stays.length} highlighted</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3">
          {stays.map((stay: Stay, index: number) => (
            <div key={`${stay.name}-${index}`} className="rounded border p-3">
              <div className="flex items-center justify-between text-sm">
                <div className="font-medium">{stay.name}</div>
                {typeof stay.nightlyRate === "number" && stay.currency ? (
                  <div className="font-semibold">
                    {new Intl.NumberFormat(undefined, {
                      currency: stay.currency,
                      style: "currency",
                    }).format(stay.nightlyRate)}
                    <span className="ml-1 text-xs opacity-70">/night</span>
                  </div>
                ) : null}
              </div>
              {stay.address ? (
                <div className="mt-1 text-xs opacity-80">{stay.address}</div>
              ) : null}
              {stay.url ? (
                <div className="mt-2 text-xs">
                  <a
                    href={stay.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline"
                  >
                    View
                  </a>
                </div>
              ) : null}
            </div>
          ))}
        </div>
        {Array.isArray(result.sources) && result.sources.length > 0 ? (
          <div className="mt-3">
            <Sources>
              <SourcesTrigger count={result.sources.length} />
              <SourcesContent>
                <div className="space-y-1">
                  {result.sources.map((source: StaySource) => (
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
