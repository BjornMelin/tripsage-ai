/** @vitest-environment jsdom */

import type { Flight } from "@schemas/search";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SearchResults } from "../search-results";

/** Mock function for testing sort functionality. */
const MockOnSort = vi.fn();
/** Mock function for testing filter functionality. */
const MockOnFilter = vi.fn();

/** Mock flight data for testing search results display. */
const MockFlights: Flight[] = [
  {
    airline: "Test Airline",
    arrivalTime: "10:00 PM",
    cabinClass: "economy",
    departureTime: "10:00 AM",
    destination: "LHR",
    duration: 600, // 10 hours in minutes
    flightNumber: "TA123",
    id: "1",
    origin: "JFK",
    price: 499,
    seatsAvailable: 10,
    stops: 0,
  },
  {
    airline: "Another Airline",
    arrivalTime: "12:30 AM",
    cabinClass: "economy",
    departureTime: "12:00 PM",
    destination: "LHR",
    duration: 630, // 10.5 hours in minutes
    flightNumber: "AA456",
    id: "2",
    layovers: [
      {
        airport: "BOS",
        duration: 90,
      },
    ],
    origin: "JFK",
    price: 399,
    seatsAvailable: 5,
    stops: 1,
  },
];

describe("SearchResults", () => {
  beforeEach(() => {
    // Clear mock calls between tests
    MockOnSort.mockClear();
    MockOnFilter.mockClear();
  });

  it("renders the results correctly", () => {
    render(
      <SearchResults
        type="flight"
        results={MockFlights}
        onSort={MockOnSort}
        onFilter={MockOnFilter}
      />
    );

    // Check if the results count is displayed
    expect(screen.getByText("2 Results")).toBeInTheDocument();

    // Check if view toggle buttons are present
    expect(screen.getByText("List")).toBeInTheDocument();
    expect(screen.getByText("Grid")).toBeInTheDocument();
    expect(screen.getByText("Map")).toBeInTheDocument();

    // Check if sort options are present
    expect(screen.getByText("Price")).toBeInTheDocument();
    expect(screen.getByText("Duration")).toBeInTheDocument();
    expect(screen.getByText("Stops")).toBeInTheDocument();

    // Check if flight details are displayed
    expect(screen.getByText("Test Airline TA123")).toBeInTheDocument();
    expect(screen.getByText("Another Airline AA456")).toBeInTheDocument();
    expect(screen.getByText("Nonstop")).toBeInTheDocument();
    expect(screen.getByText("1 stop")).toBeInTheDocument();
    expect(screen.getAllByText("$499")).toHaveLength(1);
    expect(screen.getAllByText("$399")).toHaveLength(1);
  });

  it("handles sorting correctly", () => {
    render(
      <SearchResults
        type="flight"
        results={MockFlights}
        onSort={MockOnSort}
        onFilter={MockOnFilter}
      />
    );

    // Click the price sort button
    fireEvent.click(screen.getByText("Price"));

    // Check if onSort was called with the correct parameters
    expect(MockOnSort).toHaveBeenCalledTimes(1);
    expect(MockOnSort).toHaveBeenCalledWith("price", "desc");

    // Click again to toggle sort direction
    fireEvent.click(screen.getByText("Price"));

    // Check if onSort was called again with the opposite direction
    expect(MockOnSort).toHaveBeenCalledTimes(2);
    expect(MockOnSort).toHaveBeenCalledWith("price", "asc");
  });

  it("handles view toggle correctly", () => {
    render(
      <SearchResults
        type="flight"
        results={MockFlights}
        onSort={MockOnSort}
        onFilter={MockOnFilter}
      />
    );

    // Default view should be list
    expect(screen.getByText("List")).toHaveClass("bg-primary");

    // Click the grid view button
    fireEvent.click(screen.getByText("Grid"));

    // Grid button should now be selected
    expect(screen.getByText("Grid")).toHaveClass("bg-primary");
    expect(screen.getByText("List")).not.toHaveClass("bg-primary");

    // Click the map view button
    fireEvent.click(screen.getByText("Map"));

    // Map button should now be selected
    expect(screen.getByText("Map")).toHaveClass("bg-primary");
    expect(screen.getByText("Grid")).not.toHaveClass("bg-primary");
  });

  it("displays loading state when loading is true", () => {
    render(
      <SearchResults
        type="flight"
        results={[]}
        loading={true}
        onSort={MockOnSort}
        onFilter={MockOnFilter}
      />
    );

    // Assert loading text is rendered
    expect(screen.getByText("Searching...")).toBeInTheDocument();

    // Assert spinner by class since component doesn't expose a test id
    expect(document.querySelectorAll(".animate-spin").length).toBeGreaterThan(0);

    // Results should not be displayed
    expect(screen.queryByText("Test Airline TA123")).not.toBeInTheDocument();
  });

  it("displays empty state when no results", () => {
    render(
      <SearchResults
        type="flight"
        results={[]}
        onSort={MockOnSort}
        onFilter={MockOnFilter}
      />
    );

    // Check if empty state message is displayed
    expect(
      screen.getByText("No results found. Try adjusting your search criteria.")
    ).toBeInTheDocument();

    // Results should not be displayed
    expect(screen.queryByText("Test Airline TA123")).not.toBeInTheDocument();
  });
});
