/** @vitest-environment jsdom */

import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test/test-utils";
import { withFakeTimers } from "@/test/utils/with-fake-timers";
import { ConnectionStatus } from "../connection-status";

describe("ConnectionStatus", () => {
  it("renders detailed metrics when connected", () => {
    renderWithProviders(
      <ConnectionStatus
        status="connected"
        variant="detailed"
        metrics={{
          bandwidth: 1024,
          jitter: 5,
          latency: 120,
          packetLoss: 0.1,
          quality: "good",
          signalStrength: 82,
        }}
        analytics={{
          avgResponseTime: 120,
          connectionTime: 10,
          failedMessages: 0,
          reconnectCount: 0,
          totalMessages: 10,
          uptime: 120,
        }}
      />
    );

    expect(screen.getByText("Latency")).toBeInTheDocument();
    expect(screen.getByText("Uptime")).toBeInTheDocument();
    expect(screen.getByText("Connected")).toBeInTheDocument();
  });

  it(
    "timestamps last-connected status from the canonical clock helper",
    withFakeTimers(() => {
      const fixedNowIso = "2026-02-03T04:05:06.000Z";
      const expectedTime = new Date(fixedNowIso).toLocaleTimeString();
      vi.setSystemTime(new Date(fixedNowIso));

      const { rerender } = renderWithProviders(
        <ConnectionStatus status="connected" variant="detailed" showMetrics={false} />
      );

      expect(screen.getByText("Connected")).toBeInTheDocument();

      rerender(
        <ConnectionStatus
          status="disconnected"
          variant="detailed"
          showMetrics={false}
        />
      );

      expect(screen.getByText(`Last connected: ${expectedTime}`)).toBeInTheDocument();
    })
  );
});
