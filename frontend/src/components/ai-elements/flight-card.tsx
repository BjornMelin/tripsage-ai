/**
 * @fileoverview Flight offer card for AI Elements.
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
import type { FlightSearchResult } from "@/schemas/agents";
import { Source, Sources, SourcesContent, SourcesTrigger } from "./sources";

/**
 * Props for FlightOfferCard component.
 */
export type FlightOfferCardProps = ComponentProps<typeof Card> & {
  /** Search result containing itineraries to render. */
  result: FlightSearchResult;
};

/**
 * Render a compact flight search result with top itineraries and source links.
 */
export function FlightOfferCard({ result, ...props }: FlightOfferCardProps) {
  const top = (result.itineraries ?? []).slice(0, 3);
  return (
    <Card {...props}>
      <CardHeader>
        <CardTitle>Flight Options</CardTitle>
        <CardDescription>
          {top.length} selected · Currency {result.currency}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-3">
          {top.map((it) => (
            <div key={it.id} className="rounded border p-3">
              <div className="flex items-center justify-between text-sm">
                <div className="font-medium">
                  {it.segments[0]?.origin} →{" "}
                  {it.segments[it.segments.length - 1]?.destination}
                </div>
                <div className="font-semibold">
                  {new Intl.NumberFormat(undefined, {
                    currency: result.currency,
                    style: "currency",
                  }).format(it.price)}
                </div>
              </div>
              <div className="mt-1 text-xs opacity-80">
                {it.segments.map((s, i) => (
                  <span key={`${it.id}-seg-${i}`}>
                    {s.origin}→{s.destination}
                    {i < it.segments.length - 1 ? " · " : ""}
                  </span>
                ))}
              </div>
              {it.bookingUrl ? (
                <div className="mt-2 text-xs">
                  <a
                    href={it.bookingUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline"
                  >
                    Book
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
