/**
 * @fileoverview Unit tests for SearchResults component, verifying flight display,
 * sorting functionality, filtering capabilities, loading states, and user
 * interactions with flight cards, price display, and booking actions.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Flight } from "@/types/search";
import { SearchResults } from "../search-results";

/** Mock function for testing sort functionality. */
const MOCK_ON_SORT = vi.fn();
/** Mock function for testing filter functionality. */
const MOCK_ON_FILTER = vi.fn();

/** Mock flight data for testing search results display. */
const MOCK_FLIGHTS: Flight[] = [
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
    MOCK_ON_SORT.mockClear();
    MOCK_ON_FILTER.mockClear();
  });

  it("renders the results correctly", () => {
    render(
      <SearchResults
        type="flight"
        results={MOCK_FLIGHTS}
        onSort={MOCK_ON_SORT}
        onFilter={MOCK_ON_FILTER}
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
        results={MOCK_FLIGHTS}
        onSort={MOCK_ON_SORT}
        onFilter={MOCK_ON_FILTER}
      />
    );

    // Click the price sort button
    fireEvent.click(screen.getByText("Price"));

    // Check if onSort was called with the correct parameters
    expect(MOCK_ON_SORT).toHaveBeenCalledTimes(1);
    expect(MOCK_ON_SORT).toHaveBeenCalledWith("price", "desc");

    // Click again to toggle sort direction
    fireEvent.click(screen.getByText("Price"));

    // Check if onSort was called again with the opposite direction
    expect(MOCK_ON_SORT).toHaveBeenCalledTimes(2);
    expect(MOCK_ON_SORT).toHaveBeenCalledWith("price", "asc");
  });

  it("handles view toggle correctly", () => {
    render(
      <SearchResults
        type="flight"
        results={MOCK_FLIGHTS}
        onSort={MOCK_ON_SORT}
        onFilter={MOCK_ON_FILTER}
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
        onSort={MOCK_ON_SORT}
        onFilter={MOCK_ON_FILTER}
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
        onSort={MOCK_ON_SORT}
        onFilter={MOCK_ON_FILTER}
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
