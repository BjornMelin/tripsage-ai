import { beforeEach, describe, expect, it, vi } from "vitest";
import { useChatMemory } from "@/stores/chat/chat-memory";
import { resetChatSlices } from "./_shared";

// Mock QStash enqueue functions
vi.mock("@/lib/qstash/memory-sync", () => ({
  enqueueConversationMemorySync: vi.fn().mockResolvedValue({
    idempotencyKey: "key-123",
    messageId: "msg-123",
  }),
  enqueueFullMemorySync: vi.fn().mockResolvedValue({
    idempotencyKey: "key-456",
    messageId: "msg-456",
  }),
  enqueueIncrementalMemorySync: vi.fn().mockResolvedValue({
    idempotencyKey: "key-789",
    messageId: "msg-789",
  }),
}));

describe("ChatMemory", () => {
  beforeEach(() => {
    resetChatSlices();
  });

  describe("setMemoryEnabled", () => {
    it("enables/disables memory", () => {
      useChatMemory.getState().setMemoryEnabled(false);
      expect(useChatMemory.getState().memoryEnabled).toBe(false);

      useChatMemory.getState().setMemoryEnabled(true);
      expect(useChatMemory.getState().memoryEnabled).toBe(true);
    });
  });

  describe("setAutoSyncMemory", () => {
    it("enables/disables auto-sync", () => {
      useChatMemory.getState().setAutoSyncMemory(false);
      expect(useChatMemory.getState().autoSyncMemory).toBe(false);

      useChatMemory.getState().setAutoSyncMemory(true);
      expect(useChatMemory.getState().autoSyncMemory).toBe(true);
    });
  });

  describe("updateSessionMemoryContext", () => {
    it("updates memory context for a session", () => {
      const context = {
        context: "User prefers beach destinations",
        score: 0.9,
        source: "conversation-history",
      };

      useChatMemory.getState().updateSessionMemoryContext("session-1", context);

      const storedContext = useChatMemory.getState().memoryContexts["session-1"];
      expect(storedContext).toEqual(context);
    });

    it("updates lastMemorySync timestamp", () => {
      const context = {
        context: "Test context",
        score: 0.8,
      };

      useChatMemory.getState().updateSessionMemoryContext("session-1", context);

      const lastSync = useChatMemory.getState().lastMemorySyncs["session-1"];
      expect(lastSync).toBeTruthy();
      expect(new Date(lastSync).getTime()).toBeLessThanOrEqual(Date.now());
    });
  });

  describe("syncMemoryToSession", () => {
    it("does nothing when memory is disabled", async () => {
      useChatMemory.getState().setMemoryEnabled(false);
      const { enqueueFullMemorySync } = await import("@/lib/qstash/memory-sync");

      await useChatMemory.getState().syncMemoryToSession("session-1", "user-123");

      expect(enqueueFullMemorySync).not.toHaveBeenCalled();
    });

    it("enqueues full sync when no recent sync", async () => {
      useChatMemory.getState().setMemoryEnabled(true);
      const { enqueueFullMemorySync } = await import("@/lib/qstash/memory-sync");

      await useChatMemory.getState().syncMemoryToSession("session-1", "user-123");

      expect(enqueueFullMemorySync).toHaveBeenCalledWith("session-1", "user-123");
    });

    it("enqueues incremental sync when recent sync exists", async () => {
      useChatMemory.getState().setMemoryEnabled(true);
      const recentTimestamp = new Date(Date.now() - 60 * 60 * 1000).toISOString(); // 1 hour ago
      useChatMemory.setState({
        lastMemorySyncs: { "session-1": recentTimestamp },
      });

      const { enqueueIncrementalMemorySync } = await import("@/lib/qstash/memory-sync");

      await useChatMemory.getState().syncMemoryToSession("session-1", "user-123");

      expect(enqueueIncrementalMemorySync).toHaveBeenCalledWith(
        "session-1",
        "user-123"
      );
    });

    it("updates lastMemorySync timestamp", async () => {
      useChatMemory.getState().setMemoryEnabled(true);

      await useChatMemory.getState().syncMemoryToSession("session-1", "user-123");

      const lastSync = useChatMemory.getState().lastMemorySyncs["session-1"];
      expect(lastSync).toBeTruthy();
    });
  });

  describe("storeConversationMemory", () => {
    it("does nothing when memory is disabled", async () => {
      useChatMemory.getState().setMemoryEnabled(false);
      const { enqueueConversationMemorySync } = await import(
        "@/lib/qstash/memory-sync"
      );

      await useChatMemory.getState().storeConversationMemory("session-1", "user-123");

      expect(enqueueConversationMemorySync).not.toHaveBeenCalled();
    });

    it("does nothing when auto-sync is disabled", async () => {
      useChatMemory.getState().setMemoryEnabled(true);
      useChatMemory.getState().setAutoSyncMemory(false);
      const { enqueueConversationMemorySync } = await import(
        "@/lib/qstash/memory-sync"
      );

      await useChatMemory.getState().storeConversationMemory("session-1", "user-123");

      expect(enqueueConversationMemorySync).not.toHaveBeenCalled();
    });

    it("does nothing when no messages provided", async () => {
      useChatMemory.getState().setMemoryEnabled(true);
      useChatMemory.getState().setAutoSyncMemory(true);
      const { enqueueConversationMemorySync } = await import(
        "@/lib/qstash/memory-sync"
      );

      await useChatMemory
        .getState()
        .storeConversationMemory("session-1", "user-123", []);

      expect(enqueueConversationMemorySync).not.toHaveBeenCalled();
    });

    it("enqueues conversation memory sync when enabled", async () => {
      useChatMemory.getState().setMemoryEnabled(true);
      useChatMemory.getState().setAutoSyncMemory(true);
      const { enqueueConversationMemorySync } = await import(
        "@/lib/qstash/memory-sync"
      );

      const messages = [
        {
          attachments: [],
          content: "Hello",
          id: "msg-1",
          role: "user" as const,
          timestamp: "2024-01-01T00:00:00Z",
          toolCalls: [],
          toolResults: [],
        },
      ];

      await useChatMemory
        .getState()
        .storeConversationMemory("session-1", "user-123", messages);

      expect(enqueueConversationMemorySync).toHaveBeenCalledWith(
        "session-1",
        "user-123",
        [
          {
            content: "Hello",
            metadata: {
              attachments: [],
              toolCalls: [],
              toolResults: [],
            },
            role: "user",
            timestamp: "2024-01-01T00:00:00Z",
          },
        ]
      );
    });

    it("updates lastMemorySync timestamp", async () => {
      useChatMemory.getState().setMemoryEnabled(true);
      useChatMemory.getState().setAutoSyncMemory(true);

      const messages = [
        {
          content: "Test",
          id: "msg-1",
          role: "user" as const,
          timestamp: "2024-01-01T00:00:00Z",
        },
      ];

      await useChatMemory
        .getState()
        .storeConversationMemory("session-1", "user-123", messages);

      const lastSync = useChatMemory.getState().lastMemorySyncs["session-1"];
      expect(lastSync).toBeTruthy();
    });
  });
});
