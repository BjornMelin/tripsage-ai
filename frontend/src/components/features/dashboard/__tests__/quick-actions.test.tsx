import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render } from "@/test/test-utils.test";
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
    render(<QuickActions />);

    expect(screen.getByText("Quick Actions")).toBeInTheDocument();
    expect(
      screen.getByText("Common tasks and shortcuts to help you get started")
    ).toBeInTheDocument();
  });

  it("renders all quick action buttons by default", () => {
    render(<QuickActions />);

    expect(screen.getByText("Search Flights")).toBeInTheDocument();
    expect(screen.getByText("Find Hotels")).toBeInTheDocument();
    expect(screen.getByText("Plan New Trip")).toBeInTheDocument();
    expect(screen.getByText("Ask AI Assistant")).toBeInTheDocument();
    expect(screen.getByText("Explore Destinations")).toBeInTheDocument();
    expect(screen.getByText("My Trips")).toBeInTheDocument();
    expect(screen.getByText("Detailed Search")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
  });

  it("displays action descriptions when showDescription is true", () => {
    render(<QuickActions showDescription={true} />);

    expect(
      screen.getByText("Find the best flight deals for your next trip")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Discover comfortable accommodations worldwide")
    ).toBeInTheDocument();
    expect(screen.getByText("Start planning your next adventure")).toBeInTheDocument();
    expect(
      screen.getByText("Get personalized travel recommendations")
    ).toBeInTheDocument();
  });

  it("hides action descriptions when showDescription is false", () => {
    render(<QuickActions showDescription={false} />);

    expect(
      screen.queryByText("Find the best flight deals for your next trip")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Discover comfortable accommodations worldwide")
    ).not.toBeInTheDocument();
  });

  it("links to correct URLs", () => {
    render(<QuickActions />);

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
    render(<QuickActions />);

    expect(screen.getByText("AI")).toBeInTheDocument();
  });

  it("renders in grid layout by default", () => {
    render(<QuickActions />);

    // Grid layout should have grid CSS classes
    const gridContainer = document.querySelector(".grid");
    expect(gridContainer).toBeInTheDocument();
  });

  it("renders in list layout when specified", () => {
    render(<QuickActions layout="list" />);

    // List layout should have space-y classes instead of grid
    const listContainer = document.querySelector(".space-y-2");
    expect(listContainer).toBeInTheDocument();
  });

  it("shows fewer actions when compact mode is enabled", () => {
    render(<QuickActions compact={true} />);

    // Should show only 6 actions in compact mode
    const actionButtons = screen.getAllByRole("link");
    expect(actionButtons.length).toBe(6);
  });

  it("shows all actions when compact mode is disabled", () => {
    render(<QuickActions compact={false} />);

    // Should show all 8 actions
    const actionButtons = screen.getAllByRole("link");
    expect(actionButtons.length).toBe(8);
  });

  it("hides description in compact mode even when showDescription is true", () => {
    render(<QuickActions compact={true} showDescription={true} />);

    expect(
      screen.queryByText("Find the best flight deals for your next trip")
    ).not.toBeInTheDocument();
  });

  it("adjusts title size in compact mode", () => {
    render(<QuickActions compact={true} />);

    // In compact mode, title should have text-lg class
    const title = screen.getByText("Quick Actions");
    expect(title).toHaveClass("text-lg");
  });

  it("displays icons for all actions", () => {
    render(<QuickActions />);

    // Check that SVG icons are present
    const icons = document.querySelectorAll("svg");
    expect(icons.length).toBeGreaterThan(0);
  });

  it("applies custom colors to action buttons", () => {
    render(<QuickActions />);

    // Check that custom color classes are applied
    const blueButton = document.querySelector(".bg-blue-50");
    const greenButton = document.querySelector(".bg-green-50");
    const purpleButton = document.querySelector(".bg-purple-50");
    const orangeButton = document.querySelector(".bg-orange-50");

    expect(blueButton).toBeInTheDocument();
    expect(greenButton).toBeInTheDocument();
    expect(purpleButton).toBeInTheDocument();
    expect(orangeButton).toBeInTheDocument();
  });
});

describe("QuickActionsCompact", () => {
  it("renders in compact mode", () => {
    render(<QuickActionsCompact />);

    expect(screen.getByText("Quick Actions")).toBeInTheDocument();

    // Should show fewer actions
    const actionButtons = screen.getAllByRole("link");
    expect(actionButtons.length).toBe(6);
  });

  it("hides descriptions", () => {
    render(<QuickActionsCompact />);

    expect(
      screen.queryByText("Find the best flight deals for your next trip")
    ).not.toBeInTheDocument();
  });

  it("uses grid layout", () => {
    render(<QuickActionsCompact />);

    const gridContainer = document.querySelector(".grid");
    expect(gridContainer).toBeInTheDocument();
  });
});

describe("QuickActionsList", () => {
  it("renders in list layout", () => {
    render(<QuickActionsList />);

    const listContainer = document.querySelector(".space-y-2");
    expect(listContainer).toBeInTheDocument();
  });

  it("shows descriptions", () => {
    render(<QuickActionsList />);

    expect(
      screen.getByText("Find the best flight deals for your next trip")
    ).toBeInTheDocument();
  });

  it("is not in compact mode", () => {
    render(<QuickActionsList />);

    // Should show all actions
    const actionButtons = screen.getAllByRole("link");
    expect(actionButtons.length).toBe(8);
  });

  it("displays action titles and descriptions in list format", () => {
    render(<QuickActionsList />);

    // Check that buttons have justify-start class for left alignment
    const buttons = document.querySelectorAll(".justify-start");
    expect(buttons.length).toBeGreaterThan(0);
  });
});

describe("QuickActions Accessibility", () => {
  it("has proper button roles", () => {
    render(<QuickActions />);

    const buttons = screen.getAllByRole("link");
    expect(buttons.length).toBeGreaterThan(0);
  });

  it("has accessible link text", () => {
    render(<QuickActions />);

    const searchFlightsLink = screen.getByRole("link", {
      name: /Search Flights/i,
    });
    expect(searchFlightsLink).toBeInTheDocument();
  });

  it("maintains focus styles", () => {
    render(<QuickActions />);

    // Check that interactive links include focus-visible ring classes
    const links = Array.from(document.querySelectorAll<HTMLAnchorElement>("a[href]"));
    expect(links.length).toBeGreaterThan(0);
    const hasFocusRing = links.some(
      (el) =>
        el.className.includes("focus-visible:ring-2") &&
        el.className.includes("focus-visible:ring-offset-2")
    );
    expect(hasFocusRing).toBe(true);
  });
});

describe("QuickActions Edge Cases", () => {
  it("handles missing icons gracefully", () => {
    render(<QuickActions />);

    // Component should render without errors even if icons fail to load
    expect(screen.getByText("Quick Actions")).toBeInTheDocument();
  });

  it("handles very small limits correctly", () => {
    render(<QuickActions compact={true} />);

    // Even with compact mode, should show at least some actions
    const actionButtons = screen.getAllByRole("link");
    expect(actionButtons.length).toBeGreaterThan(0);
  });

  it("maintains responsive grid classes", () => {
    render(<QuickActions />);

    // Check for responsive grid classes
    const gridContainer = document.querySelector(".grid");
    expect(gridContainer).toHaveClass("grid-cols-1");
  });
});
