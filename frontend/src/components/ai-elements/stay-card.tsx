/**
 * @fileoverview Accommodation stay card for AI Elements.
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
import type { AccommodationSearchResult } from "@/lib/schemas/agents";
import { Source, Sources, SourcesContent, SourcesTrigger } from "./sources";

/**
 * Props for StayCard component.
 */
export type StayCardProps = ComponentProps<typeof Card> & {
  /** Accommodation search result */
  result: AccommodationSearchResult;
};

/**
 * Render a compact list of stays with price and links.
 */
export function StayCard({ result, ...props }: StayCardProps) {
  const stays = (result.stays ?? []).slice(0, 3);
  return (
    <Card {...props}>
      <CardHeader>
        <CardTitle>Places to Stay</CardTitle>
        <CardDescription>{stays.length} highlighted</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3">
          {stays.map((s, i) => (
            <div key={`${s.name}-${i}`} className="rounded border p-3">
              <div className="flex items-center justify-between text-sm">
                <div className="font-medium">{s.name}</div>
                {typeof s.nightlyRate === "number" && s.currency ? (
                  <div className="font-semibold">
                    {new Intl.NumberFormat(undefined, {
                      currency: s.currency,
                      style: "currency",
                    }).format(s.nightlyRate)}
                    <span className="ml-1 text-xs opacity-70">/night</span>
                  </div>
                ) : null}
              </div>
              {s.address ? (
                <div className="mt-1 text-xs opacity-80">{s.address}</div>
              ) : null}
              {s.url ? (
                <div className="mt-2 text-xs">
                  <a
                    href={s.url}
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
