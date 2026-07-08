/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import { WEB_VITALS_ENDPOINT } from "@/lib/telemetry/web-vitals";
import { createMockNextRequest, createRouteParamsContext } from "@/test/helpers/route";

const recordTelemetryEvent = vi.fn();
let capturedRateLimit: string | undefined;
let capturedDegradedMode: string | undefined;
const WEB_VITALS_URL = `http://localhost${WEB_VITALS_ENDPOINT}`;
const VALID_LCP_PAYLOAD = {
  delta: 15,
  name: "LCP",
  route: "/",
  value: 1800,
} as const;

vi.mock("@/lib/telemetry/span", () => ({
  recordTelemetryEvent,
}));

vi.mock("@/lib/api/factory", () => ({
  withApiGuards: (options: { degradedMode?: string; rateLimit?: string }) => {
    capturedDegradedMode = options.degradedMode;
    capturedRateLimit = options.rateLimit;
    return (handler: unknown) => handler;
  },
}));

async function postWebVitals(body: Record<string, unknown>) {
  const { POST } = await import("../route");
  const request = createMockNextRequest({
    body,
    method: "POST",
    url: WEB_VITALS_URL,
  });

  return POST(request, createRouteParamsContext());
}

function expectWebVitalsRecorded(
  attributes: Record<string, unknown>,
  level: "info" | "warning" = "info"
) {
  expect(recordTelemetryEvent).toHaveBeenCalledWith("web_vitals.reported", {
    attributes,
    level,
  });
}

describe("POST /api/telemetry/web-vitals", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.resetModules();
    capturedDegradedMode = undefined;
    capturedRateLimit = undefined;
  });

  it("uses telemetry rate limiting and records valid Web Vitals", async () => {
    const response = await postWebVitals({
      ...VALID_LCP_PAYLOAD,
      delta: 120.4,
      navigationType: "navigate",
      rating: "needs-improvement",
      route: "/dashboard/trips/:uuid",
      value: 2500.3,
    });

    expect(capturedDegradedMode).toBeUndefined();
    expect(capturedRateLimit).toBe("telemetry:post");
    expect(response.status).toBe(200);
    expectWebVitalsRecorded({
      clientMetricRating: "needs-improvement",
      metricDelta: 120,
      metricName: "LCP",
      metricValue: 2500,
      navigationType: "navigate",
      route: "/dashboard/trips/:uuid",
    });
  });

  it("collapses unknown routes before recording telemetry", async () => {
    const response = await postWebVitals({
      ...VALID_LCP_PAYLOAD,
      route: "/private/customer-name",
    });

    expect(response.status).toBe(200);
    expectWebVitalsRecorded({
      clientMetricRating: "unknown",
      metricDelta: 15,
      metricName: "LCP",
      metricValue: 1800,
      navigationType: "unknown",
      route: "/unknown",
    });
  });

  it("keeps client-supplied poor ratings at info level", async () => {
    const response = await postWebVitals({
      ...VALID_LCP_PAYLOAD,
      delta: 0.1234,
      name: "CLS",
      rating: "poor",
      value: 0.3149,
    });

    expect(response.status).toBe(200);
    expectWebVitalsRecorded({
      clientMetricRating: "poor",
      metricDelta: 0.123,
      metricName: "CLS",
      metricValue: 0.315,
      navigationType: "unknown",
      route: "/",
    });
  });

  it("rejects invalid metric names and high-cardinality routes", async () => {
    const response = await postWebVitals({
      ...VALID_LCP_PAYLOAD,
      delta: 1,
      name: "Custom",
      route: "/dashboard/trips?id=abc",
      value: 1,
    });

    const body = (await response.json()) as {
      error?: string;
      issues?: Array<{ path: Array<string | number> }>;
    };

    expect(response.status).toBe(400);
    expect(body.error).toBe("invalid_request");
    expect(body.issues?.some((issue) => issue.path[0] === "name")).toBe(true);
    expect(body.issues?.some((issue) => issue.path[0] === "route")).toBe(true);
    expect(recordTelemetryEvent).not.toHaveBeenCalled();
  });

  it("rejects unsupported navigation types", async () => {
    const response = await postWebVitals({
      ...VALID_LCP_PAYLOAD,
      delta: 1,
      navigationType: "custom-flow",
      value: 1,
    });

    const body = (await response.json()) as {
      error?: string;
      issues?: Array<{ path: Array<string | number> }>;
    };

    expect(response.status).toBe(400);
    expect(body.error).toBe("invalid_request");
    expect(body.issues?.some((issue) => issue.path[0] === "navigationType")).toBe(true);
    expect(recordTelemetryEvent).not.toHaveBeenCalled();
  });

  it("rejects absurd client-controlled metric values", async () => {
    const response = await postWebVitals({
      ...VALID_LCP_PAYLOAD,
      value: 1_000_000,
    });
    const body = (await response.json()) as { error?: string; reason?: string };

    expect(response.status).toBe(400);
    expect(body.error).toBe("invalid_request");
    expect(body.reason).toBe("Web Vitals metric value out of accepted range");
    expect(recordTelemetryEvent).not.toHaveBeenCalled();
  });
});
