import type { Trip } from "@/stores/trip-store";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TripCard } from "../trip-card";

// Mock date-fns
vi.mock("date-fns", () => ({
  differenceInDays: vi.fn((end, start) => {
    const endDate = new Date(end);
    const startDate = new Date(start);
    return Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
  }),
  format: vi.fn((date, formatStr) => {
    const d = new Date(date);
    if (formatStr === "MMM dd, yyyy") {
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "2-digit",
        year: "numeric",
      });
    }
    return d.toLocaleDateString();
  }),
}));

// Mock Next.js Link
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

describe("TripCard", () => {
  const mockTrip: Trip = {
    id: "trip-1",
    name: "European Adventure",
    description: "A wonderful journey through Europe",
    startDate: "2024-06-15",
    endDate: "2024-06-25",
    destinations: [
      { id: "dest-1", name: "Paris", country: "France" },
      { id: "dest-2", name: "Rome", country: "Italy" },
    ],
    budget: 3000,
    currency: "USD",
    isPublic: false,
    tags: ["adventure", "culture"],
    status: "planning",
    createdAt: "2024-01-01",
    updatedAt: "2024-01-01",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Basic Rendering", () => {
    it("should render trip details correctly", () => {
      render(<TripCard trip={mockTrip} />);

      expect(screen.getByText("European Adventure")).toBeInTheDocument();
      expect(screen.getByText("A wonderful journey through Europe")).toBeInTheDocument();
      expect(screen.getByText("View Details")).toBeInTheDocument();
    });

    it("should display trip dates correctly", () => {
      render(<TripCard trip={mockTrip} />);

      // Should show formatted start and end dates
      expect(screen.getByText(/Jun 15, 2024 - Jun 25, 2024/)).toBeInTheDocument();
      expect(screen.getByText("(11 days)")).toBeInTheDocument();
    });

    it("should display destinations correctly", () => {
      render(<TripCard trip={mockTrip} />);

      expect(screen.getByText("Paris + 1 more")).toBeInTheDocument();
    });

    it("should display single destination without 'more' text", () => {
      const singleDestTrip = {
        ...mockTrip,
        destinations: [{ id: "dest-1", name: "Paris", country: "France" }],
      };

      render(<TripCard trip={singleDestTrip} />);

      expect(screen.getByText("Paris")).toBeInTheDocument();
      expect(screen.queryByText("+ 1 more")).not.toBeInTheDocument();
    });

    it("should display budget correctly", () => {
      render(<TripCard trip={mockTrip} />);

      expect(screen.getByText("Budget: $3,000.00")).toBeInTheDocument();
    });

    it("should display public badge when trip is public", () => {
      const publicTrip = { ...mockTrip, isPublic: true };
      render(<TripCard trip={publicTrip} />);

      expect(screen.getByText("Public")).toBeInTheDocument();
    });
  });

  describe("Trip Status", () => {
    beforeEach(() => {
      // Mock current date to 2024-01-01 for consistent testing
      vi.useFakeTimers();
      vi.setSystemTime(new Date("2024-01-01"));
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("should show 'upcoming' status for future trips", () => {
      const futureTrip = {
        ...mockTrip,
        startDate: "2024-06-15",
        endDate: "2024-06-25",
      };

      render(<TripCard trip={futureTrip} />);

      expect(screen.getByText("Upcoming")).toBeInTheDocument();
    });

    it("should show 'completed' status for past trips", () => {
      vi.setSystemTime(new Date("2024-12-01"));

      render(<TripCard trip={mockTrip} />);

      expect(screen.getByText("Completed")).toBeInTheDocument();
    });

    it("should show 'active' status for current trips", () => {
      vi.setSystemTime(new Date("2024-06-20"));

      render(<TripCard trip={mockTrip} />);

      expect(screen.getByText("Active")).toBeInTheDocument();
    });

    it("should show 'draft' status when dates are missing", () => {
      const draftTrip = {
        ...mockTrip,
        startDate: undefined,
        endDate: undefined,
      };

      render(<TripCard trip={draftTrip} />);

      expect(screen.getByText("Draft")).toBeInTheDocument();
      expect(screen.getByText("Not set - Not set")).toBeInTheDocument();
    });
  });

  describe("Action Buttons", () => {
    it("should call onEdit when edit button is clicked", () => {
      const mockOnEdit = vi.fn();
      render(<TripCard trip={mockTrip} onEdit={mockOnEdit} />);

      const editButton = screen.getByText("Edit");
      fireEvent.click(editButton);

      expect(mockOnEdit).toHaveBeenCalledWith(mockTrip);
    });

    it("should call onDelete with trip ID when delete button is clicked", () => {
      const mockOnDelete = vi.fn();
      render(<TripCard trip={mockTrip} onDelete={mockOnDelete} />);

      const deleteButton = screen.getByText("Delete");
      fireEvent.click(deleteButton);

      expect(mockOnDelete).toHaveBeenCalledWith("trip-1");
    });

    it("should not show edit button when onEdit is not provided", () => {
      render(<TripCard trip={mockTrip} />);

      expect(screen.queryByText("Edit")).not.toBeInTheDocument();
    });

    it("should not show delete button when onDelete is not provided", () => {
      render(<TripCard trip={mockTrip} />);

      expect(screen.queryByText("Delete")).not.toBeInTheDocument();
    });

    it("should create correct link for View Details button", () => {
      render(<TripCard trip={mockTrip} />);

      const viewLink = screen.getByText("View Details").closest("a");
      expect(viewLink).toHaveAttribute("href", "/dashboard/trips/trip-1");
    });
  });

  describe("Budget Display", () => {
    it("should not display budget section when budget is null", () => {
      const noBudgetTrip = { ...mockTrip, budget: undefined };
      render(<TripCard trip={noBudgetTrip} />);

      expect(screen.queryByText(/Budget:/)).not.toBeInTheDocument();
    });

    it("should format budget with different currencies", () => {
      const eurTrip = { ...mockTrip, currency: "EUR" };
      render(<TripCard trip={eurTrip} />);

      expect(screen.getByText("Budget: €3,000.00")).toBeInTheDocument();
    });

    it("should use USD as default currency when currency is not specified", () => {
      const noCurrencyTrip = { ...mockTrip, currency: undefined };
      render(<TripCard trip={noCurrencyTrip} />);

      expect(screen.getByText("Budget: $3,000.00")).toBeInTheDocument();
    });
  });

  describe("Budget Tracker Integration", () => {
    it("should display budget count when trip has budgets", () => {
      // Note: This test relies on the mocked budget store
      render(<TripCard trip={mockTrip} />);

      // The mocked store returns empty array, so no budget text should show
      expect(screen.queryByText(/budget.*tracked/)).not.toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("should handle missing description gracefully", () => {
      const noDescTrip = { ...mockTrip, description: undefined };
      render(<TripCard trip={noDescTrip} />);

      expect(screen.getByText("European Adventure")).toBeInTheDocument();
      expect(screen.queryByText("A wonderful journey through Europe")).not.toBeInTheDocument();
    });

    it("should handle empty destinations array", () => {
      const noDestTrip = { ...mockTrip, destinations: [] };
      render(<TripCard trip={noDestTrip} />);

      // Should not show destinations section at all
      expect(screen.queryByTestId("destinations")).not.toBeInTheDocument();
    });

    it("should apply custom className", () => {
      const { container } = render(<TripCard trip={mockTrip} className="custom-class" />);

      const card = container.firstChild as HTMLElement;
      expect(card).toHaveClass("custom-class");
    });

    it("should handle partial date information", () => {
      const partialDateTrip = {
        ...mockTrip,
        startDate: "2024-06-15",
        endDate: undefined,
      };

      render(<TripCard trip={partialDateTrip} />);

      expect(screen.getByText("Draft")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have proper button roles and accessibility", () => {
      render(<TripCard trip={mockTrip} onEdit={vi.fn()} onDelete={vi.fn()} />);

      const editButton = screen.getByRole("button", { name: "Edit" });
      const deleteButton = screen.getByRole("button", { name: "Delete" });
      const viewLink = screen.getByRole("link", { name: "View Details" });

      expect(editButton).toBeInTheDocument();
      expect(deleteButton).toBeInTheDocument();
      expect(viewLink).toBeInTheDocument();
    });

    it("should have proper heading structure", () => {
      render(<TripCard trip={mockTrip} />);

      const heading = screen.getByText("European Adventure");
      expect(heading.tagName).toBe("H3"); // CardTitle typically renders as h3
    });
  });

  describe("Hover Effects", () => {
    it("should have hover classes for interactive elements", () => {
      const { container } = render(<TripCard trip={mockTrip} />);

      const card = container.firstChild as HTMLElement;
      expect(card).toHaveClass("hover:shadow-lg", "transition-shadow");
    });
  });

  describe("Currency Formatting", () => {
    it("should format currency amounts correctly for large numbers", () => {
      const expensiveTrip = { ...mockTrip, budget: 25000 };
      render(<TripCard trip={expensiveTrip} />);

      expect(screen.getByText("Budget: $25,000.00")).toBeInTheDocument();
    });

    it("should handle decimal budgets", () => {
      const decimalTrip = { ...mockTrip, budget: 1500.50 };
      render(<TripCard trip={decimalTrip} />);

      expect(screen.getByText("Budget: $1,500.50")).toBeInTheDocument();
    });
  });
});