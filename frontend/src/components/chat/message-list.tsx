"use client";

import type { OptimisticChatMessage } from "@/hooks/use-optimistic-chat";
import { cn } from "@/lib/utils";
import { useCallback, useEffect, useRef } from "react";
import { ConnectionStatus } from "./connection-status";
import { MessageItem } from "./message-item";
import { TypingIndicator } from "./typing-indicator";

export interface MessageListProps {
  messages: OptimisticChatMessage[];
  currentUserId: string;
  typingUsers?: string[];
  connectionStatus?: "connecting" | "connected" | "disconnected" | "error";
  onReconnect?: () => void;
  className?: string;
  autoScroll?: boolean;
}

export function MessageList({
  messages,
  currentUserId,
  typingUsers = [],
  connectionStatus,
  onReconnect,
  className,
  autoScroll = true,
}: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const isUserScrolledRef = useRef(false);
  const lastScrollTopRef = useRef(0);

  // Check if user has scrolled away from the bottom
  const handleScroll = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 10;

    // Update user scroll state
    isUserScrolledRef.current = !isAtBottom;
    lastScrollTopRef.current = scrollTop;
  }, []);

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(
    (force = false) => {
      const container = containerRef.current;
      if (!container) return;

      if (force || (!isUserScrolledRef.current && autoScroll)) {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: "smooth",
        });
      }
    },
    [autoScroll]
  );

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages.length, scrollToBottom]);

  // Group messages by date for date separators
  const groupedMessages = messages.reduce(
    (groups, message, index) => {
      const messageDate = new Date(message.timestamp).toDateString();
      const prevMessage = messages[index - 1];
      const prevDate = prevMessage
        ? new Date(prevMessage.timestamp).toDateString()
        : null;

      if (messageDate !== prevDate) {
        groups.push({
          type: "date-separator" as const,
          date: messageDate,
        });
      }

      groups.push({
        type: "message" as const,
        message,
        isOwn: message.sender.id === currentUserId,
        showAvatar: shouldShowAvatar(message, messages[index - 1], currentUserId),
      });

      return groups;
    },
    [] as Array<
      | { type: "date-separator"; date: string }
      | {
          type: "message";
          message: OptimisticChatMessage;
          isOwn: boolean;
          showAvatar: boolean;
        }
    >
  );

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Connection status */}
      {connectionStatus && connectionStatus !== "connected" && (
        <ConnectionStatus status={connectionStatus} onReconnect={onReconnect} />
      )}

      {/* Messages container */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto overscroll-behavior-contain"
        style={{ scrollBehavior: "smooth" }}
      >
        {/* Empty state */}
        {messages.length === 0 && (
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-muted flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-muted-foreground"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-foreground mb-2">
                No messages yet
              </h3>
              <p className="text-sm text-muted-foreground">
                Start a conversation by sending your first message!
              </p>
            </div>
          </div>
        )}

        {/* Message list */}
        <div className="space-y-1">
          {groupedMessages.map((item, index) => {
            if (item.type === "date-separator") {
              return (
                <div key={`date-${item.date}`} className="flex justify-center py-2">
                  <div className="px-3 py-1 bg-muted rounded-full">
                    <span className="text-xs text-muted-foreground font-medium">
                      {formatDateSeparator(item.date)}
                    </span>
                  </div>
                </div>
              );
            }

            return (
              <MessageItem
                key={item.message.id}
                message={item.message}
                isOwn={item.isOwn}
                showAvatar={item.showAvatar}
              />
            );
          })}
        </div>

        {/* Typing indicator */}
        {typingUsers.length > 0 && <TypingIndicator users={typingUsers} />}

        {/* Scroll anchor */}
        <div className="h-4" />
      </div>

      {/* Scroll to bottom button */}
      {isUserScrolledRef.current && (
        <div className="absolute bottom-20 right-4">
          <button
            onClick={() => scrollToBottom(true)}
            className="bg-primary text-primary-foreground rounded-full p-2 shadow-lg hover:bg-primary/90 transition-colors"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 14l-7 7m0 0l-7-7m7 7V3"
              />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}

// Helper function to determine if avatar should be shown
function shouldShowAvatar(
  currentMessage: OptimisticChatMessage,
  previousMessage: OptimisticChatMessage | undefined,
  currentUserId: string
): boolean {
  if (!previousMessage) return true;

  // Always show avatar for own messages
  if (currentMessage.sender.id === currentUserId) return true;

  // Show avatar if sender changed
  if (currentMessage.sender.id !== previousMessage.sender.id) return true;

  // Show avatar if more than 5 minutes passed
  const timeDiff =
    new Date(currentMessage.timestamp).getTime() -
    new Date(previousMessage.timestamp).getTime();
  if (timeDiff > 5 * 60 * 1000) return true;

  return false;
}

// Helper function to format date separators
function formatDateSeparator(dateString: string): string {
  const date = new Date(dateString);
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  if (date.toDateString() === today.toDateString()) {
    return "Today";
  }
  if (date.toDateString() === yesterday.toDateString()) {
    return "Yesterday";
  }
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}
