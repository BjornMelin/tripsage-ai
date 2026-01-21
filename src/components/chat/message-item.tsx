/**
 * @fileoverview Chat message renderer for AI/UI messages with safe tool output rendering.
 */

"use client";

import {
  chatMessageMetadataSchema,
  type LanguageModelUsageMetadata,
} from "@schemas/ai";
import type { UIMessage } from "ai";
import { FileIcon } from "lucide-react";
import { BudgetChart } from "@/components/ai-elements/budget-chart";
import { DestinationCard } from "@/components/ai-elements/destination-card";
import { FlightOfferCard } from "@/components/ai-elements/flight-card";
import { ItineraryTimeline } from "@/components/ai-elements/itinerary-timeline";
import {
  Message,
  MessageAvatar,
  MessageContent,
} from "@/components/ai-elements/message";
import { Reasoning } from "@/components/ai-elements/reasoning";
import { Response } from "@/components/ai-elements/response";
import {
  Source,
  Sources,
  SourcesContent,
  SourcesTrigger,
} from "@/components/ai-elements/sources";
import { StayCard } from "@/components/ai-elements/stay-card";
import { Tool } from "@/components/ai-elements/tool";
import { parseSchemaCard } from "@/lib/ui/parse-schema-card";
import { safeHref } from "@/lib/url/safe-href";

type SourceUrlPart = {
  type: "source-url";
  url: string;
  title?: string;
};

/**
 * Custom message part used to signal the start of a new step in a multi-step response.
 *
 * This is an extension on top of AI SDK message parts. When present, `step` is a 1-indexed
 * step number; omit `step` when the step index is unknown.
 */
type StepStartPart = {
  type: "step-start";
  step?: number;
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

function AsRecord(value: unknown): Record<string, unknown> | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

// biome-ignore lint/style/useNamingConvention: Type guard helper for discriminated parts
function isSourceUrlPart(value: unknown): value is SourceUrlPart {
  if (typeof value !== "object" || value === null) return false;
  const part = value as Record<string, unknown>;
  return part.type === "source-url" && typeof part.url === "string";
}

// biome-ignore lint/style/useNamingConvention: Type guard helper for discriminated parts
function isStepStartPart(value: unknown): value is StepStartPart {
  if (typeof value !== "object" || value === null) return false;
  const part = value as Record<string, unknown>;
  if (part.type !== "step-start") return false;

  const step = part.step;
  const valid =
    step === undefined ||
    (typeof step === "number" && Number.isInteger(step) && step > 0);

  if (!valid && process.env.NODE_ENV === "development") {
    console.warn("Invalid step-start part: expected step to be a positive integer.", {
      step,
    });
  }

  return valid;
}

/** Keys that must be redacted from tool output. */
const REDACT_KEYS = new Set(["apikey", "token", "secret", "password", "id"]);
const MAX_STRING_LENGTH = 200;
const MAX_DEPTH = 2;

/** Allowlist of safe MIME types for data URLs */
const SAFE_MIME_TYPES = new Set([
  "image/png",
  "image/jpeg",
  "image/jpg",
  "image/gif",
  "image/webp",
  "image/svg+xml",
  "video/mp4",
  "video/webm",
  "audio/mpeg",
  "audio/wav",
  "application/pdf",
]);

const BASE64_PATTERN = /^[A-Za-z0-9+/]+={0,2}$/;

// biome-ignore lint/style/useNamingConvention: Internal utility function, not a React component
function isValidBase64(value: string): boolean {
  if (!value || value.length % 4 !== 0) return false;
  if (!BASE64_PATTERN.test(value)) return false;

  try {
    return btoa(atob(value)).replace(/=+$/, "") === value.replace(/=+$/, "");
  } catch {
    return false;
  }
}

/**
 * Validates and normalizes a MIME type string.
 * Returns the MIME type if it's in the allowlist, otherwise returns a safe default.
 * Only explicit MIME types in SAFE_MIME_TYPES are allowed to prevent XSS vectors.
 */
// biome-ignore lint/style/useNamingConvention: Internal utility function, not a React component
function validateMimeType(mimeType?: string): string {
  if (!mimeType || typeof mimeType !== "string") {
    return "application/octet-stream";
  }

  const normalized = mimeType.toLowerCase().trim();
  if (SAFE_MIME_TYPES.has(normalized)) {
    return normalized;
  }

  // Default to safe fallback for unknown types
  return "application/octet-stream";
}

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

function FormatUsage(usage?: LanguageModelUsageMetadata | null): string | null {
  if (!usage) return null;

  const inputTokens = usage.inputTokens;
  const outputTokens = usage.outputTokens;
  const hasInput = typeof inputTokens === "number";
  const hasOutput = typeof outputTokens === "number";
  const totalTokens =
    typeof usage.totalTokens === "number"
      ? usage.totalTokens
      : hasInput && hasOutput
        ? inputTokens + outputTokens
        : undefined;

  const parts: string[] = [];
  if (hasInput) parts.push(`${inputTokens} in`);
  if (hasOutput) parts.push(`${outputTokens} out`);

  if (typeof totalTokens === "number") {
    const base = parts.length > 0 ? `${parts.join(" / ")} (${totalTokens} total)` : "";
    return base || `${totalTokens} total`;
  }

  return parts.length > 0 ? parts.join(" / ") : null;
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

export interface ChatMessageItemProps {
  /** The message to render */
  message: UIMessage;
  /** When true, indicates the message is currently streaming (enables animation) */
  isStreaming?: boolean;
}

/**
 * Render a chat message item that displays message parts (text, schema cards, reasoning, tool outputs, files, and sources) with safe sanitization and UI-specific handling.
 *
 * @param message - The UI message object to render, containing role, id, parts, and optional metadata.
 * @param isStreaming - When true, enables streaming animation for the last assistant text part.
 * @returns A React element representing the rendered chat message, including avatar, content parts, citations, and optional usage/finish/abort info.
 */
export function ChatMessageItem({
  message,
  isStreaming = false,
}: ChatMessageItemProps) {
  const parts = message.parts ?? [];
  const metadata = chatMessageMetadataSchema.safeParse(message.metadata);
  const abortReason = metadata.success ? metadata.data.abortReason : undefined;
  const finishReason = metadata.success ? metadata.data.finishReason : undefined;
  const usageSummary = metadata.success ? FormatUsage(metadata.data.totalUsage) : null;
  // Extract source-url parts for citation display
  const sourceParts: SourceUrlPart[] = (parts as unknown[]).filter(isSourceUrlPart);
  // Only animate the last text part of an assistant message during streaming
  const lastTextPartIndex = parts.findLastIndex((p) => p?.type === "text");

  return (
    <Message from={message.role} data-testid={`msg-${message.id}`}>
      <MessageAvatar
        src={message.role === "user" ? "/avatar-user.svg" : "/avatar-ai.svg"}
        name={message.role === "user" ? "You" : "AI"}
      />
      <MessageContent>
        {parts.length > 0 ? (
          parts.map((part, idx) => {
            const partType = part?.type;

            if (partType === "text") {
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
                          schemaCard.data as Parameters<typeof BudgetChart>[0]["result"]
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

              // Animate Streamdown only for the last text part of assistant messages during streaming
              const shouldAnimate =
                isStreaming &&
                message.role === "assistant" &&
                idx === lastTextPartIndex;

              return (
                <Response key={`${message.id}-t-${idx}`} isAnimating={shouldAnimate}>
                  {text}
                </Response>
              );
            }

            if (partType === "source-url") {
              // Rendered separately in the Sources section below
              return null;
            }

            if (partType === "data-status") {
              return null;
            }

            if (partType === "reasoning") {
              return (
                <Reasoning
                  key={`${message.id}-r-${idx}`}
                  text={part.text ?? String(part)}
                />
              );
            }

            if (isStepStartPart(part)) {
              const step = part.step;

              return (
                <div
                  key={`${message.id}-step-${idx}`}
                  className="my-3 flex items-center gap-2 text-xs text-muted-foreground"
                >
                  <div className="h-px flex-1 bg-border" />
                  <span>{step !== undefined ? `Step ${step}` : "Step"}</span>
                  <div className="h-px flex-1 bg-border" />
                </div>
              );
            }

            const isToolLike =
              partType === "dynamic-tool" ||
              (typeof partType === "string" && partType.startsWith("tool-"));

            if (isToolLike) {
              type ToolPartLike = {
                type?: string;
                name?: string;
                toolName?: string;
                tool?: string;
                state?: string;
                status?: string;
                args?: unknown;
                input?: unknown;
                parameters?: unknown;
                result?: unknown;
                output?: unknown;
                data?: unknown;
                callProviderMetadata?: unknown;
                error?: unknown;
                errorText?: unknown;
              };

              const p = part as ToolPartLike;
              const inferredFromType =
                typeof partType === "string" && partType.startsWith("tool-")
                  ? partType.slice("tool-".length)
                  : undefined;
              const toolName = p?.name ?? p?.toolName ?? p?.tool ?? inferredFromType;
              const status = p?.state ?? p?.status;

              const raw = p?.result ?? p?.output ?? p?.data;
              const result =
                raw && typeof raw === "object" ? (raw as WebSearchUiResult) : undefined;

              if (toolName === "webSearch" && result && Array.isArray(result.results)) {
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
                          {(() => {
                            const href = safeHref(s.url);
                            const label = s.title ?? s.url;
                            if (!href) {
                              return <span className="font-medium">{label}</span>;
                            }
                            return (
                              <a
                                href={href}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-medium hover:underline"
                              >
                                {label}
                              </a>
                            );
                          })()}
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

              const rawInput = p?.args ?? p?.input ?? p?.parameters;
              const rawOutput =
                p?.result ??
                p?.output ??
                p?.data ??
                p?.error ??
                (typeof p?.errorText === "string" ? p.errorText : undefined);
              const rawProviderMetadata = p?.callProviderMetadata;
              const inputSanitized =
                rawInput !== undefined ? sanitizeToolOutput(rawInput) : undefined;
              const outputSanitized =
                rawOutput !== undefined ? sanitizeToolOutput(rawOutput) : undefined;
              const providerMetadataSanitized =
                rawProviderMetadata !== undefined
                  ? sanitizeToolOutput(rawProviderMetadata)
                  : undefined;

              return (
                <Tool
                  key={`${message.id}-tool-${idx}`}
                  input={inputSanitized}
                  name={toolName ?? "Tool"}
                  output={outputSanitized}
                  providerMetadata={providerMetadataSanitized}
                  status={status}
                />
              );
            }

            // File attachment part (includes images in AI SDK v6)
            if (partType === "file") {
              const filePart = AsRecord(part);
              if (!filePart) return null;
              const name =
                typeof filePart.name === "string" ? filePart.name : undefined;
              const filename =
                typeof filePart.filename === "string" ? filePart.filename : undefined;
              const fileName = name ?? filename ?? "Attachment";
              const mimeType = validateMimeType(
                (typeof filePart.mimeType === "string" && filePart.mimeType) ||
                  (typeof filePart.mediaType === "string" && filePart.mediaType) ||
                  undefined
              );
              const data =
                typeof filePart.data === "string" ? filePart.data : undefined;
              const url = typeof filePart.url === "string" ? filePart.url : undefined;
              const fileUrl =
                url ??
                (data && isValidBase64(data)
                  ? `data:${mimeType};base64,${data}`
                  : null);

              // Render images inline
              if (mimeType.startsWith("image/") && fileUrl) {
                const width =
                  typeof filePart.width === "number" && filePart.width > 0
                    ? filePart.width
                    : null;
                const height =
                  typeof filePart.height === "number" && filePart.height > 0
                    ? filePart.height
                    : null;
                const resolvedWidth = width ?? 640;
                const resolvedHeight = height ?? 480;
                const aspectRatio = `${resolvedWidth} / ${resolvedHeight}`;

                return (
                  <div key={`${message.id}-img-${idx}`} className="my-2">
                    <div
                      className="max-h-64 max-w-full overflow-hidden rounded-md border bg-muted/30"
                      style={{ aspectRatio }}
                    >
                      {/* biome-ignore lint/performance/noImgElement: External URLs without known dimensions */}
                      <img
                        src={fileUrl}
                        alt={fileName}
                        className="h-full w-full object-contain"
                        loading="lazy"
                        onError={(e) => {
                          e.currentTarget.style.display = "none";
                        }}
                        height={resolvedHeight}
                        width={resolvedWidth}
                      />
                    </div>
                  </div>
                );
              }

              // Render other files as attachment
              return (
                <div
                  key={`${message.id}-file-${idx}`}
                  className="my-2 inline-flex items-center gap-2 rounded-md border bg-muted/50 px-3 py-2"
                >
                  <FileIcon
                    aria-hidden="true"
                    className="size-4 text-muted-foreground"
                  />
                  <span className="text-sm font-medium">{fileName}</span>
                  <span className="text-xs text-muted-foreground">{mimeType}</span>
                </div>
              );
            }

            // Fallback for unknown part types
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

        {message.role === "assistant" &&
        (abortReason || finishReason || usageSummary) ? (
          <div className="mt-2 text-[11px] text-muted-foreground">
            {[
              abortReason ? `Abort: ${abortReason}` : null,
              finishReason ? `Finish: ${finishReason}` : null,
              usageSummary ? `Tokens: ${usageSummary}` : null,
            ]
              .filter(Boolean)
              .join(" | ")}
          </div>
        ) : null}
      </MessageContent>
    </Message>
  );
}