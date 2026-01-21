import { render, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const INIT_TELEMETRY = vi.hoisted(() => vi.fn());

vi.mock("@/lib/telemetry/client", () => ({
  initTelemetry: INIT_TELEMETRY,
}));

import { TelemetryProvider } from "./telemetry-provider";

describe("TelemetryProvider", () => {
  it("lazy-loads and initializes telemetry on mount", async () => {
    render(<TelemetryProvider />);

    await waitFor(() => {
      expect(INIT_TELEMETRY).toHaveBeenCalledTimes(1);
    });
  });
});
