import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FlightSearchForm } from "../flight-search-form";

// Mock the onSearch function
const mockOnSearch = vi.fn();

describe("FlightSearchForm", () => {
  beforeEach(() => {
    // Clear mock calls between tests
    mockOnSearch.mockClear();
  });

  it("renders the form correctly", () => {
    render(<FlightSearchForm onSearch={mockOnSearch} />);

    // Check if the form title is present
    expect(screen.getByText("Flight Search")).toBeInTheDocument();

    // Check if trip type options are present
    expect(screen.getByText("Round Trip")).toBeInTheDocument();
    expect(screen.getByText("One Way")).toBeInTheDocument();
    expect(screen.getByText("Multi-City")).toBeInTheDocument();

    // Check if origin and destination fields are present
    expect(screen.getByText("Origin")).toBeInTheDocument();
    expect(screen.getByText("Destination")).toBeInTheDocument();

    // Check if date fields are present
    expect(screen.getByText("Departure Date")).toBeInTheDocument();
    expect(screen.getByText("Return Date")).toBeInTheDocument();

    // Check if passenger fields are present
    expect(screen.getByText("Adults")).toBeInTheDocument();
    expect(screen.getByText("Children (2-11)")).toBeInTheDocument();
    expect(screen.getByText("Infants (0-1)")).toBeInTheDocument();

    // Check if cabin class options are present
    expect(screen.getByText("Cabin Class")).toBeInTheDocument();
    expect(screen.getByText("Economy")).toBeInTheDocument();
    expect(screen.getByText("Business")).toBeInTheDocument();
    expect(screen.getByText("First")).toBeInTheDocument();

    // Check if additional options are present
    expect(screen.getByText("Direct Flights Only")).toBeInTheDocument();
    expect(screen.getByText("Flexible Dates")).toBeInTheDocument();

    // Check if search button is present
    expect(screen.getByText("Search Flights")).toBeInTheDocument();
  });

  it("handles form submission with valid data", async () => {
    render(<FlightSearchForm onSearch={mockOnSearch} />);

    // Fill in required fields
    fireEvent.change(screen.getByPlaceholderText("City or airport"), {
      target: { value: "New York" },
    });
    fireEvent.change(screen.getAllByPlaceholderText("City or airport")[1], {
      target: { value: "London" },
    });

    const departureDateInput = screen.getByLabelText("Departure Date");
    const returnDateInput = screen.getByLabelText("Return Date");

    fireEvent.change(departureDateInput, { target: { value: "2025-08-15" } });
    fireEvent.change(returnDateInput, { target: { value: "2025-08-25" } });

    // Submit the form
    fireEvent.click(screen.getByText("Search Flights"));

    // Check if onSearch was called with the correct data
    expect(mockOnSearch).toHaveBeenCalledTimes(1);
    expect(mockOnSearch).toHaveBeenCalledWith({
      origin: "New York",
      destination: "London",
      startDate: "2025-08-15",
      endDate: "2025-08-25",
      adults: 1,
      children: 0,
      infants: 0,
      cabinClass: "economy",
      directOnly: false,
    });
  });
});
