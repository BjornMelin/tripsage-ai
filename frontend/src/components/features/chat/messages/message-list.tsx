"use client";

import React, { useEffect, useRef } from "react";
import type { Message, ToolCall, ToolResult } from "@/types/chat";
import { cn } from "@/lib/utils";
import MessageItem from "./message-item";
import { Loader2 } from "lucide-react";

interface MessageListProps {
  messages: Message[];
  isStreaming?: boolean;
  className?: string;
  activeToolCalls?: ToolCall[];
  toolResults?: ToolResult[];
  onRetryToolCall?: (toolCallId: string) => void;
  onCancelToolCall?: (toolCallId: string) => void;
}

export default function MessageList({
  messages,
  isStreaming,
  className,
  activeToolCalls,
  toolResults,
  onRetryToolCall,
  onCancelToolCall,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Track if the user has scrolled up (not at the bottom)
  const [userScrolledUp, setUserScrolledUp] = React.useState(false);

  // Scroll to bottom when new messages arrive or content streams
  useEffect(() => {
    if (bottomRef.current && containerRef.current) {
      const container = containerRef.current;

      // Check if user has scrolled up
      const isAtBottom =
        container.scrollHeight - container.clientHeight - container.scrollTop <
        100;

      // Auto-scroll if at bottom or a new message arrives from the user
      const lastMessage = messages[messages.length - 1];
      const isNewUserMessage = lastMessage && lastMessage.role === "USER";

      if (isAtBottom || isNewUserMessage || isStreaming) {
        bottomRef.current.scrollIntoView({
          behavior: userScrolledUp ? "auto" : "smooth",
        });
        setUserScrolledUp(false);
      }
    }
  }, [messages, messages.length, isStreaming, userScrolledUp]);

  // Detect when user scrolls up
  const handleScroll = () => {
    if (containerRef.current) {
      const container = containerRef.current;
      const isAtBottom =
        container.scrollHeight - container.clientHeight - container.scrollTop <
        100;

      setUserScrolledUp(!isAtBottom);
    }
  };

  // Welcome messages for empty state
  const emptyStateMessages = [
    "Welcome to TripSage! How can I help with your travel plans today?",
    "I can assist with flight searches, accommodation recommendations, and creating personalized itineraries.",
    "Try asking about destinations, budget planning, or hidden gems in your next travel spot!",
  ];

  return (
    <div
      ref={containerRef}
      className={cn("flex-1 overflow-y-auto pb-10", className)}
      onScroll={handleScroll}
    >
      <div className="space-y-6 px-4 pt-4">
        {messages.length === 0 ? (
          <div className="flex flex-col space-y-6 items-center justify-center py-10 text-center">
            <div className="max-w-lg space-y-6">
              <h3 className="text-xl font-semibold text-primary">
                Welcome to TripSage AI Assistant
              </h3>

              <div className="space-y-4">
                {emptyStateMessages.map((msg, i) => (
                  <div
                    key={i}
                    className="p-4 rounded-lg bg-secondary/20 text-muted-foreground"
                  >
                    {msg}
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-4">
                {[
                  "Where should I go for a budget-friendly beach vacation?",
                  "Plan a 7-day trip to Japan in spring.",
                  "What are the best hiking trails in Colorado?",
                  "Find me family-friendly activities in Barcelona.",
                ].map((suggestion, i) => (
                  <button
                    key={i}
                    className="p-3 text-sm rounded-lg border bg-card hover:bg-secondary text-left"
                    onClick={() => {
                      const input = document.querySelector("textarea");
                      if (input) {
                        const nativeInputValueSetter =
                          Object.getOwnPropertyDescriptor(
                            window.HTMLTextAreaElement.prototype,
                            "value"
                          )?.set;

                        if (nativeInputValueSetter) {
                          nativeInputValueSetter.call(input, suggestion);
                          input.dispatchEvent(
                            new Event("input", { bubbles: true })
                          );
                        }
                      }
                    }}
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageItem 
                key={message.id} 
                message={message}
                activeToolCalls={activeToolCalls}
                toolResults={toolResults}
                onRetryToolCall={onRetryToolCall}
                onCancelToolCall={onCancelToolCall}
              />
            ))}
          </>
        )}

        {isStreaming && (
          <div className="flex items-center justify-center py-2">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">
              TripSage is responding...
            </span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
