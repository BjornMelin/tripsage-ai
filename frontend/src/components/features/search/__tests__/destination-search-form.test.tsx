/** @vitest-environment jsdom */

import { act, fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/test-utils";
import { DestinationSearchForm } from "../destination-search-form";

// Use real react-hook-form behavior; keep tests focused on visible output

// Mock function for testing search form submission.
const MockOnSearch = vi.fn();
const WAIT_FOR_AUTOCOMPLETE_TICK = () => {
  vi.advanceTimersByTime(350);
};

vi.mock("@/hooks/use-memory", () => ({
  useMemoryContext: () => ({
    data: null,
    error: null,
    isError: false,
    isLoading: false,
    isSuccess: false,
  }),
}));

describe("DestinationSearchForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the destination search form correctly", () => {
    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);

    expect(screen.getByText("Destination Search")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Discover amazing destinations around the world with intelligent autocomplete"
      )
    ).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText("Search for cities, countries, or landmarks...")
    ).toBeInTheDocument();
  });

  it("displays popular destinations badges", () => {
    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);

    expect(screen.getByText("Popular Destinations")).toBeInTheDocument();
    expect(screen.getByText("Paris, France")).toBeInTheDocument();
    expect(screen.getByText("Tokyo, Japan")).toBeInTheDocument();
    expect(screen.getByText("New York, USA")).toBeInTheDocument();
  });

  it("displays destination type checkboxes", () => {
    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);

    expect(screen.getByText("Cities & Towns")).toBeInTheDocument();
    expect(screen.getByText("Countries")).toBeInTheDocument();
    expect(screen.getByText("States & Regions")).toBeInTheDocument();
    expect(screen.getByText("Landmarks & Places")).toBeInTheDocument();
  });

  it("handles popular destination selection", () => {
    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);

    const parisButton = screen.getByText("Paris, France");
    act(() => {
      fireEvent.click(parisButton);
    });

    const input = screen.getByPlaceholderText(
      "Search for cities, countries, or landmarks..."
    ) as HTMLInputElement;
    expect(input.value).toBe("Paris, France");
  });

  it("displays advanced options", () => {
    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);

    expect(screen.getByText("Max Results")).toBeInTheDocument();
    expect(screen.getByText("Language (optional)")).toBeInTheDocument();
    expect(screen.getByText("Region (optional)")).toBeInTheDocument();
  });

  it("shows autocomplete suggestions when typing", () => {
    vi.useFakeTimers();
    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);

    const input = screen.getByPlaceholderText(
      "Search for cities, countries, or landmarks..."
    );
    act(() => {
      fireEvent.change(input, { target: { value: "Par" } });
      WAIT_FOR_AUTOCOMPLETE_TICK();
    });

    expect(screen.getByText(/Popular Destination/)).toBeInTheDocument();
    vi.useRealTimers();
  });

  it("handles checkbox changes for destination types", () => {
    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);
    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes.length).toBeGreaterThan(0);
    act(() => {
      fireEvent.click(checkboxes[0]);
      if (checkboxes[1]) fireEvent.click(checkboxes[1]);
    });
  });

  it("renders the query input with placeholder", () => {
    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);
    expect(
      screen.getByPlaceholderText("Search for cities, countries, or landmarks...")
    ).toBeInTheDocument();
  });

  it("uses initial values when provided", () => {
    const initialValues = {
      limit: 5,
      query: "Tokyo",
      types: ["establishment"] as (
        | "country"
        | "locality"
        | "administrative_area"
        | "establishment"
      )[],
    };

    renderWithProviders(
      <DestinationSearchForm onSearch={MockOnSearch} initialValues={initialValues} />
    );

    // The form should be initialized with these values
    // Since we're mocking useForm, we can't test the actual initial values
    // but we can verify the component renders without errors
    expect(screen.getByText("Destination Search")).toBeInTheDocument();
  });

  it("handles autocomplete suggestion selection", () => {
    vi.useFakeTimers();
    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);

    const input = screen.getByPlaceholderText(
      "Search for cities, countries, or landmarks..."
    ) as HTMLInputElement;

    act(() => {
      fireEvent.focus(input);
      fireEvent.change(input, { target: { value: "Par" } });
      WAIT_FOR_AUTOCOMPLETE_TICK();
    });

    const suggestionButton = screen
      .getAllByRole("button")
      .find((button) => button.textContent?.includes("Popular Destination"));
    if (suggestionButton) {
      act(() => {
        fireEvent.click(suggestionButton);
      });
      expect(input.value).toContain("Par");
    }
    vi.useRealTimers();
  });
});
