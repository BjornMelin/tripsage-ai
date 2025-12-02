"use client";

/**
 * @fileoverview Chat message renderer for AI/UI messages with schema card support and safe tool output rendering.
 */

import type { UIMessage } from "ai";
import { BudgetChart } from "@/components/ai-elements/budget-chart";
import { DestinationCard } from "@/components/ai-elements/destination-card";
import { FlightOfferCard } from "@/components/ai-elements/flight-card";
import { ItineraryTimeline } from "@/components/ai-elements/itinerary-timeline";
import {
  Message,
  MessageAvatar,
  MessageContent,
} from "@/components/ai-elements/message";
import { Response } from "@/components/ai-elements/response";
import {
  Source,
  Sources,
  SourcesContent,
  SourcesTrigger,
} from "@/components/ai-elements/sources";
import { StayCard } from "@/components/ai-elements/stay-card";
import { parseSchemaCard } from "@/lib/ui/parse-schema-card";

type SourceUrlPart = {
  type: "source-url";
  url: string;
  title?: string;
};

type WebSearchUiResult = {
  results: Array<{
    url: string;
    title?: string;
    snippet?: string;
    publishedAt?: string;
  }>;
  fromCache?: boolean;
  tookMs?: number;
};

// biome-ignore lint/style/useNamingConvention: Type guard helper for discriminated parts
function isSourceUrlPart(value: unknown): value is SourceUrlPart {
  if (typeof value !== "object" || value === null) return false;
  const part = value as Record<string, unknown>;
  return part.type === "source-url" && typeof part.url === "string";
}

/** Keys that must be redacted from tool output. */
const REDACT_KEYS = new Set(["apikey", "token", "secret", "password", "id"]);
const MAX_STRING_LENGTH = 200;
const MAX_DEPTH = 2;

// biome-ignore lint/style/useNamingConvention: Internal utility function, not a React component
function sanitizeValue(value: unknown, depth: number): unknown {
  if (depth > MAX_DEPTH) return "[truncated]";
  if (value === null || value === undefined) return value;
  if (typeof value === "string") {
    if (value.length > MAX_STRING_LENGTH) {
      return `${value.slice(0, MAX_STRING_LENGTH)}…`;
    }
    return value;
  }
  if (Array.isArray(value)) {
    const truncated = value.slice(0, 10).map((v) => sanitizeValue(v, depth + 1));
    if (value.length > 10) {
      truncated.push(`[... ${value.length - 10} more items]`);
    }
    return truncated;
  }
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).slice(0, 15);
    const result = entries.reduce<Record<string, unknown>>((acc, [key, val]) => {
      if (REDACT_KEYS.has(key.toLowerCase())) {
        acc[key] = "[REDACTED]";
      } else {
        acc[key] = sanitizeValue(val, depth + 1);
      }
      return acc;
    }, {});
    const totalKeys = Object.keys(value as Record<string, unknown>).length;
    if (totalKeys > 15) {
      result.__truncated__ = `${totalKeys - 15} more keys`;
    }
    return result;
  }
  return value;
}

/** Sanitize tool output for safe display - redacts sensitive keys and truncates long values. */
// biome-ignore lint/style/useNamingConvention: This is a utility function export, not a React component
export function sanitizeToolOutput(raw: unknown): unknown {
  try {
    return sanitizeValue(raw, 0);
  } catch {
    return "[unserializable]";
  }
}

export function ChatMessageItem({ message }: { message: UIMessage }) {
  const parts = message.parts ?? [];
  // Extract source-url parts for citation display
  const sourceParts: SourceUrlPart[] = (parts as unknown[]).filter(isSourceUrlPart);

  return (
    <Message from={message.role} data-testid={`msg-${message.id}`}>
      <MessageAvatar
        src={message.role === "user" ? "/avatar-user.png" : "/avatar-ai.png"}
        name={message.role === "user" ? "You" : "AI"}
      />
      <MessageContent>
        {parts.length > 0 ? (
          parts.map((part, idx) => {
            switch (part?.type) {
              case "text": {
                const text = part.text ?? "";
                const schemaCard = parseSchemaCard(text);

                if (schemaCard) {
                  switch (schemaCard.kind) {
                    case "flight":
                      return (
                        <FlightOfferCard
                          key={`${message.id}-flight-${idx}`}
                          result={
                            schemaCard.data as Parameters<
                              typeof FlightOfferCard
                            >[0]["result"]
                          }
                        />
                      );
                    case "stay":
                      return (
                        <StayCard
                          key={`${message.id}-stay-${idx}`}
                          result={
                            schemaCard.data as Parameters<typeof StayCard>[0]["result"]
                          }
                        />
                      );
                    case "budget":
                      return (
                        <BudgetChart
                          key={`${message.id}-budget-${idx}`}
                          result={
                            schemaCard.data as Parameters<
                              typeof BudgetChart
                            >[0]["result"]
                          }
                        />
                      );
                    case "destination":
                      return (
                        <DestinationCard
                          key={`${message.id}-dest-${idx}`}
                          result={
                            schemaCard.data as Parameters<
                              typeof DestinationCard
                            >[0]["result"]
                          }
                        />
                      );
                    case "itinerary":
                      return (
                        <ItineraryTimeline
                          key={`${message.id}-itin-${idx}`}
                          result={
                            schemaCard.data as Parameters<
                              typeof ItineraryTimeline
                            >[0]["result"]
                          }
                        />
                      );
                  }
                }

                return <Response key={`${message.id}-t-${idx}`}>{part.text}</Response>;
              }
              case "source-url": {
                // Rendered separately in the Sources section below
                return null;
              }
              case "tool-call":
              case "tool-call-result": {
                type ToolResultPart = {
                  type?: string;
                  name?: string;
                  toolName?: string;
                  tool?: string;
                  result?: unknown;
                  output?: unknown;
                  data?: unknown;
                };
                const p = part as ToolResultPart;
                const toolName = p?.name ?? p?.toolName ?? p?.tool;
                const raw = p?.result ?? p?.output ?? p?.data;
                const result =
                  raw && typeof raw === "object"
                    ? (raw as WebSearchUiResult)
                    : undefined;
                if (
                  toolName === "webSearch" &&
                  result &&
                  Array.isArray(result.results)
                ) {
                  const sources = result.results;
                  return (
                    <div
                      key={`${message.id}-tool-${idx}`}
                      className="my-2 rounded-md border bg-muted/30 p-3 text-sm"
                    >
                      <div className="mb-2 flex items-center justify-between">
                        <div className="font-medium">Web Search</div>
                        <div className="text-xs opacity-70">
                          {result.fromCache ? "cached" : "live"}
                          {typeof result.tookMs === "number"
                            ? ` · ${result.tookMs}ms`
                            : null}
                        </div>
                      </div>
                      <div className="grid gap-2">
                        {sources.map((s, i) => (
                          <div
                            key={`${message.id}-ws-${i}`}
                            className="rounded border bg-background p-2"
                          >
                            <a
                              href={s.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-medium hover:underline"
                            >
                              {s.title ?? s.url}
                            </a>
                            {s.snippet ? (
                              <div className="mt-1 text-xs opacity-80">{s.snippet}</div>
                            ) : null}
                            {(() => {
                              if (
                                !("publishedAt" in s) ||
                                typeof s.publishedAt !== "string"
                              ) {
                                return null;
                              }
                              const published = new Date(s.publishedAt);
                              if (Number.isNaN(published.getTime())) return null;
                              return (
                                <div className="mt-1 text-[10px] opacity-60">
                                  {published.toLocaleString()}
                                </div>
                              );
                            })()}
                          </div>
                        ))}
                      </div>
                      {sources.length > 0 ? (
                        <div className="mt-2">
                          <Sources>
                            <SourcesTrigger count={sources.length} />
                            <SourcesContent>
                              <div className="space-y-1">
                                {sources.map((s, i) => (
                                  <Source key={`${message.id}-src-${i}`} href={s.url}>
                                    {s.title ?? s.url}
                                  </Source>
                                ))}
                              </div>
                            </SourcesContent>
                          </Sources>
                        </div>
                      ) : null}
                    </div>
                  );
                }
                const sanitized = sanitizeToolOutput(raw ?? part);
                return (
                  <div
                    key={`${message.id}-tool-${idx}`}
                    className="my-2 rounded-md border bg-muted/30 p-3 text-xs"
                  >
                    <div className="mb-1 font-medium">{toolName ?? "Tool"}</div>
                    <pre className="overflow-x-auto whitespace-pre-wrap">
                      {JSON.stringify(sanitized, null, 2)}
                    </pre>
                  </div>
                );
              }
              case "reasoning":
                return (
                  <div
                    key={`${message.id}-r-${idx}`}
                    className="my-2 rounded-md border border-yellow-300/50 bg-yellow-50 p-3 text-xs text-yellow-900 dark:border-yellow-300/30 dark:bg-yellow-950 dark:text-yellow-200"
                  >
                    <div className="mb-1 font-medium">Reasoning</div>
                    <pre className="whitespace-pre-wrap">
                      {part.text ?? String(part)}
                    </pre>
                  </div>
                );
              default: {
                let fallback = "";
                if (typeof part === "string") {
                  fallback = part;
                } else {
                  try {
                    fallback = JSON.stringify(part, null, 2);
                  } catch {
                    fallback = "[unserializable object]";
                  }
                }
                return (
                  <pre key={`${message.id}-u-${idx}`} className="text-xs opacity-70">
                    {fallback}
                  </pre>
                );
              }
            }
          })
        ) : (
          <span className="opacity-70">(no content)</span>
        )}

        {message.role === "assistant" && sourceParts.length > 0 ? (
          <div className="mt-2">
            <Sources>
              <SourcesTrigger count={sourceParts.length} />
              <SourcesContent>
                <div className="space-y-1">
                  {sourceParts.map((p, i) => {
                    const href = p.url;
                    const title = p.title ?? href;
                    return (
                      <Source key={`${message.id}-src-${i}`} href={href}>
                        {title}
                      </Source>
                    );
                  })}
                </div>
              </SourcesContent>
            </Sources>
          </div>
        ) : null}
      </MessageContent>
    </Message>
  );
}
