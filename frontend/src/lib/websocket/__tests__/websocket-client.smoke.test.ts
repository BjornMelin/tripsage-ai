/**
 * @fileoverview WebSocket client smoke tests for basic state and metrics.
 */

import { describe, expect, it } from "vitest";
import { ConnectionStatus, WebSocketClient } from "../websocket-client";

describe("WebSocketClient (smoke)", () => {
  it("initializes with disconnected state", () => {
    const client = new WebSocketClient({
      url: "ws://test",
      token: "t",
      connectionTimeout: 100,
      reconnectAttempts: 1,
      reconnectDelay: 10,
      heartbeatInterval: 1000,
    });
    const state = client.getState();
    expect(state.status).toBe(ConnectionStatus.DISCONNECTED);
    expect(state.reconnectAttempt).toBe(0);
  });

  it("moves to connected after auth response is handled", async () => {
    const client = new WebSocketClient({ url: "ws://t", token: "t" });
    // Bypass actual WebSocket by invoking internal handlers
    await (client as any).handleOpen(new Event("open"));
    (client as any).handleMessage(
      new MessageEvent("message", {
        data: JSON.stringify({ success: true, connection_id: "conn-1" }),
      })
    );
    const state = client.getState();
    expect(state.status).toBe(ConnectionStatus.CONNECTED);
    expect(state.connectionId).toBe("conn-1");
  });

  it("exposes performance metrics counters", async () => {
    const client = new WebSocketClient({ url: "ws://t", token: "t" });
    await (client as any).handleOpen(new Event("open"));
    (client as any).handleMessage(
      new MessageEvent("message", {
        data: JSON.stringify({ success: true, connection_id: "conn-2" }),
      })
    );
    const metrics = client.getPerformanceMetrics();
    expect(metrics).toHaveProperty("messagesSent");
    expect(metrics).toHaveProperty("messagesReceived");
  });
});
