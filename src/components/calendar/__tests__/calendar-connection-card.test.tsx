/** @vitest-environment jsdom */

import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CalendarConnectionCard } from "@/components/calendar/calendar-connection-card";
import { server } from "@/test/msw/server";
import { render, screen } from "@/test/test-utils";

const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000";

const { mockRecordClientErrorOnActiveSpan } = vi.hoisted(() => ({
  mockRecordClientErrorOnActiveSpan: vi.fn(),
}));

vi.mock("@/lib/telemetry/client-errors", () => ({
  recordClientErrorOnActiveSpan: mockRecordClientErrorOnActiveSpan,
}));

describe("CalendarConnectionCard", () => {
  const useCalendarStatusHandlers = (handler: Parameters<typeof http.get>[1]) => {
    server.use(
      http.get(`${BASE_URL}/api/calendar/status`, handler),
      http.get("/api/calendar/status", handler)
    );
  };

  beforeEach(() => {
    mockRecordClientErrorOnActiveSpan.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows load errors and records them through telemetry", async () => {
    useCalendarStatusHandlers(() =>
      HttpResponse.json({ error: "calendar status unavailable" }, { status: 503 })
    );

    render(<CalendarConnectionCard />);

    expect(
      await screen.findByText("Failed to load calendar status")
    ).toBeInTheDocument();
    expect(screen.getByText("calendar status unavailable")).toBeInTheDocument();
    expect(mockRecordClientErrorOnActiveSpan).toHaveBeenCalledWith(
      expect.objectContaining({ message: "calendar status unavailable" }),
      {
        action: "loadCalendarStatus",
        context: "CalendarConnectionCard",
      }
    );
  });

  it("keeps the error UI visible when telemetry recording fails", async () => {
    useCalendarStatusHandlers(() =>
      HttpResponse.json({ error: "calendar status unavailable" }, { status: 503 })
    );
    mockRecordClientErrorOnActiveSpan.mockImplementationOnce(() => {
      throw new Error("telemetry unavailable");
    });

    render(<CalendarConnectionCard />);

    expect(
      await screen.findByText("Failed to load calendar status")
    ).toBeInTheDocument();
    expect(screen.getByText("calendar status unavailable")).toBeInTheDocument();
    expect(mockRecordClientErrorOnActiveSpan).toHaveBeenCalledWith(
      expect.objectContaining({ message: "calendar status unavailable" }),
      {
        action: "loadCalendarStatus",
        context: "CalendarConnectionCard",
      }
    );
  });
});
