/** @vitest-environment jsdom */
import { render, waitFor } from "@testing-library/react";
import { afterAll, describe, expect, it, vi } from "vitest";

const INIT_TELEMETRY = vi.hoisted(() => vi.fn());

const PREV_ENV = vi.hoisted(() => ({
  enabled: process.env.NEXT_PUBLIC_OTEL_CLIENT_ENABLED,
  endpoint: process.env.NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT,
}));

vi.hoisted(() => {
  process.env.NEXT_PUBLIC_OTEL_CLIENT_ENABLED = "true";
  process.env.NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT =
    "http://localhost:4318/v1/traces";
});

vi.mock("@/lib/telemetry/client", () => ({
  initTelemetry: INIT_TELEMETRY,
}));

import { TelemetryProvider } from "./telemetry-provider";

describe("TelemetryProvider", () => {
  afterAll(() => {
    if (PREV_ENV.enabled === undefined) {
      process.env.NEXT_PUBLIC_OTEL_CLIENT_ENABLED = undefined;
    } else {
      process.env.NEXT_PUBLIC_OTEL_CLIENT_ENABLED = PREV_ENV.enabled;
    }

    if (PREV_ENV.endpoint === undefined) {
      process.env.NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT = undefined;
    } else {
      process.env.NEXT_PUBLIC_OTEL_EXPORTER_OTLP_ENDPOINT = PREV_ENV.endpoint;
    }
  });

  it("lazy-loads and initializes telemetry on mount", async () => {
    render(<TelemetryProvider />);

    await waitFor(() => {
      expect(INIT_TELEMETRY).toHaveBeenCalledTimes(1);
    });
  });
});
