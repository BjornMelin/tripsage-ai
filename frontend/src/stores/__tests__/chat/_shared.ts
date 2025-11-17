/**
 * @fileoverview Shared test utilities and helpers for chat slice tests.
 */

import { act } from "@testing-library/react";
import { useChatMemory } from "@/stores/chat/chat-memory";
import { useChatMessages } from "@/stores/chat/chat-messages";
import { useChatRealtime } from "@/stores/chat/chat-realtime";

/**
 * Resets all chat slices to their initial state.
 */
export const resetChatSlices = (): void => {
  act(() => {
    // Reset chat-messages slice
    useChatMessages.setState({
      currentSessionId: null,
      error: null,
      isLoading: false,
      isStreaming: false,
      sessions: [],
    });

    // Reset chat-realtime slice
    useChatRealtime.setState({
      agentStatuses: {},
      connectionStatus: "disconnected",
      isRealtimeEnabled: true,
      pendingMessages: [],
      typingUsers: {},
    });

    // Reset chat-memory slice
    useChatMemory.setState({
      autoSyncMemory: true,
      lastMemorySyncs: {},
      memoryContexts: {},
      memoryEnabled: true,
    });
  });
};
