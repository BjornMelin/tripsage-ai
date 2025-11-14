/**
 * @fileoverview Chat page integrating AI Elements primitives with AI SDK v6.
 * Uses the official `useChat` hook to manage UI message streams and state.
 */

"use client";

import { useChat } from "@ai-sdk/react";
import type { FileUIPart, UIMessage } from "ai";
import { DefaultChatTransport } from "ai";
import { type ReactElement, useCallback, useEffect, useMemo, useState } from "react";
import { BudgetChart } from "@/components/ai-elements/budget-chart";
import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import { DestinationCard } from "@/components/ai-elements/destination-card";
import { FlightOfferCard } from "@/components/ai-elements/flight-card";
import { ItineraryTimeline } from "@/components/ai-elements/itinerary-timeline";
import {
  Message,
  MessageAvatar,
  MessageContent,
} from "@/components/ai-elements/message";
import {
  PromptInput,
  PromptInputActionAddAttachments,
  PromptInputActionMenu,
  PromptInputActionMenuContent,
  PromptInputActionMenuItem,
  PromptInputActionMenuTrigger,
  PromptInputAttachment,
  PromptInputAttachments,
  PromptInputBody,
  PromptInputFooter,
  PromptInputHeader,
  type PromptInputMessage,
  PromptInputProvider,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
} from "@/components/ai-elements/prompt-input";
import { Response } from "@/components/ai-elements/response";
import {
  Source,
  Sources,
  SourcesContent,
  SourcesTrigger,
} from "@/components/ai-elements/sources";
import { StayCard } from "@/components/ai-elements/stay-card";
import { useSupabase } from "@/lib/supabase";
import { parseSchemaCard } from "@/lib/ui/parse-schema-card";

/**
 * Resolve the authenticated Supabase user id for the current browser session.
 *
 * @returns The authenticated user's id or null when unauthenticated.
 */
function useCurrentUserId(): string | null {
  const supabase = useSupabase();
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    supabase.auth
      .getUser()
      .then(({ data }) => {
        if (isMounted) {
          setUserId(data.user?.id ?? null);
        }
      })
      .catch(() => {
        if (isMounted) setUserId(null);
      });

    const { data: authListener } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (!isMounted) return;
        setUserId(session?.user?.id ?? null);
      }
    );

    return () => {
      isMounted = false;
      authListener?.subscription.unsubscribe();
    };
  }, [supabase]);

  return userId;
}

/**
 * Render a single chat message including text, tool usage, and metadata parts.
 *
 * @param message UI message streamed by the AI SDK transport.
 * @returns Rendered message content.
 */
// Type intentionally inferred from parts; explicit alias not required.

function ChatMessageItem({ message }: { message: UIMessage }) {
  const parts = message.parts ?? [];
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

                // Fallback to plain text rendering
                return <Response key={`${message.id}-t-${idx}`}>{part.text}</Response>;
              }
              case "tool-call":
              case "tool-call-result":
                {
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
                  type WebSearchUiResult = {
                    results: Array<{ url: string; title?: string; snippet?: string }>;
                    fromCache?: boolean;
                    tookMs?: number;
                  };
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
                                <div className="mt-1 text-xs opacity-80">
                                  {s.snippet}
                                </div>
                              ) : null}
                              {"publishedAt" in s &&
                              (s as { publishedAt?: string }).publishedAt ? (
                                <div className="mt-1 text-[10px] opacity-60">
                                  {new Date(
                                    (s as { publishedAt?: string })
                                      .publishedAt as string
                                  ).toLocaleString()}
                                </div>
                              ) : null}
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
                }
                return (
                  <div
                    key={`${message.id}-tool-${idx}`}
                    className="my-2 rounded-md border bg-muted/30 p-3 text-xs"
                  >
                    <div className="mb-1 font-medium">Tool</div>
                    <pre className="overflow-x-auto whitespace-pre-wrap">
                      {JSON.stringify(part, null, 2)}
                    </pre>
                  </div>
                );
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
              default:
                return (
                  <pre key={`${message.id}-u-${idx}`} className="text-xs opacity-70">
                    {JSON.stringify(part)}
                  </pre>
                );
            }
          })
        ) : (
          <span className="opacity-70">(no content)</span>
        )}
        {/* Assistant citations (if provided) */}
        {message.role === "assistant" &&
        parts.some((p) => {
          if (typeof p !== "object" || p === null) return false;
          const r = p as Record<string, unknown>;
          return r.type === "source-url" && typeof r.url === "string";
        }) ? (
          <div className="mt-2">
            <Sources>
              <SourcesTrigger
                count={
                  parts.filter(
                    (p) =>
                      typeof p === "object" &&
                      p !== null &&
                      (p as Record<string, unknown>).type === "source-url"
                  ).length
                }
              />
              <SourcesContent>
                <div className="space-y-1">
                  {parts
                    .map((p, i) => ({ i, p }))
                    .filter(
                      ({ p }) =>
                        typeof p === "object" &&
                        p !== null &&
                        (p as Record<string, unknown>).type === "source-url" &&
                        typeof (p as Record<string, unknown>).url === "string"
                    )
                    .map(({ p, i }) => {
                      const rec = p as Record<string, unknown>;
                      const href = String(rec.url);
                      const title =
                        typeof rec.title === "string" ? rec.title : undefined;
                      return (
                        <Source key={`${message.id}-src-${i}`} href={href}>
                          {title ?? href}
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

/**
 * Chat page component using AI SDK v6 and AI Elements.
 *
 * Manages chat state, user authentication, and message streaming.
 * Filters system messages from display and handles input validation.
 *
 * @returns Chat interface with message history and input controls.
 */
export default function ChatPage(): ReactElement {
  // Get the current authenticated user ID for personalization
  const userId = useCurrentUserId();

  // Create chat transport with user-specific context for API requests
  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: "/api/chat/stream",
        // biome-ignore lint/style/useNamingConvention: API request body matches backend snake_case
        body: () => (userId ? { user_id: userId } : {}),
        credentials: "include",
        // Enable resumable streams by preparing a reconnect request when needed.
        prepareReconnectToStreamRequest: () => ({
          api: "/api/chat/stream",
          credentials: "include",
          headers: undefined,
        }),
        // Route to agent endpoints when metadata indicates agent request
        prepareSendMessagesRequest: ({ messages, id }) => {
          const last = messages[messages.length - 1];
          // biome-ignore lint/suspicious/noExplicitAny: Metadata shape is dynamic
          const md = (last && (last as any).metadata) || {};
          if (md.agent === "flightSearch" && md.request) {
            return {
              api: "/api/agents/flights",
              body: md.request,
              credentials: "include",
            };
          }
          if (md.agent === "accommodationSearch" && md.request) {
            return {
              api: "/api/agents/accommodations",
              body: md.request,
              credentials: "include",
            };
          }
          if (md.agent === "budgetPlanning" && md.request) {
            return {
              api: "/api/agents/budget",
              body: md.request,
              credentials: "include",
            };
          }
          if (md.agent === "memoryUpdate" && md.request) {
            return {
              api: "/api/agents/memory",
              body: md.request,
              credentials: "include",
            };
          }
          if (md.agent === "destinationResearch" && md.request) {
            return {
              api: "/api/agents/destinations",
              body: md.request,
              credentials: "include",
            };
          }
          if (md.agent === "itineraryPlanning" && md.request) {
            return {
              api: "/api/agents/itineraries",
              body: md.request,
              credentials: "include",
            };
          }
          // Default to general chat stream
          return {
            api: "/api/chat/stream",
            // biome-ignore lint/style/useNamingConvention: API request body matches backend snake_case
            body: { id, messages, ...(userId ? { user_id: userId } : {}) },
            credentials: "include",
          };
        },
      }),
    [userId]
  );

  // Initialize chat state management with AI SDK hooks
  const chatHelpers = useChat({
    id: userId ?? undefined,
    resume: true,
    transport,
  });

  const { messages, sendMessage, status, stop, regenerate, clearError, error } =
    chatHelpers;
  // Experimental resume helper; not part of stable types in all builds.
  const experimentalResume =
    // biome-ignore lint/style/useNamingConvention: External library API uses snake_case
    (chatHelpers as unknown as { experimental_resume?: () => Promise<unknown> })
      .experimental_resume;

  // Surface a brief toast when a resume attempt completes.
  const [showReconnected, setShowReconnected] = useState(false);
  useEffect(() => {
    let _mounted = true;
    let timeoutId: NodeJS.Timeout | undefined;
    const fn = experimentalResume as undefined | (() => Promise<unknown>);
    if (typeof fn === "function") {
      fn()
        .then(() => {
          setShowReconnected(true);
          timeoutId = setTimeout(() => setShowReconnected(false), 3000);
        })
        .catch((_err) => {
          /* Intentionally ignored to avoid UX disruption on reconnect */
        });
    }
    return () => {
      _mounted = false;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [experimentalResume]);

  // Filter out system messages from display (e.g., tool instructions)
  const visibleMessages = useMemo(
    () => messages.filter((message) => message.role !== "system"),
    [messages]
  );

  /**
   * Handle chat message submission.
   *
   * Validates input, clears errors, and sends message with files to API.
   *
   * @param text - User message text.
   * @param files - Attached files array.
   */
  const handleSubmit = useCallback(
    async ({ text, files }: PromptInputMessage) => {
      const normalizedText = (text ?? "").trim();
      const preparedFiles: FileUIPart[] | undefined =
        files && files.length > 0 ? files : undefined;

      if (!normalizedText && !preparedFiles) {
        return;
      }

      if (status === "error") {
        clearError();
      }

      await sendMessage({
        files: preparedFiles,
        metadata: userId ? { userId } : undefined,
        text: normalizedText,
      });
    },
    [clearError, sendMessage, status, userId]
  );

  // Determine button states based on current chat status
  const canStop = status === "streaming";
  const canRetry = visibleMessages.some((message) => message.role === "assistant");

  return (
    <div className="flex h-[calc(100vh-4rem)] flex-col">
      {showReconnected ? (
        <output
          data-testid="reconnected-toast"
          className="fixed right-4 top-4 z-50 rounded-md border bg-green-600/90 px-3 py-2 text-sm text-white shadow"
        >
          Reconnected
        </output>
      ) : null}
      {/* Main conversation area with message history */}
      <Conversation className="flex-1">
        <ConversationContent>
          {visibleMessages.length === 0 ? (
            <ConversationEmptyState description="Start a conversation to see messages here." />
          ) : (
            visibleMessages.map((message) => (
              <ChatMessageItem key={message.id} message={message} />
            ))
          )}
        </ConversationContent>
        <ConversationScrollButton />
      </Conversation>

      {/* Input controls and action buttons */}
      <div className="border-t p-2">
        <PromptInputProvider>
          <PromptInput onSubmit={handleSubmit}>
            <PromptInputHeader>
              <PromptInputTools>
                <PromptInputActionMenu>
                  <PromptInputActionMenuTrigger aria-label="More actions" />
                  <PromptInputActionMenuContent>
                    <PromptInputActionAddAttachments />
                    <PromptInputActionMenuItem
                      onSelect={() =>
                        sendMessage({
                          metadata: {
                            agent: "flightSearch",
                            request: {
                              cabinClass: "economy",
                              departureDate: "2025-12-15",
                              destination: "JFK",
                              origin: "SFO",
                              passengers: 1,
                              returnDate: "2025-12-19",
                            },
                          },
                          text: "Search flights",
                        })
                      }
                    >
                      Search flights
                    </PromptInputActionMenuItem>
                    <PromptInputActionMenuItem
                      onSelect={() =>
                        sendMessage({
                          metadata: {
                            agent: "accommodationSearch",
                            request: {
                              checkIn: "2025-12-15",
                              checkOut: "2025-12-19",
                              destination: "New York City",
                              guests: 2,
                            },
                          },
                          text: "Find stays",
                        })
                      }
                    >
                      Find stays
                    </PromptInputActionMenuItem>
                    <PromptInputActionMenuItem
                      onSelect={() =>
                        sendMessage({
                          metadata: {
                            agent: "budgetPlanning",
                            request: {
                              destination: "New York City",
                              durationDays: 5,
                              travelers: 2,
                            },
                          },
                          text: "Plan budget",
                        })
                      }
                    >
                      Plan budget
                    </PromptInputActionMenuItem>
                    <PromptInputActionMenuItem
                      onSelect={() =>
                        sendMessage({
                          metadata: {
                            agent: "destinationResearch",
                            request: {
                              destination: "Tokyo",
                            },
                          },
                          text: "Research destination",
                        })
                      }
                    >
                      Research destination
                    </PromptInputActionMenuItem>
                    <PromptInputActionMenuItem
                      onSelect={() =>
                        sendMessage({
                          metadata: {
                            agent: "itineraryPlanning",
                            request: {
                              destination: "Tokyo",
                              durationDays: 7,
                            },
                          },
                          text: "Plan itinerary",
                        })
                      }
                    >
                      Plan itinerary
                    </PromptInputActionMenuItem>
                  </PromptInputActionMenuContent>
                </PromptInputActionMenu>
              </PromptInputTools>
            </PromptInputHeader>
            <PromptInputBody>
              <PromptInputTextarea
                placeholder="Ask TripSage AI anything about travel planning…"
                aria-label="Chat prompt"
              />
              <div className="flex flex-wrap gap-2 px-2 py-1">
                <PromptInputAttachments>
                  {(file) => <PromptInputAttachment data={file} />}
                </PromptInputAttachments>
              </div>
            </PromptInputBody>
            <PromptInputFooter>
              <div className="flex w-full items-center justify-end gap-2">
                <button
                  type="button"
                  aria-label="Stop streaming"
                  className="rounded border px-3 py-1 text-sm disabled:opacity-50"
                  onClick={() => {
                    stop();
                  }}
                  disabled={!canStop}
                >
                  Stop
                </button>
                <button
                  type="button"
                  aria-label="Retry last request"
                  className="rounded border px-3 py-1 text-sm disabled:opacity-50"
                  onClick={() => {
                    regenerate();
                  }}
                  disabled={!canRetry || status === "streaming"}
                >
                  Retry
                </button>
                <div className="ml-auto">
                  <PromptInputSubmit status={status} />
                </div>
              </div>
              {error ? (
                <p className="mt-2 text-sm text-destructive">
                  {error.message ?? "Something went wrong. Please try again."}
                </p>
              ) : null}
            </PromptInputFooter>
          </PromptInput>
        </PromptInputProvider>
      </div>
    </div>
  );
}
