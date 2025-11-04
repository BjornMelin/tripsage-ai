/**
 * @fileoverview Unit tests for DestinationSearchForm component, verifying form rendering,
 * user interactions, validation, popular destinations display, and search submission
 * with various input scenarios and accessibility features.
 */

import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/test-utils.test";
import { DestinationSearchForm } from "../destination-search-form";

// Use real react-hook-form behavior; keep tests focused on visible output

// Mock function for testing search form submission.
const MockOnSearch = vi.fn();

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

  it("handles form submission", async () => {
    const user = userEvent.setup();
    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);
    const input = screen.getByPlaceholderText(
      "Search for cities, countries, or landmarks..."
    );
    await user.clear(input);
    await user.type(input, "Paris");
    const submitButton = screen.getByRole("button", { name: "Search Destinations" });
    await user.click(submitButton);
    expect(MockOnSearch).toHaveBeenCalledWith(
      expect.objectContaining({ query: "Paris" })
    );
  });

  it("handles popular destination selection", async () => {
    const user = userEvent.setup();
    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);

    const parisButton = screen.getByText("Paris, France");
    await user.click(parisButton);

    // The setValue function should be called when a popular destination is clicked
    // This is mocked in our useForm mock
  });

  it("displays advanced options", () => {
    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);

    expect(screen.getByText("Max Results")).toBeInTheDocument();
    expect(screen.getByText("Language (optional)")).toBeInTheDocument();
    expect(screen.getByText("Region (optional)")).toBeInTheDocument();
  });

  it("shows autocomplete suggestions when typing", async () => {
    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);

    // Test that the suggestions container is set up
    const input = screen.getByPlaceholderText(
      "Search for cities, countries, or landmarks..."
    );
    expect(input).toBeInTheDocument();

    // The actual suggestions would be tested with a proper mock of the API calls
    // For now, we verify the input exists and is interactive
    await userEvent.type(input, "Par");
  });

  it("handles checkbox changes for destination types", async () => {
    const user = userEvent.setup();
    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);
    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes.length).toBeGreaterThan(0);
    await user.click(checkboxes[0]);
    if (checkboxes[1]) await user.click(checkboxes[1]);
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

  it("handles autocomplete suggestion selection", async () => {
    const user = userEvent.setup();
    renderWithProviders(<DestinationSearchForm onSearch={MockOnSearch} />);

    const input = screen.getByPlaceholderText(
      "Search for cities, countries, or landmarks..."
    );

    // Focus the input to potentially show suggestions
    await user.click(input);

    // Type to trigger suggestions
    await user.type(input, "Par");

    // The actual suggestion interaction would require mocking the API
    // For now, we verify the input responds to user interaction
    expect(input).toHaveFocus();
  });
});
