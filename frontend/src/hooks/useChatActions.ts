/**
 * @fileoverview Orchestrator hook for combined chat actions.
 *
 * Provides high-level actions for chat operations. Memory sync is handled
 * server-side via the memory orchestrator, so client-side memory sync calls
 * have been removed.
 */

import { useCallback } from "react";
import type { Message, SendMessageOptions } from "@/lib/schemas/chat";
import { useChatMessages } from "@/stores/chat/chat-messages";

/**
 * Hook for orchestrating chat actions.
 *
 * Provides high-level actions for message operations. Memory sync happens
 * automatically server-side via the memory orchestrator when messages are
 * sent through the API routes.
 *
 * @returns Object with orchestrated chat actions
 */
export function useChatActions() {
  const { addMessage, sendMessage, streamMessage } = useChatMessages();

  /**
   * Add a message to a session.
   *
   * @param sessionId - Chat session ID
   * @param message - Message to add
   * @returns Message ID
   */
  const addMessageWithMemory = useCallback(
    (sessionId: string, message: Omit<Message, "id" | "timestamp">): string => {
      return addMessage(sessionId, message);
    },
    [addMessage]
  );

  /**
   * Send a message.
   *
   * @param content - Message content
   * @param options - Send message options
   */
  const sendMessageWithMemory = useCallback(
    async (content: string, options?: SendMessageOptions): Promise<void> => {
      await sendMessage(content, options);
      // Memory sync happens server-side via orchestrator
    },
    [sendMessage]
  );

  /**
   * Stream a message.
   *
   * @param content - Message content
   * @param options - Send message options
   */
  const streamMessageWithMemory = useCallback(
    async (content: string, options?: SendMessageOptions): Promise<void> => {
      await streamMessage(content, options);
      // Memory sync happens server-side via orchestrator
    },
    [streamMessage]
  );

  return {
    addMessageWithMemory,
    sendMessageWithMemory,
    streamMessageWithMemory,
  };
}
