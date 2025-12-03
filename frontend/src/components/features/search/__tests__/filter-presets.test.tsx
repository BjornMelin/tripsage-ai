/** @vitest-environment jsdom */

import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { useSearchFiltersStore } from "@/stores/search-filters-store";
import { render as renderWithProviders } from "@/test/test-utils";
import { FilterPresets } from "../filter-presets";

const ResetStore = () => useSearchFiltersStore.getState().reset();

describe("FilterPresets", () => {
  beforeEach(() => {
    ResetStore();
    useSearchFiltersStore.getState().setSearchType("flight");
  });

  afterEach(() => {
    ResetStore();
  });

  it("enables Save when filters are active and creates a preset", async () => {
    useSearchFiltersStore
      .getState()
      .setActiveFilter("price_range", { max: 400, min: 100 });
    renderWithProviders(<FilterPresets />);

    const saveButton = screen.getByRole("button", { name: /save/i });
    expect(saveButton).toBeEnabled();

    await userEvent.click(saveButton);
    const nameInput = await screen.findByLabelText(/name/i);
    await userEvent.type(nameInput, "My preset");
    await userEvent.click(screen.getByRole("button", { name: /save preset/i }));

    expect(
      useSearchFiltersStore
        .getState()
        .filterPresets.some((preset) => preset.name === "My preset")
    ).toBe(true);
  });
});
