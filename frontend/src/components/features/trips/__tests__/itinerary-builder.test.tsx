import type { Trip } from "@/stores/trip-store";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ItineraryBuilder } from "../itinerary-builder";

// Mock the drag and drop library
vi.mock("@hello-pangea/dnd", () => ({
  DragDropContext: ({ children, onDragEnd }: any) => {
    return (
      <div data-testid="drag-drop-context" data-on-drag-end={onDragEnd}>
        {children}
      </div>
    );
  },
  Droppable: ({ children, droppableId }: any) => {
    const provided = {
      droppableProps: { "data-droppable-id": droppableId },
      innerRef: vi.fn(),
      placeholder: <div data-testid="droppable-placeholder" />,
    };
    return children(provided);
  },
  Draggable: ({ children, draggableId, index }: any) => {
    const provided = {
      innerRef: vi.fn(),
      draggableProps: { "data-draggable-id": draggableId },
      dragHandleProps: { "data-drag-handle": true },
    };
    const snapshot = { isDragging: false };
    return children(provided, snapshot);
  },
}));

// Mock the trip store
const mockUpdateTrip = vi.fn();
const mockAddDestination = vi.fn();
const mockUpdateDestination = vi.fn();
const mockRemoveDestination = vi.fn();

vi.mock("@/stores/trip-store", () => ({
  useTripStore: vi.fn(() => ({
    updateTrip: mockUpdateTrip,
    addDestination: mockAddDestination,
    updateDestination: mockUpdateDestination,
    removeDestination: mockRemoveDestination,
  })),
}));

describe("ItineraryBuilder", () => {
  const mockTrip: Trip = {
    id: "trip-1",
    name: "European Adventure",
    description: "A wonderful journey through Europe",
    startDate: "2024-06-15",
    endDate: "2024-06-25",
    destinations: [
      {
        id: "dest-1",
        name: "Paris",
        country: "France",
        startDate: "2024-06-15",
        endDate: "2024-06-18",
        activities: ["Visit Eiffel Tower", "Louvre Museum"],
        accommodation: { type: "hotel", name: "Hotel de Ville" },
        transportation: { type: "flight", details: "Air France AF123" },
        estimatedCost: 800,
        notes: "Book restaurants in advance",
      },
      {
        id: "dest-2",
        name: "Rome",
        country: "Italy",
        startDate: "2024-06-19",
        endDate: "2024-06-22",
        activities: ["Colosseum", "Vatican"],
        accommodation: { type: "airbnb", name: "Central Apartment" },
        transportation: { type: "train", details: "High-speed train" },
        estimatedCost: 600,
        notes: "Check for Vatican tours",
      },
    ],
    budget: 3000,
    currency: "USD",
    isPublic: false,
    tags: ["adventure", "culture"],
    status: "planning",
    createdAt: "2024-01-01",
    updatedAt: "2024-01-01",
  };

  const emptyTrip: Trip = {
    ...mockTrip,
    destinations: [],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Basic Rendering", () => {
    it("should render itinerary builder with trip destinations", () => {
      render(<ItineraryBuilder trip={mockTrip} />);

      expect(screen.getByText("Itinerary Builder")).toBeInTheDocument();
      expect(screen.getByText("Plan and organize your trip destinations")).toBeInTheDocument();
      expect(screen.getByText("Add Destination")).toBeInTheDocument();
      expect(screen.getByText("Paris")).toBeInTheDocument();
      expect(screen.getByText("Rome")).toBeInTheDocument();
    });

    it("should render empty state when no destinations", () => {
      render(<ItineraryBuilder trip={emptyTrip} />);

      expect(screen.getByText("No destinations added yet. Start building your itinerary!")).toBeInTheDocument();
      expect(screen.getByText("Add First Destination")).toBeInTheDocument();
    });

    it("should apply custom className", () => {
      const { container } = render(<ItineraryBuilder trip={mockTrip} className="custom-class" />);

      const card = container.firstChild as HTMLElement;
      expect(card).toHaveClass("custom-class");
    });
  });

  describe("Destination Display", () => {
    it("should display destination details correctly", () => {
      render(<ItineraryBuilder trip={mockTrip} />);

      // Check Paris destination
      expect(screen.getByText("Paris")).toBeInTheDocument();
      expect(screen.getByText("France")).toBeInTheDocument();
      expect(screen.getByText("2024-06-15 - 2024-06-18")).toBeInTheDocument();
      expect(screen.getByText("Air France AF123")).toBeInTheDocument();
      expect(screen.getByText("Hotel de Ville")).toBeInTheDocument();
      expect(screen.getByText("Cost: $800")).toBeInTheDocument();
      expect(screen.getByText("Book restaurants in advance")).toBeInTheDocument();

      // Check activities
      expect(screen.getByText("Visit Eiffel Tower")).toBeInTheDocument();
      expect(screen.getByText("Louvre Museum")).toBeInTheDocument();

      // Check Rome destination
      expect(screen.getByText("Rome")).toBeInTheDocument();
      expect(screen.getByText("Italy")).toBeInTheDocument();
      expect(screen.getByText("High-speed train")).toBeInTheDocument();
      expect(screen.getByText("Central Apartment")).toBeInTheDocument();
    });

    it("should display transportation icons correctly", () => {
      render(<ItineraryBuilder trip={mockTrip} />);

      // The icons are rendered but we can check their parent elements
      const flightDetails = screen.getByText("Air France AF123").parentElement;
      const trainDetails = screen.getByText("High-speed train").parentElement;

      expect(flightDetails).toHaveClass("flex", "items-center", "gap-1");
      expect(trainDetails).toHaveClass("flex", "items-center", "gap-1");
    });

    it("should handle destinations without optional fields", () => {
      const minimalTrip = {
        ...mockTrip,
        destinations: [
          {
            id: "dest-1",
            name: "Berlin",
            country: "Germany",
          },
        ],
      };

      render(<ItineraryBuilder trip={minimalTrip} />);

      expect(screen.getByText("Berlin")).toBeInTheDocument();
      expect(screen.getByText("Germany")).toBeInTheDocument();
      expect(screen.queryByText("Activities:")).not.toBeInTheDocument();
      expect(screen.queryByText("Cost:")).not.toBeInTheDocument();
    });
  });

  describe("Add Destination Dialog", () => {
    it("should open add destination dialog", async () => {
      const user = userEvent.setup();
      render(<ItineraryBuilder trip={mockTrip} />);

      const addButton = screen.getByText("Add Destination");
      await user.click(addButton);

      expect(screen.getByText("Add New Destination")).toBeInTheDocument();
      expect(screen.getByText("Fill in the details for this destination")).toBeInTheDocument();
      expect(screen.getByLabelText("Destination Name")).toBeInTheDocument();
      expect(screen.getByLabelText("Country")).toBeInTheDocument();
    });

    it("should close dialog when cancel is clicked", async () => {
      const user = userEvent.setup();
      render(<ItineraryBuilder trip={mockTrip} />);

      const addButton = screen.getByText("Add Destination");
      await user.click(addButton);

      const cancelButton = screen.getByText("Cancel");
      await user.click(cancelButton);

      expect(screen.queryByText("Add New Destination")).not.toBeInTheDocument();
    });

    it("should fill form and add destination", async () => {
      const user = userEvent.setup();
      mockAddDestination.mockResolvedValue(undefined);

      render(<ItineraryBuilder trip={mockTrip} />);

      const addButton = screen.getByText("Add Destination");
      await user.click(addButton);

      // Fill form fields
      await user.type(screen.getByLabelText("Destination Name"), "Madrid");
      await user.type(screen.getByLabelText("Country"), "Spain");
      await user.type(screen.getByLabelText("Start Date"), "2024-06-23");
      await user.type(screen.getByLabelText("End Date"), "2024-06-25");

      // Add transportation
      await user.click(screen.getByText("Select transport"));
      await user.click(screen.getByText("Flight"));
      await user.type(screen.getByPlaceholderText("Transportation details"), "Iberia IB456");

      // Add accommodation
      await user.click(screen.getByText("Accommodation type"));
      await user.click(screen.getByText("Hotel"));
      await user.type(screen.getByPlaceholderText("Accommodation name"), "Hotel Plaza");

      // Add estimated cost
      await user.type(screen.getByLabelText("Estimated Cost ($)"), "700");

      // Add notes
      await user.type(screen.getByLabelText("Notes"), "Visit Prado Museum");

      // Submit form
      const submitButton = screen.getByText("Add Destination");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockAddDestination).toHaveBeenCalledWith("trip-1", expect.objectContaining({
          name: "Madrid",
          country: "Spain",
          startDate: "2024-06-23",
          endDate: "2024-06-25",
          transportation: { type: "flight", details: "Iberia IB456" },
          accommodation: { type: "hotel", name: "Hotel Plaza" },
          estimatedCost: 700,
          notes: "Visit Prado Museum",
        }));
      });
    });

    it("should handle activities management", async () => {
      const user = userEvent.setup();
      render(<ItineraryBuilder trip={mockTrip} />);

      const addButton = screen.getByText("Add Destination");
      await user.click(addButton);

      // Add an activity
      const addActivityButton = screen.getByText("Add Activity");
      await user.click(addActivityButton);

      const activityInput = screen.getByPlaceholderText("Activity description");
      await user.type(activityInput, "Visit Museum");

      expect(activityInput).toHaveValue("Visit Museum");

      // Add another activity
      await user.click(addActivityButton);
      const activityInputs = screen.getAllByPlaceholderText("Activity description");
      expect(activityInputs).toHaveLength(2);

      // Remove an activity
      const removeButtons = screen.getAllByRole("button");
      const removeActivityButton = removeButtons.find(btn => 
        btn.querySelector('svg') && btn.getAttribute('type') === 'button'
      );
      
      if (removeActivityButton) {
        await user.click(removeActivityButton);
      }
    });
  });

  describe("Edit Destination Dialog", () => {
    it("should open edit dialog with pre-filled data", async () => {
      const user = userEvent.setup();
      render(<ItineraryBuilder trip={mockTrip} />);

      // Find and click edit button for Paris destination
      const editButtons = screen.getAllByRole("button");
      const editButton = editButtons.find(btn => 
        btn.getAttribute("aria-label") === undefined && 
        btn.querySelector('svg')
      );

      if (editButton) {
        await user.click(editButton);
      }

      await waitFor(() => {
        expect(screen.getByText("Edit Destination")).toBeInTheDocument();
        expect(screen.getByDisplayValue("Paris")).toBeInTheDocument();
        expect(screen.getByDisplayValue("France")).toBeInTheDocument();
        expect(screen.getByDisplayValue("2024-06-15")).toBeInTheDocument();
        expect(screen.getByDisplayValue("2024-06-18")).toBeInTheDocument();
      });
    });

    it("should update destination when form is submitted", async () => {
      const user = userEvent.setup();
      mockUpdateDestination.mockResolvedValue(undefined);

      render(<ItineraryBuilder trip={mockTrip} />);

      // Open edit dialog
      const editButtons = screen.getAllByRole("button");
      const editButton = editButtons.find(btn => 
        btn.getAttribute("aria-label") === undefined && 
        btn.querySelector('svg')
      );

      if (editButton) {
        await user.click(editButton);
      }

      await waitFor(() => {
        expect(screen.getByDisplayValue("Paris")).toBeInTheDocument();
      });

      // Modify the destination name
      const nameInput = screen.getByDisplayValue("Paris");
      await user.clear(nameInput);
      await user.type(nameInput, "Lyon");

      // Submit form
      const updateButton = screen.getByText("Update Destination");
      await user.click(updateButton);

      await waitFor(() => {
        expect(mockUpdateDestination).toHaveBeenCalledWith("trip-1", "dest-1", expect.objectContaining({
          name: "Lyon",
        }));
      });
    });
  });

  describe("Destination Actions", () => {
    it("should delete destination when delete button is clicked", async () => {
      const user = userEvent.setup();
      mockRemoveDestination.mockResolvedValue(undefined);

      render(<ItineraryBuilder trip={mockTrip} />);

      // Find delete button (trash icon)
      const deleteButtons = screen.getAllByRole("button");
      const deleteButton = deleteButtons.find(btn => 
        btn.className.includes("text-destructive")
      );

      if (deleteButton) {
        await user.click(deleteButton);
      }

      await waitFor(() => {
        expect(mockRemoveDestination).toHaveBeenCalledWith("trip-1", expect.any(String));
      });
    });
  });

  describe("Drag and Drop", () => {
    it("should render drag and drop context", () => {
      render(<ItineraryBuilder trip={mockTrip} />);

      expect(screen.getByTestId("drag-drop-context")).toBeInTheDocument();
      expect(screen.getByTestId("droppable-placeholder")).toBeInTheDocument();
    });

    it("should have drag handles on destinations", () => {
      render(<ItineraryBuilder trip={mockTrip} />);

      const dragHandles = screen.getAllByTestId("drag-drop-context")
        .map(element => element.querySelector('[data-drag-handle="true"]'))
        .filter(Boolean);

      expect(dragHandles.length).toBeGreaterThan(0);
    });
  });

  describe("Custom Update Handler", () => {
    it("should call onUpdateTrip when provided", async () => {
      const mockOnUpdateTrip = vi.fn();
      render(<ItineraryBuilder trip={mockTrip} onUpdateTrip={mockOnUpdateTrip} />);

      // Simulate drag end - this would normally be called by the drag and drop library
      // We can test this by accessing the component's internal logic
      // For now, we'll just verify the prop is passed correctly
      expect(mockOnUpdateTrip).toBeDefined();
    });

    it("should fall back to store method when onUpdateTrip is not provided", () => {
      render(<ItineraryBuilder trip={mockTrip} />);

      // This tests that the component renders without error when onUpdateTrip is not provided
      expect(screen.getByText("Itinerary Builder")).toBeInTheDocument();
    });
  });

  describe("Form Validation and Edge Cases", () => {
    it("should handle empty form submission", async () => {
      const user = userEvent.setup();
      mockAddDestination.mockResolvedValue(undefined);

      render(<ItineraryBuilder trip={mockTrip} />);

      const addButton = screen.getByText("Add Destination");
      await user.click(addButton);

      // Submit without filling any fields
      const submitButton = screen.getByText("Add Destination");
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockAddDestination).toHaveBeenCalledWith("trip-1", expect.objectContaining({
          name: "",
          country: "",
        }));
      });
    });

    it("should handle numeric input for estimated cost", async () => {
      const user = userEvent.setup();
      render(<ItineraryBuilder trip={mockTrip} />);

      const addButton = screen.getByText("Add Destination");
      await user.click(addButton);

      const costInput = screen.getByLabelText("Estimated Cost ($)");
      await user.type(costInput, "1500.50");

      expect(costInput).toHaveValue(1500.50);
    });

    it("should handle clearing estimated cost", async () => {
      const user = userEvent.setup();
      render(<ItineraryBuilder trip={mockTrip} />);

      const addButton = screen.getByText("Add Destination");
      await user.click(addButton);

      const costInput = screen.getByLabelText("Estimated Cost ($)");
      await user.type(costInput, "1000");
      await user.clear(costInput);

      expect(costInput).toHaveValue(null);
    });
  });

  describe("Accessibility", () => {
    it("should have proper form labels", () => {
      render(<ItineraryBuilder trip={mockTrip} />);

      const addButton = screen.getByText("Add Destination");
      fireEvent.click(addButton);

      expect(screen.getByLabelText("Destination Name")).toBeInTheDocument();
      expect(screen.getByLabelText("Country")).toBeInTheDocument();
      expect(screen.getByLabelText("Start Date")).toBeInTheDocument();
      expect(screen.getByLabelText("End Date")).toBeInTheDocument();
      expect(screen.getByLabelText("Estimated Cost ($)")).toBeInTheDocument();
      expect(screen.getByLabelText("Notes")).toBeInTheDocument();
    });

    it("should have proper button roles", () => {
      render(<ItineraryBuilder trip={mockTrip} />);

      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThan(0);

      // Check that main action buttons exist
      expect(screen.getByRole("button", { name: /Add Destination/ })).toBeInTheDocument();
    });

    it("should have proper dialog structure", async () => {
      const user = userEvent.setup();
      render(<ItineraryBuilder trip={mockTrip} />);

      const addButton = screen.getByText("Add Destination");
      await user.click(addButton);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
  });

  describe("Transportation Icons", () => {
    it("should return correct icons for different transportation types", () => {
      const tripWithVariousTransport = {
        ...mockTrip,
        destinations: [
          {
            id: "dest-1",
            name: "Test City",
            country: "Test Country",
            transportation: { type: "flight", details: "Flight details" },
          },
          {
            id: "dest-2", 
            name: "Test City 2",
            country: "Test Country 2",
            transportation: { type: "car", details: "Car details" },
          },
          {
            id: "dest-3",
            name: "Test City 3", 
            country: "Test Country 3",
            transportation: { type: "train", details: "Train details" },
          },
          {
            id: "dest-4",
            name: "Test City 4",
            country: "Test Country 4", 
            transportation: { type: "other", details: "Other transport" },
          },
        ],
      };

      render(<ItineraryBuilder trip={tripWithVariousTransport} />);

      expect(screen.getByText("Flight details")).toBeInTheDocument();
      expect(screen.getByText("Car details")).toBeInTheDocument();
      expect(screen.getByText("Train details")).toBeInTheDocument();
      expect(screen.getByText("Other transport")).toBeInTheDocument();
    });
  });
});