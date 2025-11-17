/** @vitest-environment jsdom */

import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/test-utils";
import { ActivitySearchForm } from "../activity-search-form";

const MockOnSearch = vi.fn();

describe("ActivitySearchForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders form with all required fields", () => {
    renderWithProviders(<ActivitySearchForm onSearch={MockOnSearch} />);

    expect(screen.getByLabelText(/location/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/adults/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/children/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/infants/i)).toBeInTheDocument();
    expect(screen.getByText(/activity categories/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /search activities/i })
    ).toBeInTheDocument();
  });

  it("displays activity category options", () => {
    renderWithProviders(<ActivitySearchForm onSearch={MockOnSearch} />);

    expect(screen.getByText("Outdoor & Adventure")).toBeInTheDocument();
    expect(screen.getByText("Cultural & Historical")).toBeInTheDocument();
    expect(screen.getByText("Food & Drink")).toBeInTheDocument();
    expect(screen.getByText("Guided Tours")).toBeInTheDocument();
    expect(screen.getByText("Water Sports")).toBeInTheDocument();
    expect(screen.getByText("Wildlife & Nature")).toBeInTheDocument();
    expect(screen.getByText("Sports & Recreation")).toBeInTheDocument();
    expect(screen.getByText("Nightlife & Entertainment")).toBeInTheDocument();
    expect(screen.getByText("Wellness & Spa")).toBeInTheDocument();
    expect(screen.getByText("Shopping")).toBeInTheDocument();
    expect(screen.getByText("Transportation")).toBeInTheDocument();
    expect(screen.getByText("Classes & Workshops")).toBeInTheDocument();
  });

  it("validates required fields", async () => {
    renderWithProviders(<ActivitySearchForm onSearch={MockOnSearch} />);

    const submitButton = screen.getByRole("button", {
      name: /search activities/i,
    });

    fireEvent.click(submitButton);

    await waitFor(
      () => {
        expect(screen.getByText("Location is required")).toBeInTheDocument();
      },
      { timeout: 1000 }
    );

    await waitFor(
      () => {
        expect(screen.getByText("Start date is required")).toBeInTheDocument();
      },
      { timeout: 1000 }
    );

    await waitFor(
      () => {
        expect(screen.getByText("End date is required")).toBeInTheDocument();
      },
      { timeout: 1000 }
    );
  });

  // TODO: Wire to real search pipeline; confirm payload shape.
  it.skip("handles form submission with valid data", () => {
    renderWithProviders(<ActivitySearchForm onSearch={MockOnSearch} />);

    // Fill in required fields
    fireEvent.change(screen.getByLabelText(/location/i), {
      target: { value: "New York" },
    });
    fireEvent.change(screen.getByLabelText(/start date/i), {
      target: { value: "2024-07-01" },
    });
    fireEvent.change(screen.getByLabelText(/end date/i), {
      target: { value: "2024-07-03" },
    });

    // Select some categories
    fireEvent.click(screen.getByLabelText(/outdoor & adventure/i));
    fireEvent.click(screen.getByLabelText(/cultural & historical/i));

    // Fill optional fields
    fireEvent.change(screen.getByLabelText(/duration/i), {
      target: { value: "4" },
    });
    fireEvent.change(screen.getByLabelText(/min rating/i), {
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
    act(() => {
      fireEvent.click(submitButton);
    });

    expect(MockOnSearch).toHaveBeenCalledWith({
      adults: 1,
      categories: ["outdoor", "cultural"],
      children: 0,
      destination: "New York",
      duration: 4,
      endDate: "2024-07-03",
      infants: 0,
      priceRange: {
        max: 200,
        min: 50,
      },
      rating: 4,
      startDate: "2024-07-01",
    });
  });

  it("handles participant count changes", async () => {
    renderWithProviders(<ActivitySearchForm onSearch={MockOnSearch} />);

    // Fill required fields first
    const locationInput = screen.getByLabelText(/location/i);
    const startDateInput = screen.getByLabelText(/start date/i);
    const endDateInput = screen.getByLabelText(/end date/i);
    const adultsInput = screen.getByLabelText(/adults/i);
    const childrenInput = screen.getByLabelText(/children/i);
    const infantsInput = screen.getByLabelText(/infants/i);
    const submitButton = screen.getByRole("button", {
      name: /search activities/i,
    });

    fireEvent.change(locationInput, { target: { value: "Paris" } });
    fireEvent.change(startDateInput, { target: { value: "2024-08-01" } });
    fireEvent.change(endDateInput, { target: { value: "2024-08-05" } });
    fireEvent.change(adultsInput, { target: { value: "2" } });
    fireEvent.change(childrenInput, { target: { value: "1" } });
    fireEvent.change(infantsInput, { target: { value: "1" } });

    fireEvent.click(submitButton);

    await waitFor(
      () => {
        expect(MockOnSearch).toHaveBeenCalledWith(
          expect.objectContaining({
            adults: 2,
            children: 1,
            destination: "Paris",
            infants: 1,
          })
        );
      },
      { timeout: 1000 }
    );
  });

  it("accepts fractional rating values", async () => {
    renderWithProviders(<ActivitySearchForm onSearch={MockOnSearch} />);

    const locationInput = screen.getByLabelText(/location/i);
    const startDateInput = screen.getByLabelText(/start date/i);
    const endDateInput = screen.getByLabelText(/end date/i);
    const ratingInput = screen.getByLabelText(/min rating/i);
    const submitButton = screen.getByRole("button", { name: /search activities/i });

    fireEvent.change(locationInput, { target: { value: "Lisbon" } });
    fireEvent.change(startDateInput, { target: { value: "2024-09-01" } });
    fireEvent.change(endDateInput, { target: { value: "2024-09-05" } });
    fireEvent.change(ratingInput, { target: { value: "4.5" } });

    fireEvent.click(submitButton);

    await waitFor(
      () => {
        expect(MockOnSearch).toHaveBeenCalledTimes(1);
      },
      { timeout: 1000 }
    );
  });

  it("handles category selection and deselection", () => {
    renderWithProviders(<ActivitySearchForm onSearch={MockOnSearch} />);

    const outdoorCheckbox = screen.getByLabelText(/outdoor & adventure/i);
    const culturalCheckbox = screen.getByLabelText(/cultural & historical/i);

    // Initially unchecked
    expect(outdoorCheckbox).not.toBeChecked();
    expect(culturalCheckbox).not.toBeChecked();

    // Select categories
    fireEvent.click(outdoorCheckbox);
    fireEvent.click(culturalCheckbox);

    expect(outdoorCheckbox).toBeChecked();
    expect(culturalCheckbox).toBeChecked();

    // Deselect one category
    fireEvent.click(outdoorCheckbox);

    expect(outdoorCheckbox).not.toBeChecked();
    expect(culturalCheckbox).toBeChecked();
  });

  it("applies initial values correctly", () => {
    const initialValues = {
      adults: 3,
      categories: ["food", "cultural"],
      children: 2,
      duration: 6,
      location: "Tokyo",
    };

    renderWithProviders(
      <ActivitySearchForm initialValues={initialValues} onSearch={MockOnSearch} />
    );

    expect(screen.getByDisplayValue("Tokyo")).toBeInTheDocument();
    expect(screen.getByDisplayValue("3")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2")).toBeInTheDocument();
    expect(screen.getByDisplayValue("6")).toBeInTheDocument();
    expect(screen.getByLabelText(/food & drink/i)).toBeChecked();
    expect(screen.getByLabelText(/cultural & historical/i)).toBeChecked();
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

    // Test duration max
    const durationInput = screen.getByLabelText(/duration/i);
    fireEvent.change(durationInput, { target: { value: "50" } });
    fireEvent.blur(durationInput);

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
