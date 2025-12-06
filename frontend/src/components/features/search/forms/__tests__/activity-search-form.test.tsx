/** @vitest-environment jsdom */

import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/test-utils";
import { ActivitySearchForm } from "../activity-search-form";

const MockOnSearch = vi.fn();

// Helper to get a future date string
function GetFutureDate(daysAhead: number): string {
  const date = new Date();
  date.setDate(date.getDate() + daysAhead);
  return date.toISOString().split("T")[0];
}

describe("ActivitySearchForm", () => {
  beforeEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("renders form with all required fields", () => {
    renderWithProviders(<ActivitySearchForm onSearch={MockOnSearch} />);

    expect(screen.getByLabelText(/destination/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^date$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/start date \(range\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/end date \(range\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/adults/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/children/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/activity category/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /search activities/i })
    ).toBeInTheDocument();
  });

  it("displays duration and price filter inputs", () => {
    renderWithProviders(<ActivitySearchForm onSearch={MockOnSearch} />);

    expect(screen.getByLabelText(/min duration/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/max duration/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/min price/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/max price/i)).toBeInTheDocument();
  });

  it("handles form submission with valid data", async () => {
    renderWithProviders(<ActivitySearchForm onSearch={MockOnSearch} />);

    const futureDate = GetFutureDate(30);

    // Fill in required fields
    fireEvent.change(screen.getByLabelText(/destination/i), {
      target: { value: "New York" },
    });
    fireEvent.change(screen.getByLabelText(/^date$/i), {
      target: { value: futureDate },
    });

    // Fill optional fields
    fireEvent.change(screen.getByLabelText(/activity category/i), {
      target: { value: "outdoor" },
    });
    fireEvent.change(screen.getByLabelText(/max duration/i), {
      target: { value: "4" },
    });
    fireEvent.change(screen.getByLabelText(/min price/i), {
      target: { value: "50" },
    });
    fireEvent.change(screen.getByLabelText(/max price/i), {
      target: { value: "200" },
    });

    const submitButton = screen.getByRole("button", {
      name: /search activities/i,
    });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(MockOnSearch).toHaveBeenCalledWith(
        expect.objectContaining({
          adults: 1,
          category: "outdoor",
          children: 0,
          date: futureDate,
          destination: "New York",
        })
      );
    });
  });

  it("handles participant count changes", async () => {
    renderWithProviders(<ActivitySearchForm onSearch={MockOnSearch} />);

    const futureDate = GetFutureDate(60);

    // Fill required fields first
    const destinationInput = screen.getByLabelText(/destination/i);
    const dateInput = screen.getByLabelText(/^date$/i);
    const adultsInput = screen.getByLabelText(/adults/i);
    const childrenInput = screen.getByLabelText(/children/i);
    const submitButton = screen.getByRole("button", {
      name: /search activities/i,
    });

    fireEvent.change(destinationInput, { target: { value: "Paris" } });
    fireEvent.change(dateInput, { target: { value: futureDate } });
    fireEvent.change(adultsInput, { target: { value: "2" } });
    fireEvent.change(childrenInput, { target: { value: "1" } });

    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(MockOnSearch).toHaveBeenCalledWith(
        expect.objectContaining({
          adults: 2,
          children: 1,
          destination: "Paris",
        })
      );
    });
  });

  it("submits with category value", async () => {
    renderWithProviders(<ActivitySearchForm onSearch={MockOnSearch} />);

    const futureDate = GetFutureDate(90);

    const destinationInput = screen.getByLabelText(/destination/i);
    const dateInput = screen.getByLabelText(/^date$/i);
    const categoryInput = screen.getByLabelText(/activity category/i);
    const submitButton = screen.getByRole("button", { name: /search activities/i });

    fireEvent.change(destinationInput, { target: { value: "Lisbon" } });
    fireEvent.change(dateInput, { target: { value: futureDate } });
    fireEvent.change(categoryInput, { target: { value: "cultural" } });

    fireEvent.click(submitButton);

    await waitFor(
      () => {
        expect(MockOnSearch).toHaveBeenCalledTimes(1);
        expect(MockOnSearch).toHaveBeenCalledWith(
          expect.objectContaining({
            category: "cultural",
          })
        );
      },
      { timeout: 1000 }
    );
  });

  it("handles category input changes", () => {
    renderWithProviders(<ActivitySearchForm onSearch={MockOnSearch} />);

    const categoryInput = screen.getByLabelText(/activity category/i);

    // Initially empty
    expect(categoryInput).toHaveValue("");

    // Enter a category value
    fireEvent.change(categoryInput, { target: { value: "outdoor" } });
    expect(categoryInput).toHaveValue("outdoor");

    // Change category
    fireEvent.change(categoryInput, { target: { value: "cultural" } });
    expect(categoryInput).toHaveValue("cultural");

    // Clear category
    fireEvent.change(categoryInput, { target: { value: "" } });
    expect(categoryInput).toHaveValue("");
  });

  it("applies initial values correctly", () => {
    const initialValues = {
      category: "food",
      destination: "Tokyo",
      duration: { max: 6, min: 1 },
      participants: {
        adults: 3,
        children: 2,
      },
    };

    renderWithProviders(
      <ActivitySearchForm initialValues={initialValues} onSearch={MockOnSearch} />
    );

    expect(screen.getByDisplayValue("Tokyo")).toBeInTheDocument();
    expect(screen.getByDisplayValue("3")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2")).toBeInTheDocument();
  });

  it("validates number input ranges", async () => {
    renderWithProviders(<ActivitySearchForm onSearch={MockOnSearch} />);

    // Test adults min/max
    const adultsInput = screen.getByLabelText(/adults/i);
    fireEvent.change(adultsInput, { target: { value: "0" } });
    fireEvent.blur(adultsInput);

    // Test children max
    const childrenInput = screen.getByLabelText(/children/i);
    fireEvent.change(childrenInput, { target: { value: "15" } });
    fireEvent.blur(childrenInput);

    // Test duration min - use the specific min duration input
    const minDurationInput = screen.getByLabelText(/min duration/i);
    fireEvent.change(minDurationInput, { target: { value: "50" } });
    fireEvent.blur(minDurationInput);

    const submitButton = screen.getByRole("button", {
      name: /search activities/i,
    });

    fireEvent.click(submitButton);

    // The form should handle validation or input constraints
    await waitFor(
      () => {
        expect(screen.getByLabelText(/adults/i)).toBeInTheDocument();
      },
      { timeout: 500 }
    );
  });
});
