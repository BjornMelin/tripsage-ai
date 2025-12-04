/** @vitest-environment jsdom */

import type { Activity } from "@schemas/search";
import { fireEvent, screen } from "@testing-library/react";
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
});
