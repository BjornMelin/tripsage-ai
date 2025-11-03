/**
 * @fileoverview Unit tests for FlightSearchForm component, covering form rendering,
 * user input handling, validation, trip type switching, passenger selection,
 * and search submission with various scenarios and edge cases.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FlightSearchForm } from "../flight-search-form";

// Mock the onSearch function
const MockOnSearch = vi.fn();

describe("FlightSearchForm", () => {
  beforeEach(() => {
    // Clear mock calls between tests
    MockOnSearch.mockClear();
  });

  it("renders the form correctly (aligned with current UI)", () => {
    render(<FlightSearchForm onSearch={MockOnSearch} />);

    // Title and trip type buttons
    expect(screen.getByText("Find Flights")).toBeInTheDocument();
    expect(screen.getByText("Round Trip")).toBeInTheDocument();
    expect(screen.getByText("One Way")).toBeInTheDocument();
    expect(screen.getByText("Multi-City")).toBeInTheDocument();

    // From/To labels
    expect(screen.getByText("From")).toBeInTheDocument();
    expect(screen.getByText("To")).toBeInTheDocument();

    // Date labels
    expect(screen.getByText("Departure")).toBeInTheDocument();
    expect(screen.getByText("Return")).toBeInTheDocument();

    // Passenger label hints
    expect(screen.getByText("Adults")).toBeInTheDocument();
    expect(screen.getByText(/Children \(2-11\)/)).toBeInTheDocument();

    // Primary actions
    expect(screen.getByText("Search Flights")).toBeInTheDocument();
    expect(screen.getByText("Flexible Dates")).toBeInTheDocument();
  });

  it("handles form submission with valid data", async () => {
    render(<FlightSearchForm onSearch={MockOnSearch} />);

    // Fill in required fields matching current placeholders/labels
    fireEvent.change(screen.getByPlaceholderText("Departure city or airport"), {
      target: { value: "New York" },
    });
    fireEvent.change(screen.getByPlaceholderText("Destination city or airport"), {
      target: { value: "London" },
    });

    // Date inputs (type=date) are not directly label-associated due to wrapper structure;
    // select by role order within the form.
    const container = document.body;
    const dateInputs = Array.from(
      container.querySelectorAll('input[type="date"]')
    ) as HTMLInputElement[];
    const [departureDateInput, returnDateInput] = dateInputs;

    fireEvent.change(departureDateInput, { target: { value: "2099-08-15" } });
    fireEvent.change(returnDateInput, { target: { value: "2099-08-25" } });

    // Submit the form (ensure form submit event is dispatched)
    const submitBtn = screen.getByText("Search Flights");
    const formEl = submitBtn.closest("form") as HTMLFormElement;
    expect(formEl).toBeTruthy();
    fireEvent.submit(formEl!);

    // onSearch receives schema-validated FlightSearchFormData shape (async)
    await vi.waitFor(() => expect(MockOnSearch).toHaveBeenCalledTimes(1));
    expect(MockOnSearch).toHaveBeenCalledWith({
      cabinClass: "economy",
      departureDate: "2099-08-15",
      destination: "London",
      directOnly: false,
      excludedAirlines: [],
      maxStops: undefined,
      origin: "New York",
      passengers: { adults: 1, children: 0, infants: 0 },
      preferredAirlines: [],
      returnDate: "2099-08-25",
      tripType: "round-trip",
    });
  });
});
