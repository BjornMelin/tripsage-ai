import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ActivityComparisonModal } from "./activity-comparison-modal";
import type { Activity } from "@schemas/search";

// Mock Lucide icons
vi.mock("lucide-react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("lucide-react")>();
  return {
    ...actual,
    MapPin: () => <div data-testid="map-pin-icon" />,
    Star: () => <div data-testid="star-icon" />,
    X: () => <div data-testid="x-icon" />,
  };
});

// Mock Next.js Image
vi.mock("next/image", () => ({
  default: (props: any) => <img {...props} alt={props.alt} />,
}));

const mockActivities: Activity[] = [
  {
    id: "1",
    name: "Activity 1",
    description: "Description 1",
    location: "Location 1",
    price: 100,
    rating: 4.5,
    type: "tour",
    images: ["/image1.jpg"],
    duration: 120, // 2 hours in minutes
    coordinates: { lat: 0, lng: 0 },
    date: "2023-01-01T00:00:00Z",
  },
  {
    id: "2",
    name: "Activity 2",
    description: "Description 2",
    location: "Location 2",
    price: 50,
    rating: 4.0,
    type: "museum",
    images: [], // No image
    duration: 60, // 1 hour in minutes
    coordinates: { lat: 0, lng: 0 },
    date: "2023-01-01T00:00:00Z",
  },
];

describe("ActivityComparisonModal", () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    activities: mockActivities,
    onRemove: vi.fn(),
    onAddToTrip: vi.fn(),
  };

  it("should render nothing when activities list is empty", () => {
    const { container } = render(
      <ActivityComparisonModal {...defaultProps} activities={[]} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("should render comparison table with activities", () => {
    render(<ActivityComparisonModal {...defaultProps} />);

    expect(screen.getByText("Compare Activities")).toBeInTheDocument();
    expect(screen.getByText("Activity 1")).toBeInTheDocument();
    expect(screen.getByText("Activity 2")).toBeInTheDocument();
    
    // Check details
    expect(screen.getByText("$100.00")).toBeInTheDocument();
    expect(screen.getByText("$50.00")).toBeInTheDocument();
    expect(screen.getByText("Location 1")).toBeInTheDocument();
    expect(screen.getByText("tour")).toBeInTheDocument();
  });

  it("should handle remove action", () => {
    render(<ActivityComparisonModal {...defaultProps} />);

    const removeButtons = screen.getAllByLabelText(/Remove .* from comparison/);
    fireEvent.click(removeButtons[0]);

    expect(defaultProps.onRemove).toHaveBeenCalledWith("1");
  });

  it("should handle add to trip action", () => {
    render(<ActivityComparisonModal {...defaultProps} />);

    const addButtons = screen.getAllByText("Add to Trip");
    fireEvent.click(addButtons[0]);

    expect(defaultProps.onAddToTrip).toHaveBeenCalledWith(mockActivities[0]);
  });

  it("should render placeholder when no image is available", () => {
    render(<ActivityComparisonModal {...defaultProps} />);

    expect(screen.getByText("No image")).toBeInTheDocument();
  });
});
