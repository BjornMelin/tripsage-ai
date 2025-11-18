/** @vitest-environment jsdom */

import { act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useChatMemory } from "@/stores/chat/chat-memory";
import { useChatMessages } from "@/stores/chat/chat-messages";
import { useChatRealtime } from "@/stores/chat/chat-realtime";

describe("ChatMessages", () => {
  beforeEach(() => {
    act(() => {
      useChatMessages.setState({
        currentSessionId: null,
        error: null,
        isLoading: false,
        isStreaming: false,
        sessions: [],
      });
      useChatRealtime.setState({
        agentStatuses: {},
        connectionStatus: "disconnected",
        isRealtimeEnabled: true,
        pendingMessages: [],
        typingUsers: {},
      });
      useChatMemory.setState({
        autoSyncMemory: true,
        lastMemorySyncs: {},
        memoryContexts: {},
        memoryEnabled: true,
      });
    });
  });

  describe("createSession", () => {
    it("creates a new session with default title", () => {
      const sessionId = useChatMessages.getState().createSession();

      expect(sessionId).toBeTruthy();
      const session = useChatMessages
        .getState()
        .sessions.find((s) => s.id === sessionId);
      expect(session).toBeDefined();
      expect(session?.title).toBe("New Conversation");
      expect(session?.messages).toEqual([]);
    });

    it("creates a session with custom title and userId", () => {
      const sessionId = useChatMessages
        .getState()
        .createSession("Custom Title", "user-123");

      const session = useChatMessages
        .getState()
        .sessions.find((s) => s.id === sessionId);
      expect(session?.title).toBe("Custom Title");
      expect(session?.userId).toBe("user-123");
    });

    it("sets the new session as current", () => {
      const sessionId = useChatMessages.getState().createSession();
      expect(useChatMessages.getState().currentSessionId).toBe(sessionId);
    });
  });

  describe("setCurrentSession", () => {
    it("sets the current session", () => {
      const sessionId = useChatMessages.getState().createSession();
      useChatMessages.getState().setCurrentSession(sessionId);
      expect(useChatMessages.getState().currentSessionId).toBe(sessionId);
    });
  });

  describe("deleteSession", () => {
    it("deletes a session", () => {
      const sessionId = useChatMessages.getState().createSession();
      useChatMessages.getState().deleteSession(sessionId);

      const session = useChatMessages
        .getState()
        .sessions.find((s) => s.id === sessionId);
      expect(session).toBeUndefined();
    });

    it("selects first available session when deleting current", () => {
      const session1 = useChatMessages.getState().createSession("Session 1");
      const session2 = useChatMessages.getState().createSession("Session 2");

      useChatMessages.getState().setCurrentSession(session1);
      useChatMessages.getState().deleteSession(session1);

      expect(useChatMessages.getState().currentSessionId).toBe(session2);
    });

    it("sets currentSessionId to null when deleting last session", () => {
      const sessionId = useChatMessages.getState().createSession();
      useChatMessages.getState().deleteSession(sessionId);

      expect(useChatMessages.getState().currentSessionId).toBeNull();
    });
  });

  describe("addMessage", () => {
    it("adds a message to a session", () => {
      const sessionId = useChatMessages.getState().createSession();
      const messageId = useChatMessages.getState().addMessage(sessionId, {
        content: "Hello",
        role: "user",
      });

      expect(messageId).toBeTruthy();
      const session = useChatMessages
        .getState()
        .sessions.find((s) => s.id === sessionId);
      expect(session?.messages).toHaveLength(1);
      expect(session?.messages?.[0]?.content).toBe("Hello");
      expect(session?.messages?.[0]?.role).toBe("user");
    });

    it("updates session updatedAt timestamp", () => {
      const sessionId = useChatMessages.getState().createSession();
      const originalUpdatedAt = useChatMessages
        .getState()
        .sessions.find((s) => s.id === sessionId)?.updatedAt;

      // Wait a bit to ensure timestamp difference
      vi.useFakeTimers();
      vi.advanceTimersByTime(1000);

      useChatMessages.getState().addMessage(sessionId, {
        content: "Test",
        role: "user",
      });

      const updatedAt = useChatMessages
        .getState()
        .sessions.find((s) => s.id === sessionId)?.updatedAt;

      expect(updatedAt).not.toBe(originalUpdatedAt);
      vi.useRealTimers();
    });
  });

  describe("updateMessage", () => {
    it("updates a message in a session", () => {
      const sessionId = useChatMessages.getState().createSession();
      const messageId = useChatMessages.getState().addMessage(sessionId, {
        content: "Original",
        role: "user",
      });

      useChatMessages.getState().updateMessage(sessionId, messageId, {
        content: "Updated",
      });

      const session = useChatMessages
        .getState()
        .sessions.find((s) => s.id === sessionId);
      expect(session?.messages?.[0]?.content).toBe("Updated");
    });
  });

  describe("clearMessages", () => {
    it("clears all messages from a session", () => {
      const sessionId = useChatMessages.getState().createSession();
      useChatMessages.getState().addMessage(sessionId, {
        content: "Message 1",
        role: "user",
      });
      useChatMessages.getState().addMessage(sessionId, {
        content: "Message 2",
        role: "assistant",
      });

      useChatMessages.getState().clearMessages(sessionId);

      const session = useChatMessages
        .getState()
        .sessions.find((s) => s.id === sessionId);
      expect(session?.messages).toEqual([]);
    });
  });

  describe("currentSession computed", () => {
    it("returns null when no current session", () => {
      expect(useChatMessages.getState().currentSession).toBeNull();
    });

    it("returns the current session", () => {
      const sessionId = useChatMessages.getState().createSession("Test");
      const state = useChatMessages.getState();
      const currentSession = state.currentSession;

      expect(currentSession).toBeDefined();
      expect(currentSession?.id).toBe(sessionId);
      expect(currentSession?.title).toBe("Test");
      // Verify the session exists in sessions array
      expect(state.sessions.find((s) => s.id === sessionId)).toBeDefined();
      expect(state.currentSessionId).toBe(sessionId);
    });
  });

  describe("exportSessionData", () => {
    it("exports session data as JSON", () => {
      const sessionId = useChatMessages.getState().createSession("Test");
      useChatMessages.getState().addMessage(sessionId, {
        content: "Test message",
        role: "user",
      });

      const exported = useChatMessages.getState().exportSessionData(sessionId);
      const parsed = JSON.parse(exported);

      expect(parsed.title).toBe("Test");
      expect(parsed.messages).toHaveLength(1);
    });

    it("returns empty string for non-existent session", () => {
      const exported = useChatMessages.getState().exportSessionData("non-existent");
      expect(exported).toBe("");
    });
  });

  describe("importSessionData", () => {
    it("imports session data from JSON", () => {
      const sessionData = {
        createdAt: "2024-01-01T00:00:00Z",
        id: "original-id",
        messages: [
          {
            content: "Hello",
            id: "msg-1",
            role: "user" as const,
            timestamp: "2024-01-01T00:00:00Z",
          },
        ],
        title: "Imported Session",
        updatedAt: "2024-01-01T00:00:00Z",
      };

      const sessionId = useChatMessages
        .getState()
        .importSessionData(JSON.stringify(sessionData));

      expect(sessionId).toBeTruthy();
      const session = useChatMessages
        .getState()
        .sessions.find((s) => s.id === sessionId);
      expect(session?.title).toBe("Imported Session (Imported)");
      expect(session?.messages).toHaveLength(1);
    });

    it("returns null for invalid JSON", () => {
      const sessionId = useChatMessages.getState().importSessionData("invalid");
      expect(sessionId).toBeNull();
      expect(useChatMessages.getState().error).toBeTruthy();
    });
  });
});
