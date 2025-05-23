import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi, beforeEach } from "vitest";
import HotelSearchPage from "../page";
import { api } from "@/lib/api/client";

// Mock dependencies
vi.mock("@/lib/api/client", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

vi.mock("@/components/layouts/search-layout", () => ({
  SearchLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="search-layout">{children}</div>
  ),
}));

vi.mock("@/stores/search-store", () => {
  const mockStore = {
    results: { accommodations: [] },
    error: null,
    updateAccommodationParams: vi.fn(),
    setResults: vi.fn(),
    setIsLoading: vi.fn(),
    setError: vi.fn(),
  };

  return {
    useSearchStore: vi.fn(() => mockStore),
  };
});

describe("HotelSearchPage", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it("should render the hotel search form", () => {
    render(<HotelSearchPage />, { wrapper });

    expect(screen.getByText("Hotel Search")).toBeInTheDocument();
    expect(
      screen.getByText("Find the perfect accommodation for your stay")
    ).toBeInTheDocument();
  });

  it("should show popular destinations when no search performed", () => {
    render(<HotelSearchPage />, { wrapper });

    expect(screen.getByText("Popular Destinations")).toBeInTheDocument();
    expect(screen.getByText("New York")).toBeInTheDocument();
    expect(screen.getByText("Paris")).toBeInTheDocument();
    expect(screen.getByText("Tokyo")).toBeInTheDocument();
  });

  it("should show accommodation tips", () => {
    render(<HotelSearchPage />, { wrapper });

    expect(screen.getByText("Accommodation Tips")).toBeInTheDocument();
    expect(
      screen.getByText("Book directly with hotels for possible benefits")
    ).toBeInTheDocument();
    expect(screen.getByText("Consider location carefully")).toBeInTheDocument();
  });

  it("should perform search when form is submitted", async () => {
    const mockSearchResponse = {
      results: [
        {
          id: "1",
          name: "Test Hotel",
          type: "Hotel",
          location: "New York",
          checkIn: "2024-03-15",
          checkOut: "2024-03-18",
          pricePerNight: 200,
          totalPrice: 600,
          rating: 4.5,
          amenities: ["wifi", "gym"],
          images: [],
        },
      ],
      totalResults: 1,
    };

    (api.post as any).mockResolvedValueOnce(mockSearchResponse);

    render(<HotelSearchPage />, { wrapper });

    // Fill in the form
    fireEvent.change(
      screen.getByPlaceholderText("City, address, or landmark"),
      {
        target: { value: "New York" },
      }
    );

    const checkInInput = screen.getByLabelText("Check-in Date");
    fireEvent.change(checkInInput, { target: { value: "2024-03-15" } });

    const checkOutInput = screen.getByLabelText("Check-out Date");
    fireEvent.change(checkOutInput, { target: { value: "2024-03-18" } });

    // Submit the form
    const searchButton = screen.getByText("Search Hotels");
    fireEvent.click(searchButton);

    // Should show searching state
    await waitFor(() => {
      expect(
        screen.getByText("Searching for accommodations...")
      ).toBeInTheDocument();
    });
  });

  it("should display error message on search failure", async () => {
    const { useSearchStore } = await import("@/stores/search-store");
    vi.mocked(useSearchStore).mockReturnValue({
      results: { accommodations: [] },
      error: "Failed to search accommodations",
      updateAccommodationParams: vi.fn(),
      setResults: vi.fn(),
      setIsLoading: vi.fn(),
      setError: vi.fn(),
    });

    render(<HotelSearchPage />, { wrapper });

    expect(
      screen.getByText("Failed to search accommodations")
    ).toBeInTheDocument();
  });

  it("should handle amenity selection", () => {
    render(<HotelSearchPage />, { wrapper });

    const wifiCheckbox = screen.getByLabelText("Free WiFi");
    fireEvent.click(wifiCheckbox);

    expect(wifiCheckbox).toBeChecked();
  });

  it("should handle guest count inputs", () => {
    render(<HotelSearchPage />, { wrapper });

    const adultsInput = screen.getByLabelText("Adults");
    fireEvent.change(adultsInput, { target: { value: "3" } });

    expect(adultsInput).toHaveValue(3);

    const childrenInput = screen.getByLabelText("Children (0-17)");
    fireEvent.change(childrenInput, { target: { value: "2" } });

    expect(childrenInput).toHaveValue(2);
  });

  it("should handle price range inputs", () => {
    render(<HotelSearchPage />, { wrapper });

    const minPriceInput = screen.getByLabelText("Min Price ($)");
    fireEvent.change(minPriceInput, { target: { value: "50" } });

    expect(minPriceInput).toHaveValue(50);

    const maxPriceInput = screen.getByLabelText("Max Price ($)");
    fireEvent.change(maxPriceInput, { target: { value: "200" } });

    expect(maxPriceInput).toHaveValue(200);
  });

  it("should handle star rating selection", () => {
    render(<HotelSearchPage />, { wrapper });

    const ratingInput = screen.getByLabelText("Star Rating (min)");
    fireEvent.change(ratingInput, { target: { value: "4" } });

    expect(ratingInput).toHaveValue(4);
  });
});
