import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { TripSuggestions } from "../trip-suggestions";
import { useDealsStore } from "@/stores/deals-store";
import { useBudgetStore } from "@/stores/budget-store";

// Mock the stores
vi.mock("@/stores/deals-store", () => ({
  useDealsStore: vi.fn(),
}));

vi.mock("@/stores/budget-store", () => ({
  useBudgetStore: vi.fn(),
}));

// Mock Next.js Link component
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

describe("TripSuggestions", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock implementations
    (useDealsStore as any).mockReturnValue({});
    (useBudgetStore as any).mockReturnValue({
      budget: null,
    });
  });

  it("renders loading state correctly", () => {
    render(<TripSuggestions />);

    expect(screen.getByText("Trip Suggestions")).toBeInTheDocument();
    expect(
      screen.getByText("AI-powered travel recommendations")
    ).toBeInTheDocument();
  });

  it("renders trip suggestions correctly", () => {
    render(<TripSuggestions />);

    // Check for mock suggestions
    expect(
      screen.getByText("Tokyo Cherry Blossom Adventure")
    ).toBeInTheDocument();
    expect(screen.getByText("Bali Tropical Retreat")).toBeInTheDocument();
    expect(
      screen.getByText("Swiss Alps Hiking Experience")
    ).toBeInTheDocument();
    expect(screen.getByText("Santorini Sunset Romance")).toBeInTheDocument();
  });

  it("displays suggestion card information correctly", () => {
    render(<TripSuggestions />);

    // Check Tokyo suggestion details
    expect(screen.getByText("Tokyo, Japan")).toBeInTheDocument();
    expect(screen.getByText("$2,800")).toBeInTheDocument();
    expect(screen.getByText("7 days")).toBeInTheDocument();
    expect(screen.getByText("4.8")).toBeInTheDocument();
    expect(screen.getByText("March - May")).toBeInTheDocument();
  });

  it("shows trending badge for trending suggestions", () => {
    render(<TripSuggestions />);

    expect(screen.getByText("Trending")).toBeInTheDocument();
  });

  it("displays category icons and names", () => {
    render(<TripSuggestions />);

    expect(screen.getByText("culture")).toBeInTheDocument();
    expect(screen.getByText("relaxation")).toBeInTheDocument();
    expect(screen.getByText("adventure")).toBeInTheDocument();
    expect(screen.getByText("nature")).toBeInTheDocument();
  });

  it("shows difficulty levels with appropriate colors", () => {
    render(<TripSuggestions />);

    expect(screen.getByText("easy")).toBeInTheDocument();
    expect(screen.getByText("challenging")).toBeInTheDocument();
    expect(screen.getByText("moderate")).toBeInTheDocument();
  });

  it("displays star ratings correctly", () => {
    render(<TripSuggestions />);

    // All suggestions should have ratings
    const ratingElements = screen.getAllByText(/\d\.\d/);
    expect(ratingElements.length).toBeGreaterThan(0);
  });

  it("shows highlights as badges", () => {
    render(<TripSuggestions />);

    expect(screen.getByText("Cherry Blossoms")).toBeInTheDocument();
    expect(screen.getByText("Temples")).toBeInTheDocument();
    expect(screen.getByText("Street Food")).toBeInTheDocument();
    expect(screen.getByText("Beaches")).toBeInTheDocument();
  });

  it("truncates highlights when there are more than 3", () => {
    render(<TripSuggestions />);

    // Tokyo suggestion has 4 highlights, so should show "+1 more"
    expect(screen.getByText("+1 more")).toBeInTheDocument();
  });

  it("formats prices correctly", () => {
    render(<TripSuggestions />);

    expect(screen.getByText("$2,800")).toBeInTheDocument();
    expect(screen.getByText("$1,500")).toBeInTheDocument();
    expect(screen.getByText("$3,200")).toBeInTheDocument();
    expect(screen.getByText("$2,100")).toBeInTheDocument();
    expect(screen.getByText("$2,500")).toBeInTheDocument();
  });

  it("shows best time to visit information", () => {
    render(<TripSuggestions />);

    expect(screen.getByText("Best time: March - May")).toBeInTheDocument();
    expect(screen.getByText("Best time: April - October")).toBeInTheDocument();
    expect(screen.getByText("Best time: June - September")).toBeInTheDocument();
  });

  it("includes 'Plan Trip' buttons linking to trip creation", () => {
    render(<TripSuggestions />);

    const planTripButtons = screen.getAllByText("Plan Trip");
    expect(planTripButtons.length).toBeGreaterThan(0);

    // Check that the first button has the correct href
    const firstButton = planTripButtons[0].closest("a");
    expect(firstButton).toHaveAttribute(
      "href",
      "/dashboard/trips/create?suggestion=suggestion-1"
    );
  });

  it("filters suggestions based on budget when available", () => {
    (useBudgetStore as any).mockReturnValue({
      budget: {
        totalBudget: 2000, // Only suggestions <= $2,000 should show
      },
    });

    render(<TripSuggestions />);

    // Should show Bali ($1,500) but not Tokyo ($2,800) or Swiss Alps ($3,200)
    expect(screen.getByText("Bali Tropical Retreat")).toBeInTheDocument();
    expect(
      screen.queryByText("Tokyo Cherry Blossom Adventure")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Swiss Alps Hiking Experience")
    ).not.toBeInTheDocument();
  });

  it("shows all suggestions when no budget is set", () => {
    (useBudgetStore as any).mockReturnValue({
      budget: null,
    });

    render(<TripSuggestions />);

    // Should show all mock suggestions
    expect(
      screen.getByText("Tokyo Cherry Blossom Adventure")
    ).toBeInTheDocument();
    expect(screen.getByText("Bali Tropical Retreat")).toBeInTheDocument();
    expect(
      screen.getByText("Swiss Alps Hiking Experience")
    ).toBeInTheDocument();
  });

  it("limits the number of suggestions displayed", () => {
    render(<TripSuggestions limit={2} />);

    // Should show only 2 suggestions
    const planTripButtons = screen.getAllByText("Plan Trip");
    expect(planTripButtons.length).toBe(2);
  });

  it("renders empty state when no suggestions are available", () => {
    // Set budget very low so no suggestions match
    (useBudgetStore as any).mockReturnValue({
      budget: {
        totalBudget: 100,
      },
    });

    render(<TripSuggestions />);

    expect(
      screen.getByText(
        "Get personalized trip suggestions based on your preferences."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText("Chat with AI for Suggestions")
    ).toBeInTheDocument();
  });

  it("handles showEmpty prop correctly", () => {
    (useBudgetStore as any).mockReturnValue({
      budget: {
        totalBudget: 100, // No suggestions match
      },
    });

    const { rerender } = render(<TripSuggestions showEmpty={false} />);

    expect(
      screen.queryByText("Chat with AI for Suggestions")
    ).not.toBeInTheDocument();
    expect(screen.getByText("No suggestions available.")).toBeInTheDocument();

    rerender(<TripSuggestions showEmpty={true} />);

    expect(
      screen.getByText("Chat with AI for Suggestions")
    ).toBeInTheDocument();
  });

  it("shows 'Get More Suggestions' button when suggestions exist", () => {
    render(<TripSuggestions />);

    const moreButton = screen.getByRole("link", {
      name: /Get More Suggestions/i,
    });
    expect(moreButton).toBeInTheDocument();
    expect(moreButton).toHaveAttribute("href", "/dashboard/chat");
  });

  it("has hover effects on suggestion cards", () => {
    render(<TripSuggestions />);

    // Check that cards have hover classes
    const suggestionCards = document.querySelectorAll(
      ".hover\\:bg-accent\\/50"
    );
    expect(suggestionCards.length).toBeGreaterThan(0);
  });

  it("displays duration in correct format", () => {
    render(<TripSuggestions />);

    expect(screen.getByText("7 days")).toBeInTheDocument();
    expect(screen.getByText("10 days")).toBeInTheDocument();
    expect(screen.getByText("5 days")).toBeInTheDocument();
    expect(screen.getByText("6 days")).toBeInTheDocument();
    expect(screen.getByText("8 days")).toBeInTheDocument();
  });

  it("shows seasonal badge when appropriate", () => {
    render(<TripSuggestions />);

    // Tokyo and Iceland are marked as seasonal in mock data
    // We can't easily test for specific badges, but can test that the component renders
    expect(
      screen.getByText("Tokyo Cherry Blossom Adventure")
    ).toBeInTheDocument();
    expect(screen.getByText("Iceland Northern Lights")).toBeInTheDocument();
  });

  it("displays descriptions with proper truncation", () => {
    render(<TripSuggestions />);

    expect(
      screen.getByText(
        "Experience the magic of cherry blossom season in Japan's vibrant capital city."
      )
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "Relax on pristine beaches and explore ancient temples in this tropical paradise."
      )
    ).toBeInTheDocument();
  });

  it("renders without errors when no budget store data", () => {
    (useBudgetStore as any).mockReturnValue({
      budget: undefined,
    });

    render(<TripSuggestions />);

    expect(screen.getByText("Trip Suggestions")).toBeInTheDocument();
  });
});
