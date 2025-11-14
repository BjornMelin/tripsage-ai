import { describe, expect, it } from "vitest";
import { ConnectionStatus, useChatStore } from "../chat-store";

describe("chat-store realtime lifecycle", () => {
  it("disconnectRealtime resets realtime state and connection status", () => {
    const store = useChatStore.getState();

    // Prime some realtime state
    useChatStore.setState({
      connectionStatus: ConnectionStatus.Connected,
      pendingMessages: [{ content: "test", id: "1", role: "assistant", timestamp: "" }],
      realtimeChannel: {
        unsubscribe: () => {
          /* noop for test */
        },
      } as unknown as typeof store.realtimeChannel,
      typingUsers: { s1_u1: { timestamp: "", userId: "u1" } },
    });

    useChatStore.getState().disconnectRealtime();

    const next = useChatStore.getState();
    expect(next.connectionStatus).toBe(ConnectionStatus.Disconnected);
    expect(next.realtimeChannel).toBeNull();
    expect(next.pendingMessages).toEqual([]);
    expect(next.typingUsers).toEqual({});
  });
});
