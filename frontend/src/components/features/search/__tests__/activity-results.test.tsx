/** @vitest-environment jsdom */

import type { Activity } from "@schemas/search";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { render } from "@/test/test-utils";
import { ActivityResults } from "../activity-results";

const BaseActivity: Activity = {
  coordinates: { lat: 0, lng: 0 },
  date: "2025-01-01",
  description: "Test activity",
  duration: 120,
  id: "activity-1",
  images: [],
  location: "Testville",
  name: "City Tour",
  price: 50,
  rating: 4.5,
  type: "tour",
};

describe("ActivityResults", () => {
  it("renders activity details when results are provided", () => {
    render(
      <ActivityResults
        results={[BaseActivity]}
        onSelect={vi.fn().mockResolvedValue(undefined)}
      />
    );

    expect(screen.getByText("City Tour")).toBeInTheDocument();
    expect(screen.getByText("Test activity")).toBeInTheDocument();
    expect(screen.getByText("Testville")).toBeInTheDocument();
  });

  it("calls onSelect when an activity is clicked", () => {
    const onSelect = vi.fn().mockResolvedValue(undefined);

    render(<ActivityResults results={[BaseActivity]} onSelect={onSelect} />);

    fireEvent.click(screen.getByRole("button", { name: /select/i }));

    expect(onSelect).toHaveBeenCalledWith(BaseActivity);
  });

  it("renders multiple activities and selects the second", () => {
    const secondActivity: Activity = {
      ...BaseActivity,
      id: "activity-2",
      name: "Beach Day",
    };
    const onSelect = vi.fn().mockResolvedValue(undefined);

    render(
      <ActivityResults results={[BaseActivity, secondActivity]} onSelect={onSelect} />
    );

    expect(screen.getByText("City Tour")).toBeInTheDocument();
    expect(screen.getByText("Beach Day")).toBeInTheDocument();

    const selectButtons = screen.getAllByRole("button", { name: /select/i });
    fireEvent.click(selectButtons[1]);

    expect(onSelect).toHaveBeenCalledWith(secondActivity);
  });

  it("shows empty state when there are no results", () => {
    render(
      <ActivityResults results={[]} onSelect={vi.fn().mockResolvedValue(undefined)} />
    );

    expect(screen.getByText("No activities found")).toBeInTheDocument();
    expect(
      screen.getByText("Try adjusting your search criteria or dates")
    ).toBeInTheDocument();
  });

  it("calls onOpenFilters when Filters button is clicked", () => {
    const onOpenFilters = vi.fn();

    render(
      <ActivityResults
        results={[BaseActivity]}
        onSelect={vi.fn().mockResolvedValue(undefined)}
        onOpenFilters={onOpenFilters}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /open activity filters/i }));

    expect(onOpenFilters).toHaveBeenCalledTimes(1);
  });

  it("reorders activities when sort controls change", () => {
    const highRatedHighPrice: Activity = {
      ...BaseActivity,
      id: "activity-2",
      name: "Luxury Tour",
      price: 300,
      rating: 5,
    };
    const lowPriceLowRating: Activity = {
      ...BaseActivity,
      id: "activity-3",
      name: "Budget Walk",
      price: 20,
      rating: 3,
    };

    render(
      <ActivityResults
        results={[highRatedHighPrice, lowPriceLowRating]}
        onSelect={vi.fn().mockResolvedValue(undefined)}
      />
    );

    const initialOrder = screen
      .getAllByRole("heading", { level: 3 })
      .map((heading) => heading.textContent);

    expect(initialOrder).toEqual(["Luxury Tour", "Budget Walk"]);

    fireEvent.click(screen.getByRole("button", { name: "Price" }));

    const priceSortedOrder = screen
      .getAllByRole("heading", { level: 3 })
      .map((heading) => heading.textContent);

    expect(priceSortedOrder).toEqual(["Budget Walk", "Luxury Tour"]);
  });

  it("toggles between grid and list view modes", () => {
    render(
      <ActivityResults
        results={[BaseActivity]}
        onSelect={vi.fn().mockResolvedValue(undefined)}
      />
    );

    const controls = screen.getByTestId("activity-results-controls");
    const layout = controls.nextElementSibling as HTMLElement;
    const listToggle = within(controls).getByRole("button", { name: /list view/i });
    const gridToggle = within(controls).getByRole("button", { name: /grid view/i });

    expect(layout.className).toContain("grid-cols-1");

    fireEvent.click(listToggle);
    expect(layout.className).toContain("space-y-4");

    fireEvent.click(gridToggle);
    expect(layout.className).toContain("grid-cols-1");
  });

  it("shows compare bar and handles compare and load more interactions", async () => {
    const firstActivity: Activity = { ...BaseActivity, id: "a1", name: "First" };
    const secondActivity: Activity = { ...BaseActivity, id: "a2", name: "Second" };
    const onCompare = vi.fn();
    const onLoadMore = vi.fn().mockResolvedValue(undefined);

    render(
      <ActivityResults
        results={[firstActivity, secondActivity]}
        onSelect={vi.fn().mockResolvedValue(undefined)}
        onCompare={onCompare}
        onLoadMore={onLoadMore}
        hasMore
      />
    );

    const compareButtons = screen.getAllByRole("button", { name: "Compare" });

    fireEvent.click(compareButtons[0]);
    expect(screen.getByText(/selected for comparison/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /compare \(1\)/i })).toBeDisabled();

    fireEvent.click(compareButtons[1]);
    const compareAction = screen.getByRole("button", { name: /compare \(2\)/i });
    expect(compareAction).not.toBeDisabled();

    fireEvent.click(compareAction);
    expect(onCompare).toHaveBeenCalledWith([firstActivity, secondActivity]);

    const loadMoreButton = screen.getByRole("button", {
      name: /load more activities/i,
    });
    fireEvent.click(loadMoreButton);

    await waitFor(() => expect(onLoadMore).toHaveBeenCalledTimes(1));
  });
});
