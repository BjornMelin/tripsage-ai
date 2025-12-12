/** @vitest-environment jsdom */

import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";
import { CalendarEventList } from "@/components/calendar/calendar-event-list";
import { server } from "@/test/msw/server";
import { render, screen } from "@/test/test-utils";

const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000";

describe("CalendarEventList", () => {
  it("renders events returned by API", async () => {
    const handler = () =>
      HttpResponse.json({
        items: [
          {
            end: { dateTime: "2025-12-12T11:00:00.000Z" },
            htmlLink: "https://calendar.google.com/calendar/event?eid=test",
            id: "event-1",
            start: { dateTime: "2025-12-12T10:00:00.000Z" },
            summary: "Test Event",
          },
        ],
      });

    server.use(
      http.get(`${BASE_URL}/api/calendar/events`, handler),
      http.get("/api/calendar/events", handler)
    );

    render(<CalendarEventList />);

    expect(await screen.findByText("Test Event")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /view in google calendar/i })
    ).toHaveAttribute("href", "https://calendar.google.com/calendar/event?eid=test");
  });

  it("shows error state when API response is invalid", async () => {
    const handler = () =>
      HttpResponse.json({
        items: [{}],
      });

    server.use(
      http.get(`${BASE_URL}/api/calendar/events`, handler),
      http.get("/api/calendar/events", handler)
    );

    render(<CalendarEventList />);

    expect(await screen.findByText(/failed to load events/i)).toBeInTheDocument();
    expect(screen.getByText(/invalid calendar events response/i)).toBeInTheDocument();
  });
});
