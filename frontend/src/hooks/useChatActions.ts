/**
 * @fileoverview Orchestrator hook for combined chat and memory actions.
 *
 * Coordinates between chat-messages and chat-memory slices without creating
 * cross-slice dependencies. This hook provides high-level actions that combine
 * message operations with memory sync.
 */

import { useCallback } from "react";
import type { Message, SendMessageOptions } from "@/lib/schemas/chat";
import { useChatMemory } from "@/stores/chat/chat-memory";
import { useChatMessages } from "@/stores/chat/chat-messages";

/**
 * Hook for orchestrating chat actions with memory sync.
 *
 * Provides high-level actions that combine message operations with memory sync
 * without creating cross-slice dependencies in the stores themselves.
 *
 * @returns Object with orchestrated chat actions
 */
export function useChatActions() {
  const { addMessage, sendMessage, streamMessage } = useChatMessages();
  const { storeConversationMemory, syncMemoryToSession } = useChatMemory();

  /**
   * Add a message and optionally sync to memory.
   *
   * @param sessionId - Chat session ID
   * @param message - Message to add
   * @param syncMemory - Whether to sync to memory (default: true)
   * @returns Message ID
   */
  const addMessageWithMemory = useCallback(
    (
      sessionId: string,
      message: Omit<Message, "id" | "timestamp">,
      syncMemory = true
    ): string => {
      const messageId = addMessage(sessionId, message);

      if (syncMemory) {
        const session = useChatMessages
          .getState()
          .sessions.find((s) => s.id === sessionId);
        if (session?.userId) {
          // Sync memory in background (best-effort)
          storeConversationMemory(sessionId, session.userId, [
            {
              ...message,
              id: messageId,
              timestamp: new Date().toISOString(),
            } as Message,
          ]).catch((error) => {
            console.warn("Memory sync failed:", error);
          });
        }
      }

      return messageId;
    },
    [addMessage, storeConversationMemory]
  );

  /**
   * Send a message and sync to memory.
   *
   * @param content - Message content
   * @param options - Send message options
   */
  const sendMessageWithMemory = useCallback(
    async (content: string, options?: SendMessageOptions): Promise<void> => {
      await sendMessage(content, options);

      // Memory sync happens automatically via addMessageWithMemory if needed
      // This is a convenience wrapper that ensures memory sync is enabled
      const currentSession = useChatMessages.getState().currentSession;
      if (currentSession?.userId) {
        syncMemoryToSession(currentSession.id, currentSession.userId).catch((error) => {
          console.warn("Memory sync failed:", error);
        });
      }
    },
    [sendMessage, syncMemoryToSession]
  );

  /**
   * Stream a message and sync to memory.
   *
   * @param content - Message content
   * @param options - Send message options
   */
  const streamMessageWithMemory = useCallback(
    async (content: string, options?: SendMessageOptions): Promise<void> => {
      await streamMessage(content, options);

      // Memory sync happens after streaming completes
      const currentSession = useChatMessages.getState().currentSession;
      if (currentSession?.userId) {
        syncMemoryToSession(currentSession.id, currentSession.userId).catch((error) => {
          console.warn("Memory sync failed:", error);
        });
      }
    },
    [streamMessage, syncMemoryToSession]
  );

  return {
    addMessageWithMemory,
    sendMessageWithMemory,
    streamMessageWithMemory,
  };
}
