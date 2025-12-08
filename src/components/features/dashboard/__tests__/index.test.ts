/**
 * @vitest-environment node
 *
 * Node environment is safe here because this test only verifies module exports.
 * All child components are mocked to return null, so no DOM APIs are invoked.
 * This significantly improves test performance compared to jsdom (~50ms vs ~2000ms).
 */

import { describe, expect, it, vi } from "vitest";

// Mock child components before importing - prevents DOM API access
vi.mock("../recent-trips", () => ({ RecentTrips: () => null }));
vi.mock("../upcoming-flights", () => ({ UpcomingFlights: () => null }));
vi.mock("../trip-suggestions", () => ({ TripSuggestions: () => null }));
vi.mock("../quick-actions", () => ({
  QuickActions: () => null,
  QuickActionsCompact: () => null,
  QuickActionsList: () => null,
}));

// Static import after mocks - single module load
import * as dashboardModule from "../index";

describe("Dashboard Components Exports", () => {
  it("should export all dashboard components", () => {
    expect(dashboardModule.RecentTrips).toBeDefined();
    expect(dashboardModule.UpcomingFlights).toBeDefined();
    expect(dashboardModule.TripSuggestions).toBeDefined();
    expect(dashboardModule.QuickActions).toBeDefined();
    expect(dashboardModule.QuickActionsCompact).toBeDefined();
    expect(dashboardModule.QuickActionsList).toBeDefined();
  });

  it("should have proper component types", () => {
    expect(typeof dashboardModule.RecentTrips).toBe("function");
    expect(typeof dashboardModule.UpcomingFlights).toBe("function");
    expect(typeof dashboardModule.TripSuggestions).toBe("function");
    expect(typeof dashboardModule.QuickActions).toBe("function");
    expect(typeof dashboardModule.QuickActionsCompact).toBe("function");
    expect(typeof dashboardModule.QuickActionsList).toBe("function");
  });
});
