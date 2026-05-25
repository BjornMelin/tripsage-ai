/** @vitest-environment jsdom */

import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DateUtils } from "@/lib/dates/unified-date-utils";

const calendarEventListSpy = vi.hoisted(() => vi.fn());
const refreshSpy = vi.hoisted(() => vi.fn());
const toastSpy = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    refresh: refreshSpy,
  }),
}));

vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({ toast: toastSpy }),
}));

vi.mock("@/lib/security/random", () => ({
  nowIso: vi.fn(() => "2026-01-15T12:34:56.000Z"),
}));

vi.mock("@/components/calendar/calendar-connection-card", () => ({
  CalendarConnectionCard: () => <div data-testid="calendar-connection-card" />,
}));

vi.mock("@/components/calendar/calendar-event-form", () => ({
  CalendarEventForm: () => <div data-testid="calendar-event-form" />,
}));

vi.mock("@/components/calendar/calendar-event-list", () => ({
  CalendarEventList: (props: { timeMax?: Date; timeMin?: Date }) => {
    calendarEventListSpy(props);
    return <div data-testid="calendar-event-list" />;
  },
}));

vi.mock("@/components/ui/tabs", () => ({
  Tabs: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TabsContent: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TabsList: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TabsTrigger: ({ children }: { children: ReactNode }) => (
    <button type="button">{children}</button>
  ),
}));

import CalendarPage from "../page";

describe("CalendarPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("passes a centralized-clock event window to the event list", () => {
    const expectedStart = DateUtils.startOf(
      new Date("2026-01-15T12:34:56.000Z"),
      "day"
    );

    render(<CalendarPage />);

    expect(calendarEventListSpy).toHaveBeenCalledWith({
      timeMax: DateUtils.add(expectedStart, 7, "days"),
      timeMin: expectedStart,
    });
  });
});
