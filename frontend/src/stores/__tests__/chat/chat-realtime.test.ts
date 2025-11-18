/** @vitest-environment jsdom */

import { act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useChatMessages } from "@/stores/chat/chat-messages";
import { useChatRealtime } from "@/stores/chat/chat-realtime";

describe("ChatRealtime", () => {
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
      // Memory sync handled server-side via orchestrator
    });
  });

  describe("setChatConnectionStatus", () => {
    it("updates connection status", () => {
      useChatRealtime.getState().setChatConnectionStatus("connected");
      expect(useChatRealtime.getState().connectionStatus).toBe("connected");
    });

    it("validates connection status against schema", () => {
      // Invalid status should not update
      const originalStatus = useChatRealtime.getState().connectionStatus;
      // @ts-expect-error - testing invalid status
      useChatRealtime.getState().setChatConnectionStatus("invalid");
      expect(useChatRealtime.getState().connectionStatus).toBe(originalStatus);
    });
  });

  describe("setRealtimeEnabled", () => {
    it("enables/disables realtime", () => {
      useChatRealtime.getState().setRealtimeEnabled(false);
      expect(useChatRealtime.getState().isRealtimeEnabled).toBe(false);
    });

    it("resets realtime state when disabled", () => {
      useChatRealtime.getState().setChatConnectionStatus("connected");
      useChatRealtime.getState().setUserTyping("session-1", "user-1");

      useChatRealtime.getState().setRealtimeEnabled(false);

      expect(useChatRealtime.getState().connectionStatus).toBe("disconnected");
      expect(Object.keys(useChatRealtime.getState().typingUsers)).toHaveLength(0);
    });
  });

  describe("setUserTyping", () => {
    it("adds typing user", () => {
      useChatRealtime.getState().setUserTyping("session-1", "user-1", "User");
      const typingUsers = useChatRealtime.getState().typingUsers;

      expect(typingUsers["session-1_user-1"]).toBeDefined();
      expect(typingUsers["session-1_user-1"]?.userId).toBe("user-1");
      expect(typingUsers["session-1_user-1"]?.username).toBe("User");
    });

    it("auto-removes typing user after timeout", () => {
      vi.useFakeTimers();
      useChatRealtime.getState().setUserTyping("session-1", "user-1");

      expect(useChatRealtime.getState().typingUsers["session-1_user-1"]).toBeDefined();

      vi.advanceTimersByTime(3000);

      expect(
        useChatRealtime.getState().typingUsers["session-1_user-1"]
      ).toBeUndefined();

      vi.useRealTimers();
    });
  });

  describe("removeUserTyping", () => {
    it("removes typing user", () => {
      useChatRealtime.getState().setUserTyping("session-1", "user-1");
      useChatRealtime.getState().removeUserTyping("session-1", "user-1");

      expect(
        useChatRealtime.getState().typingUsers["session-1_user-1"]
      ).toBeUndefined();
    });
  });

  describe("clearTypingUsers", () => {
    it("clears all typing users for a session", () => {
      useChatRealtime.getState().setUserTyping("session-1", "user-1");
      useChatRealtime.getState().setUserTyping("session-1", "user-2");
      useChatRealtime.getState().setUserTyping("session-2", "user-3");

      useChatRealtime.getState().clearTypingUsers("session-1");

      expect(
        useChatRealtime.getState().typingUsers["session-1_user-1"]
      ).toBeUndefined();
      expect(
        useChatRealtime.getState().typingUsers["session-1_user-2"]
      ).toBeUndefined();
      expect(useChatRealtime.getState().typingUsers["session-2_user-3"]).toBeDefined();
    });
  });

  describe("addPendingMessage", () => {
    it("adds message to pending queue", () => {
      const message = {
        content: "Pending",
        id: "msg-1",
        role: "user" as const,
        timestamp: "2024-01-01T00:00:00Z",
      };

      useChatRealtime.getState().addPendingMessage(message);

      expect(useChatRealtime.getState().pendingMessages).toHaveLength(1);
      expect(useChatRealtime.getState().pendingMessages[0]?.id).toBe("msg-1");
    });
  });

  describe("removePendingMessage", () => {
    it("removes message from pending queue", () => {
      const message = {
        content: "Pending",
        id: "msg-1",
        role: "user" as const,
        timestamp: "2024-01-01T00:00:00Z",
      };

      useChatRealtime.getState().addPendingMessage(message);
      useChatRealtime.getState().removePendingMessage("msg-1");

      expect(useChatRealtime.getState().pendingMessages).toHaveLength(0);
    });
  });

  describe("updateAgentStatus", () => {
    it("updates agent status for a session", () => {
      useChatRealtime.getState().updateAgentStatus("session-1", {
        currentTask: "Processing",
        isActive: true,
        progress: 50,
      });

      const status = useChatRealtime.getState().agentStatuses["session-1"];
      expect(status?.isActive).toBe(true);
      expect(status?.progress).toBe(50);
      expect(status?.currentTask).toBe("Processing");
    });

    it("merges with existing status", () => {
      useChatRealtime.getState().updateAgentStatus("session-1", {
        isActive: true,
        progress: 50,
      });

      useChatRealtime.getState().updateAgentStatus("session-1", {
        progress: 75,
      });

      const status = useChatRealtime.getState().agentStatuses["session-1"];
      expect(status?.isActive).toBe(true);
      expect(status?.progress).toBe(75);
    });
  });

  describe("handleTypingUpdate", () => {
    it("handles typing update broadcast", () => {
      useChatRealtime.getState().handleTypingUpdate("session-1", {
        isTyping: true,
        userId: "user-1",
      });

      expect(useChatRealtime.getState().typingUsers["session-1_user-1"]).toBeDefined();

      useChatRealtime.getState().handleTypingUpdate("session-1", {
        isTyping: false,
        userId: "user-1",
      });

      expect(
        useChatRealtime.getState().typingUsers["session-1_user-1"]
      ).toBeUndefined();
    });
  });

  describe("handleAgentStatusUpdate", () => {
    it("handles agent status broadcast", () => {
      useChatRealtime.getState().handleAgentStatusUpdate("session-1", {
        currentTask: "Working",
        isActive: true,
        progress: 60,
        statusMessage: "Almost done",
      });

      const status = useChatRealtime.getState().agentStatuses["session-1"];
      expect(status?.isActive).toBe(true);
      expect(status?.progress).toBe(60);
      expect(status?.currentTask).toBe("Working");
      expect(status?.statusMessage).toBe("Almost done");
    });
  });

  describe("resetRealtimeState", () => {
    it("resets all realtime state", () => {
      useChatRealtime.getState().setChatConnectionStatus("connected");
      useChatRealtime.getState().setUserTyping("session-1", "user-1");
      useChatRealtime.getState().addPendingMessage({
        content: "Test",
        id: "msg-1",
        role: "user",
        timestamp: "2024-01-01T00:00:00Z",
      });

      useChatRealtime.getState().resetRealtimeState();

      expect(useChatRealtime.getState().connectionStatus).toBe("disconnected");
      expect(Object.keys(useChatRealtime.getState().typingUsers)).toHaveLength(0);
      expect(useChatRealtime.getState().pendingMessages).toHaveLength(0);
    });
  });
});
