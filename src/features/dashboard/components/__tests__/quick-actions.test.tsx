/** @vitest-environment jsdom */

import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/test-utils";
import { QuickActions, QuickActionsCompact, QuickActionsList } from "../quick-actions";

// Mock Next.js Link component
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

describe("QuickActions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the component title and description", () => {
    renderWithProviders(<QuickActions />);

    expect(screen.getByText("Quick Actions")).toBeInTheDocument();
    expect(
      screen.getByText("Common tasks and shortcuts to help you get started")
    ).toBeInTheDocument();
  });

  it("renders all quick action buttons by default", () => {
    renderWithProviders(<QuickActions />);

    expect(screen.getByText("Search Flights")).toBeInTheDocument();
    expect(screen.getByText("Find Hotels")).toBeInTheDocument();
    expect(screen.getByText("Plan New Trip")).toBeInTheDocument();
    expect(screen.getByText("Ask AI Assistant")).toBeInTheDocument();
    expect(screen.getByText("Explore Destinations")).toBeInTheDocument();
    expect(screen.getByText("My Trips")).toBeInTheDocument();
    expect(screen.getByText("Detailed Search")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("displays action descriptions in the default variant", () => {
    renderWithProviders(<QuickActions />);

    expect(
      screen.getByText("Find the best flight deals for your next trip")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Discover comfortable accommodations worldwide")
    ).toBeInTheDocument();
  });

  it("links to correct URLs", () => {
    renderWithProviders(<QuickActions />);

    const searchFlightsLink = screen.getByRole("link", {
      name: /Search Flights/i,
    });
    expect(searchFlightsLink).toHaveAttribute("href", "/dashboard/search/flights");

    const findHotelsLink = screen.getByRole("link", { name: /Find Hotels/i });
    expect(findHotelsLink).toHaveAttribute("href", "/dashboard/search/hotels");

    const planTripLink = screen.getByRole("link", { name: /Plan New Trip/i });
    expect(planTripLink).toHaveAttribute("href", "/dashboard/trips/create");

    const chatLink = screen.getByRole("link", { name: /Ask AI Assistant/i });
    expect(chatLink).toHaveAttribute("href", "/chat");

    const exploreLink = screen.getByRole("link", {
      name: /Explore Destinations/i,
    });
    expect(exploreLink).toHaveAttribute("href", "/dashboard/search/destinations");

    const tripsLink = screen.getByRole("link", { name: /My Trips/i });
    expect(tripsLink).toHaveAttribute("href", "/dashboard/trips");

    const advancedSearchLink = screen.getByRole("link", {
      name: /Detailed Search/i,
    });
    expect(advancedSearchLink).toHaveAttribute("href", "/dashboard/search");

    const settingsLink = screen.getByRole("link", { name: /Settings/i });
    expect(settingsLink).toHaveAttribute("href", "/dashboard/settings");
  });

  it("displays AI badge on AI Assistant action", () => {
    renderWithProviders(<QuickActions />);

    expect(screen.getByText("AI")).toBeInTheDocument();
  });

  it("renders in grid layout by default", () => {
    renderWithProviders(<QuickActions />);

    // Grid layout should have grid CSS classes
    const gridContainer = document.querySelector(".grid");
    expect(gridContainer).toBeInTheDocument();
  });

  it("displays icons for all actions", () => {
    renderWithProviders(<QuickActions />);

    // Check that SVG icons are present
    const icons = document.querySelectorAll("svg");
    expect(icons.length).toBeGreaterThan(0);
  });

  it("applies custom colors to action buttons", () => {
    renderWithProviders(<QuickActions />);

    // Check that custom color classes are applied
    const infoButton = document.querySelector(".bg-info/10");
    const successButton = document.querySelector(".bg-success/10");
    const highlightButton = document.querySelector(".bg-highlight/10");
    const warningButton = document.querySelector(".bg-warning/10");

    expect(infoButton).toBeInTheDocument();
    expect(successButton).toBeInTheDocument();
    expect(highlightButton).toBeInTheDocument();
    expect(warningButton).toBeInTheDocument();
  });
});

describe("QuickActionsCompact", () => {
  it("renders in compact mode", () => {
    renderWithProviders(<QuickActionsCompact />);

    expect(screen.getByText("Quick Actions")).toBeInTheDocument();

    // Should show fewer actions
    const actionButtons = screen.getAllByRole("link");
    expect(actionButtons.length).toBe(6);
  });

  it("hides descriptions", () => {
    renderWithProviders(<QuickActionsCompact />);

    expect(
      screen.queryByText("Find the best flight deals for your next trip")
    ).not.toBeInTheDocument();
  });

  it("adjusts title size", () => {
    renderWithProviders(<QuickActionsCompact />);

    const title = screen.getByText("Quick Actions");
    expect(title).toHaveClass("text-lg");
  });

  it("uses grid layout", () => {
    renderWithProviders(<QuickActionsCompact />);

    const gridContainer = document.querySelector(".grid");
    expect(gridContainer).toBeInTheDocument();
  });
});

describe("QuickActionsList", () => {
  it("renders in list layout", () => {
    renderWithProviders(<QuickActionsList />);

    const listContainer = document.querySelector(".space-y-2");
    expect(listContainer).toBeInTheDocument();
  });

  it("shows descriptions", () => {
    renderWithProviders(<QuickActionsList />);

    expect(
      screen.getByText("Find the best flight deals for your next trip")
    ).toBeInTheDocument();
  });

  it("is not in compact mode", () => {
    renderWithProviders(<QuickActionsList />);

    // Should show all actions
    const actionButtons = screen.getAllByRole("link");
    expect(actionButtons.length).toBe(8);
  });

  it("displays action titles and descriptions in list format", () => {
    renderWithProviders(<QuickActionsList />);

    // Check that buttons have justify-start class for left alignment
    const buttons = document.querySelectorAll(".justify-start");
    expect(buttons.length).toBeGreaterThan(0);
  });
});

describe("QuickActions Accessibility", () => {
  it("has proper button roles", () => {
    renderWithProviders(<QuickActions />);

    const buttons = screen.getAllByRole("link");
    expect(buttons.length).toBeGreaterThan(0);
  });

  it("has accessible link text", () => {
    renderWithProviders(<QuickActions />);

    const searchFlightsLink = screen.getByRole("link", {
      name: /Search Flights/i,
    });
    expect(searchFlightsLink).toBeInTheDocument();
  });

  it("maintains focus styles", () => {
    renderWithProviders(<QuickActions />);

    // Check that interactive links include focus-visible ring classes
    const links = Array.from(document.querySelectorAll<HTMLAnchorElement>("a[href]"));
    expect(links.length).toBeGreaterThan(0);
    const hasFocusStyle = links.some(
      (el) =>
        el.className.includes("focus-visible:ring") ||
        el.className.includes("focus-visible:border-ring")
    );
    expect(hasFocusStyle).toBe(true);
  });
});

describe("QuickActions Edge Cases", () => {
  it("handles missing icons gracefully", () => {
    renderWithProviders(<QuickActions />);

    // Component should render without errors even if icons fail to load
    expect(screen.getByText("Quick Actions")).toBeInTheDocument();
  });

  it("handles very small limits correctly", () => {
    renderWithProviders(<QuickActionsCompact />);

    // Even with compact mode, should show at least some actions
    const actionButtons = screen.getAllByRole("link");
    expect(actionButtons.length).toBeGreaterThan(0);
  });

  it("maintains responsive grid classes", () => {
    renderWithProviders(<QuickActions />);

    // Check for responsive grid classes
    const gridContainer = document.querySelector(".grid");
    expect(gridContainer).toHaveClass("grid-cols-1");
  });
});
