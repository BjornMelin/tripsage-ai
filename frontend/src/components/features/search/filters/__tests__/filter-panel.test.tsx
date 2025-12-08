/** @vitest-environment jsdom */

import { fireEvent, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useSearchFiltersStore } from "@/stores/search-filters-store";
import { render as renderWithProviders } from "@/test/test-utils";
import { FilterPanel } from "../filter-panel";

const ResetStore = () => {
  useSearchFiltersStore.getState().reset();
};

describe("FilterPanel", () => {
  beforeEach(() => {
    ResetStore();
    useSearchFiltersStore.getState().setSearchType("flight");
  });

  afterEach(() => {
    ResetStore();
  });

  it("renders active price range badge with formatted values", () => {
    useSearchFiltersStore
      .getState()
      .setActiveFilter("price_range", { max: 200, min: 100 });

    renderWithProviders(<FilterPanel />);

    const badge = screen.getByTestId("active-filter-badge-price_range");
    expect(badge).toBeInTheDocument();
    expect(badge.textContent).toContain("Price Range: $100-$200");
  });

  it("clears active filters when Clear All is clicked", () => {
    useSearchFiltersStore
      .getState()
      .setActiveFilter("price_range", { max: 150, min: 50 });

    renderWithProviders(<FilterPanel />);

    fireEvent.click(screen.getByRole("button", { name: /clear all/i }));

    expect(Object.keys(useSearchFiltersStore.getState().activeFilters)).toHaveLength(0);
  });
});
