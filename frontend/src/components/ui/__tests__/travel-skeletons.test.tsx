import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import {
  FlightSkeleton,
  HotelSkeleton,
  TripSkeleton,
  DestinationSkeleton,
  ItineraryItemSkeleton,
  ChatMessageSkeleton,
  SearchFilterSkeleton,
} from "../travel-skeletons";

describe("FlightSkeleton", () => {
  it("renders flight search result skeleton", () => {
    render(<FlightSkeleton data-testid="flight" />);

    const flight = screen.getByTestId("flight");
    expect(flight).toBeInTheDocument();
    expect(flight).toHaveAttribute("aria-label", "Loading flight results");
  });

  it("has appropriate structure", () => {
    const { container } = render(<FlightSkeleton />);

    // Should have multiple skeleton elements for flight details
    const skeletons = container.querySelectorAll("[class*='animate-pulse']");
    expect(skeletons.length).toBeGreaterThan(5);
  });

  it("applies custom className", () => {
    render(<FlightSkeleton className="custom-flight" data-testid="flight" />);

    const flight = screen.getByTestId("flight");
    expect(flight).toHaveClass("custom-flight");
  });
});

describe("HotelSkeleton", () => {
  it("renders hotel search result skeleton", () => {
    render(<HotelSkeleton data-testid="hotel" />);

    const hotel = screen.getByTestId("hotel");
    expect(hotel).toBeInTheDocument();
    expect(hotel).toHaveAttribute("aria-label", "Loading hotel results");
  });

  it("includes image skeleton", () => {
    const { container } = render(<HotelSkeleton />);

    // Should have image skeleton
    const imageSkeletons = container.querySelectorAll(
      "[class*='h-48'], [height='200px']"
    );
    expect(imageSkeletons.length).toBeGreaterThan(0);
  });

  it("includes rating and amenity skeletons", () => {
    const { container } = render(<HotelSkeleton />);

    // Should have multiple skeleton elements for various hotel details
    const skeletons = container.querySelectorAll("[class*='animate-pulse']");
    expect(skeletons.length).toBeGreaterThan(10);
  });
});

describe("TripSkeleton", () => {
  it("renders trip card skeleton", () => {
    render(<TripSkeleton data-testid="trip" />);

    const trip = screen.getByTestId("trip");
    expect(trip).toBeInTheDocument();
    expect(trip).toHaveAttribute("aria-label", "Loading trip information");
  });

  it("includes image and trip details", () => {
    const { container } = render(<TripSkeleton />);

    // Should have image skeleton
    const imageSkeletons = container.querySelectorAll(
      "[class*='h-40'], [height='160px']"
    );
    expect(imageSkeletons.length).toBeGreaterThan(0);

    // Should have multiple detail skeletons
    const detailSkeletons = container.querySelectorAll(
      "[class*='animate-pulse']"
    );
    expect(detailSkeletons.length).toBeGreaterThan(5);
  });
});

describe("DestinationSkeleton", () => {
  it("renders destination card skeleton", () => {
    render(<DestinationSkeleton data-testid="destination" />);

    const destination = screen.getByTestId("destination");
    expect(destination).toBeInTheDocument();
    expect(destination).toHaveAttribute(
      "aria-label",
      "Loading destination information"
    );
  });

  it("includes image and destination details", () => {
    const { container } = render(<DestinationSkeleton />);

    // Should have image skeleton
    const imageSkeletons = container.querySelectorAll("[height='200px']");
    expect(imageSkeletons.length).toBeGreaterThan(0);

    // Should have tags/category skeletons
    const tagSkeletons = container.querySelectorAll("[class*='rounded-full']");
    expect(tagSkeletons.length).toBeGreaterThan(0);
  });
});

describe("ItineraryItemSkeleton", () => {
  it("renders itinerary item skeleton", () => {
    render(<ItineraryItemSkeleton data-testid="itinerary-item" />);

    const item = screen.getByTestId("itinerary-item");
    expect(item).toBeInTheDocument();
    expect(item).toHaveAttribute("aria-label", "Loading itinerary item");
  });

  it("has timeline structure", () => {
    const { container } = render(<ItineraryItemSkeleton />);

    // Should have time indicator skeleton
    const timeSkeletons = container.querySelectorAll("[class*='rounded-full']");
    expect(timeSkeletons.length).toBeGreaterThan(0);

    // Should have content skeletons
    const contentSkeletons = container.querySelectorAll(
      "[class*='animate-pulse']"
    );
    expect(contentSkeletons.length).toBeGreaterThan(3);
  });
});

describe("ChatMessageSkeleton", () => {
  it("renders chat message skeleton", () => {
    render(<ChatMessageSkeleton data-testid="chat-message" />);

    const message = screen.getByTestId("chat-message");
    expect(message).toBeInTheDocument();
    expect(message).toHaveAttribute("aria-label", "Loading chat message");
  });

  it("renders user message layout", () => {
    render(<ChatMessageSkeleton isUser={true} data-testid="user-message" />);

    const message = screen.getByTestId("user-message");
    expect(message).toHaveClass("justify-end");
  });

  it("renders assistant message layout", () => {
    render(
      <ChatMessageSkeleton isUser={false} data-testid="assistant-message" />
    );

    const message = screen.getByTestId("assistant-message");
    expect(message).toHaveClass("justify-start");
  });

  it("includes avatar skeleton", () => {
    const { container } = render(<ChatMessageSkeleton />);

    // Should have avatar skeleton
    const avatarSkeletons = container.querySelectorAll(
      "[class*='rounded-full']"
    );
    expect(avatarSkeletons.length).toBeGreaterThan(0);
  });
});

describe("SearchFilterSkeleton", () => {
  it("renders search filter skeleton", () => {
    render(<SearchFilterSkeleton data-testid="search-filter" />);

    const filter = screen.getByTestId("search-filter");
    expect(filter).toBeInTheDocument();
    expect(filter).toHaveAttribute("aria-label", "Loading search filters");
  });

  it("has filter section structure", () => {
    const { container } = render(<SearchFilterSkeleton />);

    // Should have multiple filter sections
    const skeletons = container.querySelectorAll("[class*='animate-pulse']");
    expect(skeletons.length).toBeGreaterThan(10); // Multiple sections with multiple items each
  });

  it("includes checkbox-style filter items", () => {
    const { container } = render(<SearchFilterSkeleton />);

    // Should have small square skeletons for checkboxes
    const checkboxSkeletons = container.querySelectorAll(
      "[class*='h-4'][class*='w-4'], [class*='h-3'][class*='w-3']"
    );
    expect(checkboxSkeletons.length).toBeGreaterThan(0);
  });
});
