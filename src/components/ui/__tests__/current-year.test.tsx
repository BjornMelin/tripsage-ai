/** @vitest-environment jsdom */

import { describe, expect, it, vi } from "vitest";
import { renderWithProviders, screen } from "@/test/test-utils";
import { withFakeTimers } from "@/test/utils/with-fake-timers";
import { CurrentYear } from "../current-year";

describe("CurrentYear", () => {
  it(
    "renders the current year from the canonical clock helper",
    withFakeTimers(() => {
      vi.setSystemTime(new Date("2026-02-03T04:05:06.000Z"));

      renderWithProviders(<CurrentYear />);

      expect(screen.getByText("2026")).toBeInTheDocument();
    })
  );
});
