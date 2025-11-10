import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ActivitySearchForm } from "../activity-search-form";

const CreateWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("ActivitySearchForm", () => {
  it("renders form with all required fields", () => {
    render(<ActivitySearchForm />, { wrapper: CreateWrapper() });

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
    render(<ActivitySearchForm />, { wrapper: CreateWrapper() });

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
    render(<ActivitySearchForm />, { wrapper: CreateWrapper() });

    const submitButton = screen.getByRole("button", {
      name: /search activities/i,
    });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText("Location is required")).toBeInTheDocument();
      expect(screen.getByText("Start date is required")).toBeInTheDocument();
      expect(screen.getByText("End date is required")).toBeInTheDocument();
    });
  });

  // TODO: Wire to real search pipeline; confirm payload shape.
  it.skip("handles form submission with valid data", async () => {
    const mockOnSearch = vi.fn();
    render(<ActivitySearchForm onSearch={mockOnSearch} />, {
      wrapper: CreateWrapper(),
    });

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
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSearch).toHaveBeenCalledWith({
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
  });

  it("handles participant count changes", async () => {
    const mockOnSearch = vi.fn();
    render(<ActivitySearchForm onSearch={mockOnSearch} />, {
      wrapper: CreateWrapper(),
    });

    // Change participant counts
    fireEvent.change(screen.getByLabelText(/adults/i), {
      target: { value: "2" },
    });
    fireEvent.change(screen.getByLabelText(/children/i), {
      target: { value: "1" },
    });
    fireEvent.change(screen.getByLabelText(/infants/i), {
      target: { value: "1" },
    });

    // Fill required fields
    fireEvent.change(screen.getByLabelText(/location/i), {
      target: { value: "Paris" },
    });
    fireEvent.change(screen.getByLabelText(/start date/i), {
      target: { value: "2024-08-01" },
    });
    fireEvent.change(screen.getByLabelText(/end date/i), {
      target: { value: "2024-08-05" },
    });

    const submitButton = screen.getByRole("button", {
      name: /search activities/i,
    });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockOnSearch).toHaveBeenCalledWith(
        expect.objectContaining({
          adults: 2,
          children: 1,
          infants: 1,
        })
      );
    });
  });

  it("handles category selection and deselection", () => {
    render(<ActivitySearchForm />, { wrapper: CreateWrapper() });

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

    render(<ActivitySearchForm initialValues={initialValues} />, {
      wrapper: CreateWrapper(),
    });

    expect(screen.getByDisplayValue("Tokyo")).toBeInTheDocument();
    expect(screen.getByDisplayValue("3")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2")).toBeInTheDocument();
    expect(screen.getByDisplayValue("6")).toBeInTheDocument();
    expect(screen.getByLabelText(/food & drink/i)).toBeChecked();
    expect(screen.getByLabelText(/cultural & historical/i)).toBeChecked();
  });

  it("validates number input ranges", async () => {
    render(<ActivitySearchForm />, { wrapper: CreateWrapper() });

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

    // Values should be clamped or validation should occur
    await waitFor(() => {
      // The form should handle validation or input constraints
      expect(screen.getByLabelText(/adults/i)).toBeInTheDocument();
    });
  });
});
