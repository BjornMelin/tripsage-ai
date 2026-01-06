/** @vitest-environment jsdom */

import { delay, HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";
import { CalendarEventList } from "@/components/calendar/calendar-event-list";
import { server } from "@/test/msw/server";
import { render, screen, within } from "@/test/test-utils";

const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL || "http://localhost:3000";

vi.mock("@/hooks/use-current-user-id", () => ({
  useCurrentUserId: () => "user-123",
}));

describe("CalendarEventList", () => {
  const useEventsHandlers = (handler: Parameters<typeof http.get>[1]) => {
    server.use(
      http.get(`${BASE_URL}/api/calendar/events`, handler),
      http.get("/api/calendar/events", handler)
    );
  };

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

    useEventsHandlers(handler);

    render(<CalendarEventList />);

    expect(await screen.findByText(/failed to load events/i)).toBeInTheDocument();
    expect(screen.getByText(/invalid calendar events response/i)).toBeInTheDocument();
  });

  it('shows "No events found in this time range" for empty items', async () => {
    useEventsHandlers(() => HttpResponse.json({ items: [] }));

    render(<CalendarEventList />);

    expect(
      await screen.findByText("No events found in this time range.")
    ).toBeInTheDocument();
  });

  it("shows generic error UI when API returns non-200", async () => {
    useEventsHandlers(() => new HttpResponse(null, { status: 500 }));

    render(<CalendarEventList />);

    expect(await screen.findByText(/failed to load events:/i)).toBeInTheDocument();
    expect(screen.getByText(/failed to fetch events/i)).toBeInTheDocument();
  });

  it("renders date-only events as all-day", async () => {
    useEventsHandlers(() =>
      HttpResponse.json({
        items: [
          {
            end: { date: "2025-12-13" },
            id: "event-all-day",
            start: { date: "2025-12-12" },
            summary: "All Day Event",
          },
        ],
      })
    );

    render(<CalendarEventList />);

    const title = await screen.findByText("All Day Event");
    const listItem = title.closest("li");
    expect(listItem).not.toBeNull();
    expect(within(listItem as HTMLElement).getByText(/- all day/i)).toBeInTheDocument();
  });

  it("renders events with missing optional fields without broken links", async () => {
    useEventsHandlers(() =>
      HttpResponse.json({
        items: [
          {
            end: { dateTime: "2025-12-12T11:00:00.000Z" },
            id: "event-missing-optional-fields",
            start: { dateTime: "2025-12-12T10:00:00.000Z" },
            summary: "Minimal Event",
          },
        ],
      })
    );

    render(<CalendarEventList />);

    expect(await screen.findByText("Minimal Event")).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: /view in google calendar/i })
    ).not.toBeInTheDocument();
  });

  it("shows loading skeletons while request is pending", async () => {
    useEventsHandlers(async () => {
      await delay(100);
      return HttpResponse.json({
        items: [
          {
            end: { dateTime: "2025-12-12T11:00:00.000Z" },
            id: "event-slow",
            start: { dateTime: "2025-12-12T10:00:00.000Z" },
            summary: "Slow Event",
          },
        ],
      });
    });

    render(<CalendarEventList />);

    expect(
      screen.getAllByRole("status", { name: /loading content/i }).length
    ).toBeGreaterThan(0);
    expect(await screen.findByText("Slow Event")).toBeInTheDocument();
  });

  it("refetches when query props change and updates rendered events", async () => {
    let requestCount = 0;

    const handler = ({ request }: { request: Request }) => {
      requestCount += 1;
      const url = new URL(request.url);
      const calendarId = url.searchParams.get("calendarId");

      if (calendarId === "secondary") {
        return HttpResponse.json({
          items: [
            {
              end: { dateTime: "2025-12-12T13:00:00.000Z" },
              id: "event-secondary",
              start: { dateTime: "2025-12-12T12:00:00.000Z" },
              summary: "Secondary Event",
            },
          ],
        });
      }

      return HttpResponse.json({
        items: [
          {
            end: { dateTime: "2025-12-12T11:00:00.000Z" },
            id: "event-primary",
            start: { dateTime: "2025-12-12T10:00:00.000Z" },
            summary: "Primary Event",
          },
        ],
      });
    };

    useEventsHandlers(handler);

    const { rerender } = render(<CalendarEventList calendarId="primary" />);

    expect(await screen.findByText("Primary Event")).toBeInTheDocument();

    rerender(<CalendarEventList calendarId="secondary" />);

    expect(await screen.findByText("Secondary Event")).toBeInTheDocument();
    expect(screen.queryByText("Primary Event")).not.toBeInTheDocument();
    expect(requestCount).toBeGreaterThanOrEqual(2);
  });
});
