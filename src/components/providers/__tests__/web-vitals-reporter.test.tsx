/** @vitest-environment jsdom */

import { render, waitFor } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WEB_VITALS_ENDPOINT } from "@/lib/telemetry/web-vitals";
import { server } from "@/test/msw/server";

type CapturedMetric = {
  delta: number;
  name: "LCP";
  navigationType: "navigate";
  rating: "good";
  value: number;
};

let capturedHandler: ((metric: CapturedMetric) => void) | undefined;
const BASE_METRIC: CapturedMetric = {
  delta: 15,
  name: "LCP",
  navigationType: "navigate",
  rating: "good",
  value: 1800,
};

vi.mock("next/web-vitals", () => ({
  useReportWebVitals: vi.fn((handler: (metric: CapturedMetric) => void) => {
    capturedHandler = handler;
  }),
}));

function StubSendBeacon(result: boolean) {
  const sendBeacon = vi.fn<(url: string, data?: BodyInit | null) => boolean>(
    () => result
  );
  vi.stubGlobal("navigator", {
    ...navigator,
    sendBeacon,
  });

  return sendBeacon;
}

async function RenderReporter() {
  const { WebVitalsReporter } = await import("../web-vitals-reporter");
  render(<WebVitalsReporter />);
}

function ReportMetric(metric: Partial<CapturedMetric> = {}) {
  capturedHandler?.({ ...BASE_METRIC, ...metric });
}

describe("WebVitalsReporter", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
    capturedHandler = undefined;
    window.history.replaceState(null, "", "/dashboard/trips/123");
  });

  it("reports sanitized Web Vitals with sendBeacon", async () => {
    const sendBeacon = StubSendBeacon(true);

    await RenderReporter();
    ReportMetric();

    expect(sendBeacon).toHaveBeenCalledWith(WEB_VITALS_ENDPOINT, expect.any(Blob));
    const beaconBody = sendBeacon.mock.calls.at(0)?.[1];
    if (!(beaconBody instanceof Blob)) {
      throw new Error("Expected Web Vitals payload to be sent as a Blob");
    }
    const body = await beaconBody.text();
    expect(JSON.parse(body)).toEqual({
      delta: 15,
      name: "LCP",
      navigationType: "navigate",
      rating: "good",
      route: "/dashboard/trips/:id",
      value: 1800,
    });
  });

  it("falls back to keepalive fetch when sendBeacon declines the payload", async () => {
    StubSendBeacon(false);
    let fallbackRequestBody: unknown;
    let fallbackContentType: string | null = null;
    server.use(
      http.post(WEB_VITALS_ENDPOINT, async ({ request }) => {
        fallbackContentType = request.headers.get("content-type");
        fallbackRequestBody = await request.json();
        return new HttpResponse(null, { status: 204 });
      })
    );

    await RenderReporter();
    ReportMetric();

    await waitFor(() => {
      expect(fallbackContentType).toBe("application/json");
      expect(fallbackRequestBody).toEqual({
        delta: 15,
        name: "LCP",
        navigationType: "navigate",
        rating: "good",
        route: "/dashboard/trips/:id",
        value: 1800,
      });
    });
  });
});
