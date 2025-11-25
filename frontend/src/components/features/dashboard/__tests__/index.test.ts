/** @vitest-environment jsdom */

import { describe, expect, it } from "vitest";

describe("Dashboard Components Exports", () => {
  it("should export all dashboard components", async () => {
    const dashboardModule = await import("../index");

    expect(dashboardModule.RecentTrips).toBeDefined();
    expect(dashboardModule.UpcomingFlights).toBeDefined();
    expect(dashboardModule.TripSuggestions).toBeDefined();
    expect(dashboardModule.QuickActions).toBeDefined();
    expect(dashboardModule.QuickActionsCompact).toBeDefined();
    expect(dashboardModule.QuickActionsList).toBeDefined();
  });

  it("should have proper component types", async () => {
    const dashboardModule = await import("../index");

    expect(typeof dashboardModule.RecentTrips).toBe("function");
    expect(typeof dashboardModule.UpcomingFlights).toBe("function");
    expect(typeof dashboardModule.TripSuggestions).toBe("function");
    expect(typeof dashboardModule.QuickActions).toBe("function");
    expect(typeof dashboardModule.QuickActionsCompact).toBe("function");
    expect(typeof dashboardModule.QuickActionsList).toBe("function");
  });
});
