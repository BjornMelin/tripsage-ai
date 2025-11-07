import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { render } from "@/test/test-utils";
import {
  ChatMessageSkeleton,
  DestinationSkeleton,
  FlightSkeleton,
  HotelSkeleton,
  ItineraryItemSkeleton,
  SearchFilterSkeleton,
  TripSkeleton,
} from "../travel-skeletons";

describe("FlightSkeleton", () => {
  it("renders flight search result skeleton", () => {
    render(<FlightSkeleton />);
    expect(screen.getByText("Loading flight results")).toBeInTheDocument();
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
    render(<HotelSkeleton />);
    expect(screen.getByText("Loading hotel results")).toBeInTheDocument();
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
    render(<TripSkeleton />);
    expect(screen.getByText("Loading trip information")).toBeInTheDocument();
  });

  it("includes image and trip details", () => {
    const { container } = render(<TripSkeleton />);

    // Should have image skeleton(s) via CardSkeleton rendering
    const imageSkeletons = container.querySelectorAll(".skeleton");
    expect(imageSkeletons.length).toBeGreaterThan(0);

    // Should have multiple detail skeletons
    const detailSkeletons = container.querySelectorAll("[class*='animate-pulse']");
    expect(detailSkeletons.length).toBeGreaterThan(5);
  });
});

describe("DestinationSkeleton", () => {
  it("renders destination card skeleton", () => {
    render(<DestinationSkeleton />);
    expect(screen.getByText("Loading destination information")).toBeInTheDocument();
  });

  it("includes image and destination details", () => {
    const { container } = render(<DestinationSkeleton />);

    // Should have image skeleton(s) within header area
    const imageSkeletons = container.querySelectorAll(".relative .skeleton");
    expect(imageSkeletons.length).toBeGreaterThan(0);

    // Should have tags/category skeletons
    const tagSkeletons = container.querySelectorAll("[class*='rounded-full']");
    expect(tagSkeletons.length).toBeGreaterThan(0);
  });
});

describe("ItineraryItemSkeleton", () => {
  it("renders itinerary item skeleton", () => {
    render(<ItineraryItemSkeleton />);
    expect(screen.getByText("Loading itinerary item")).toBeInTheDocument();
  });

  it("has timeline structure", () => {
    const { container } = render(<ItineraryItemSkeleton />);

    // Should have time indicator skeleton
    const timeSkeletons = container.querySelectorAll("[class*='rounded-full']");
    expect(timeSkeletons.length).toBeGreaterThan(0);

    // Should have content skeletons
    const contentSkeletons = container.querySelectorAll("[class*='animate-pulse']");
    expect(contentSkeletons.length).toBeGreaterThan(3);
  });
});

describe("ChatMessageSkeleton", () => {
  it("renders chat message skeleton", () => {
    render(<ChatMessageSkeleton />);
    expect(screen.getByText("Loading chat message")).toBeInTheDocument();
  });

  it("renders user message layout", () => {
    render(<ChatMessageSkeleton isUser={true} data-testid="user-message" />);

    const message = screen.getByTestId("user-message");
    expect(message).toHaveClass("justify-end");
  });

  it("renders assistant message layout", () => {
    render(<ChatMessageSkeleton isUser={false} data-testid="assistant-message" />);

    const message = screen.getByTestId("assistant-message");
    expect(message).toHaveClass("justify-start");
  });

  it("includes avatar skeleton", () => {
    const { container } = render(<ChatMessageSkeleton />);

    // Should have avatar skeleton
    const avatarSkeletons = container.querySelectorAll("[class*='rounded-full']");
    expect(avatarSkeletons.length).toBeGreaterThan(0);
  });
});

describe("SearchFilterSkeleton", () => {
  it("renders search filter skeleton", () => {
    render(<SearchFilterSkeleton />);
    expect(screen.getByText("Loading search filters")).toBeInTheDocument();
  });

  it("has filter section structure", () => {
    const { container } = render(<SearchFilterSkeleton />);

    // Should have multiple filter sections
    const skeletons = container.querySelectorAll("[class*='animate-pulse']");
    expect(skeletons.length).toBeGreaterThan(10); // Multiple sections with multiple items each
  });

  it("includes checkbox-style filter items", () => {
    const { container } = render(<SearchFilterSkeleton />);
    // Validate presence of multiple skeleton lines for options
    const optionSkeletons = container.querySelectorAll(".skeleton");
    expect(optionSkeletons.length).toBeGreaterThan(0);
  });
});
