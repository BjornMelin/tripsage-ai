/** @vitest-environment jsdom */

import { describe, expect, it, vi } from "vitest";
import { CalendarEventForm } from "@/components/calendar/calendar-event-form";
import { render, screen } from "@/test/test-utils";
import { withFakeTimers } from "@/test/utils/with-fake-timers";

describe("CalendarEventForm", () => {
  it(
    "renders default start and end datetime values",
    withFakeTimers(() => {
      vi.setSystemTime(new Date("2026-03-04T05:06:07.000Z"));

      render(<CalendarEventForm />);

      expect(screen.getByLabelText("Start")).toHaveValue("2026-03-04T05:06");
      expect(screen.getByLabelText("End")).toHaveValue("2026-03-04T06:06");
    })
  );

  it("preserves initial event datetime values", () => {
    render(
      <CalendarEventForm
        initialData={{
          end: { dateTime: new Date("2026-04-01T13:30:00.000Z") },
          start: { dateTime: new Date("2026-04-01T12:30:00.000Z") },
          summary: "Existing event",
        }}
      />
    );

    expect(screen.getByLabelText("Title")).toHaveValue("Existing event");
    expect(screen.getByLabelText("Start")).toHaveValue("2026-04-01T12:30");
    expect(screen.getByLabelText("End")).toHaveValue("2026-04-01T13:30");
  });
});
