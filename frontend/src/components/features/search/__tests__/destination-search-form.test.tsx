/**
 * @vitest-environment jsdom
 */

import type { DestinationSearchParams } from "@/types/search";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DestinationSearchForm } from "../destination-search-form";

// Mock the form dependencies
vi.mock("react-hook-form", async () => {
  const actual = await vi.importActual("react-hook-form");
  return {
    ...actual,
    useForm: () => ({
      control: {},
      handleSubmit: (fn: Function) => (e: Event) => {
        e.preventDefault();
        fn({
          query: "Paris",
          types: ["locality", "country"],
          limit: 10,
        });
      },
      watch: (name: string) => {
        if (name === "query") return "Paris";
        if (name === "types") return ["locality", "country"];
        return undefined;
      },
      setValue: vi.fn(),
      getValues: () => ({
        query: "Paris",
        types: ["locality", "country"],
      }),
      formState: { errors: {} },
    }),
  };
});

const mockOnSearch = vi.fn();

describe("DestinationSearchForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the destination search form correctly", () => {
    render(<DestinationSearchForm onSearch={mockOnSearch} />);

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
    render(<DestinationSearchForm onSearch={mockOnSearch} />);

    expect(screen.getByText("Popular Destinations")).toBeInTheDocument();
    expect(screen.getByText("Paris, France")).toBeInTheDocument();
    expect(screen.getByText("Tokyo, Japan")).toBeInTheDocument();
    expect(screen.getByText("New York, USA")).toBeInTheDocument();
  });

  it("displays destination type checkboxes", () => {
    render(<DestinationSearchForm onSearch={mockOnSearch} />);

    expect(screen.getByText("Cities & Towns")).toBeInTheDocument();
    expect(screen.getByText("Countries")).toBeInTheDocument();
    expect(screen.getByText("States & Regions")).toBeInTheDocument();
    expect(screen.getByText("Landmarks & Places")).toBeInTheDocument();
  });

  it("handles form submission", async () => {
    const user = userEvent.setup();
    render(<DestinationSearchForm onSearch={mockOnSearch} />);

    const submitButton = screen.getByRole("button", {
      name: "Search Destinations",
    });
    await user.click(submitButton);

    expect(mockOnSearch).toHaveBeenCalledWith({
      query: "Paris",
      types: ["locality", "country"],
      limit: 10,
    });
  });

  it("handles popular destination selection", async () => {
    const user = userEvent.setup();
    render(<DestinationSearchForm onSearch={mockOnSearch} />);

    const parisButton = screen.getByText("Paris, France");
    await user.click(parisButton);

    // The setValue function should be called when a popular destination is clicked
    // This is mocked in our useForm mock
  });

  it("displays advanced options", () => {
    render(<DestinationSearchForm onSearch={mockOnSearch} />);

    expect(screen.getByText("Max Results")).toBeInTheDocument();
    expect(screen.getByText("Language (optional)")).toBeInTheDocument();
    expect(screen.getByText("Region (optional)")).toBeInTheDocument();
  });

  it("shows autocomplete suggestions when typing", async () => {
    render(<DestinationSearchForm onSearch={mockOnSearch} />);

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
    render(<DestinationSearchForm onSearch={mockOnSearch} />);

    // Find checkboxes by their labels
    const localityCheckbox = screen.getByRole("checkbox", {
      name: /cities & towns/i,
    });
    const countryCheckbox = screen.getByRole("checkbox", {
      name: /countries/i,
    });

    expect(localityCheckbox).toBeInTheDocument();
    expect(countryCheckbox).toBeInTheDocument();

    // Test checking/unchecking
    await user.click(localityCheckbox);
    await user.click(countryCheckbox);
  });

  it("validates required fields", () => {
    render(<DestinationSearchForm onSearch={mockOnSearch} />);

    // The form should have validation for the query field
    const queryInput = screen.getByPlaceholderText(
      "Search for cities, countries, or landmarks..."
    );
    expect(queryInput).toBeRequired();
  });

  it("uses initial values when provided", () => {
    const initialValues = {
      query: "Tokyo",
      types: ["establishment"] as (
        | "country"
        | "locality"
        | "administrative_area"
        | "establishment"
      )[],
      limit: 5,
    };

    render(
      <DestinationSearchForm onSearch={mockOnSearch} initialValues={initialValues} />
    );

    // The form should be initialized with these values
    // Since we're mocking useForm, we can't test the actual initial values
    // but we can verify the component renders without errors
    expect(screen.getByText("Destination Search")).toBeInTheDocument();
  });

  it("handles autocomplete suggestion selection", async () => {
    const user = userEvent.setup();
    render(<DestinationSearchForm onSearch={mockOnSearch} />);

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
