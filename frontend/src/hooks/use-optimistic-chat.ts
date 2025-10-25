/**
 * @fileoverview React hook for optimistic chat updates.
 *
 * Provides optimistic UI updates for chat messages, showing messages
 * immediately while sending in the background.
 */

"use client";

import { useCallback, useOptimistic, useState } from "react";
import type { ChatMessage } from "./use-websocket-chat";

export interface OptimisticChatMessage extends ChatMessage {
  isOptimistic?: boolean;
}

export interface UseOptimisticChatOptions {
  messages: ChatMessage[];
  sendMessage: (content: string) => Promise<void>;
  currentUser: {
    id: string;
    name: string;
    avatar?: string;
  };
}

export interface UseOptimisticChatReturn {
  optimisticMessages: OptimisticChatMessage[];
  sendOptimisticMessage: (content: string) => Promise<void>;
  isPending: boolean;
  error: string | null;
}

/**
 * Hook for optimistic chat message updates.
 *
 * Shows messages immediately in UI while sending in background.
 *
 * @param options - Hook configuration options
 * @param options.messages - Current chat messages
 * @param options.sendMessage - Function to send messages
 * @param options.currentUser - Current user information
 * @returns Object with optimistic messages and send function
 */
export function useOptimisticChat({
  messages,
  sendMessage,
  currentUser,
}: UseOptimisticChatOptions): UseOptimisticChatReturn {
  const [isPending, setIsPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [optimisticMessages, addOptimisticMessage] = useOptimistic<
    OptimisticChatMessage[],
    OptimisticChatMessage
  >(
    messages.map((msg) => ({ ...msg, isOptimistic: false })),
    (currentMessages, newMessage) => [...currentMessages, newMessage]
  );

  const sendOptimisticMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) {
        return;
      }

      const optimisticMessage: OptimisticChatMessage = {
        id: crypto.randomUUID(),
        content: content.trim(),
        timestamp: new Date(),
        sender: currentUser,
        status: "sending",
        isOptimistic: true,
      };

      setIsPending(true);
      setError(null);

      // Add optimistic message immediately
      addOptimisticMessage(optimisticMessage);

      try {
        // Send actual message
        await sendMessage(content.trim());

        // The real message will come back through WebSocket and replace the optimistic one
        setIsPending(false);
      } catch (err) {
        setIsPending(false);
        setError(err instanceof Error ? err.message : "Failed to send message");

        // The optimistic message will remain in the list with error state
        // In a real implementation, you might want to update the message status
        console.error("Failed to send message:", err);
      }
    },
    [sendMessage, currentUser, addOptimisticMessage]
  );

  return {
    optimisticMessages,
    sendOptimisticMessage,
    isPending,
    error,
  };
}
