/** @vitest-environment jsdom */

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, type AppError } from "@/lib/api/error-types";

if (!HTMLElement.prototype.hasPointerCapture) {
  HTMLElement.prototype.hasPointerCapture = () => false;
}

if (!HTMLElement.prototype.releasePointerCapture) {
  HTMLElement.prototype.releasePointerCapture = () => undefined;
}

if (!HTMLElement.prototype.scrollIntoView) {
  HTMLElement.prototype.scrollIntoView = () => undefined;
}

// Mock Lucide icons
vi.mock("lucide-react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("lucide-react")>();
  return {
    ...actual,
    FilterIcon: () => <span data-testid="filter-icon" />,
    GridIcon: () => <span data-testid="grid-icon" />,
    ListIcon: () => <span data-testid="list-icon" />,
    PlusIcon: () => <span data-testid="plus-icon" />,
    SearchIcon: () => <span data-testid="search-icon" />,
  };
});

// Mock trip data
interface MockTrip {
  id: string;
  title: string;
  description?: string;
  destinations: Array<{ name: string }>;
  budget?: number;
  startDate?: string;
  endDate?: string;
  createdAt: string;
  visibility: string;
}

const mockTrips = vi.hoisted(() => vi.fn((): MockTrip[] => []));
const mockIsLoading = vi.hoisted(() => vi.fn(() => false));
const mockError = vi.hoisted(() => vi.fn((): AppError | null => null));
const mockIsConnected = vi.hoisted(() => vi.fn(() => true));
const mockRealtimeStatus = vi.hoisted(() => vi.fn(() => "connected" as const));
const mockCreateTrip = vi.hoisted(() => vi.fn());
const mockDeleteTrip = vi.hoisted(() => vi.fn());

vi.mock("@/hooks/use-trips", () => ({
  useDeleteTrip: () => ({
    mutateAsync: mockDeleteTrip,
  }),
  useTrips: () => ({
    data: mockTrips(),
    error: mockError(),
    isConnected: mockIsConnected(),
    isLoading: mockIsLoading(),
    realtimeStatus: mockRealtimeStatus(),
  }),
}));

vi.mock("@/stores/trip-store", () => ({
  Trip: {},
  useTripStore: () => ({
    createTrip: mockCreateTrip,
  }),
}));

// Mock child components
vi.mock("@/components/features/realtime/connection-status-monitor", () => ({
  ConnectionStatusIndicator: () => <div data-testid="connection-status" />,
}));

vi.mock("@/components/features/trips", () => ({
  TripCard: ({
    trip,
    onDelete,
  }: {
    trip: MockTrip;
    onDelete: (id: string) => void;
  }) => (
    <div data-testid={`trip-card-${trip.id}`}>
      <span>{trip.title}</span>
      <button type="button" onClick={() => onDelete(trip.id)}>
        Delete
      </button>
    </div>
  ),
}));

import TripsPage from "../page";

describe("TripsPage", () => {
  beforeEach(() => {
    mockTrips.mockReset();
    mockIsLoading.mockReset();
    mockError.mockReset();
    mockIsConnected.mockReset();
    mockRealtimeStatus.mockReset();
    mockCreateTrip.mockReset();
    mockDeleteTrip.mockReset();
    mockTrips.mockReturnValue([]);
    mockIsLoading.mockReturnValue(false);
    mockError.mockReturnValue(null);
    mockIsConnected.mockReturnValue(true);
    mockRealtimeStatus.mockReturnValue("connected");
  });

  describe("Loading state", () => {
    it("renders loading skeleton when loading with no trips", () => {
      mockIsLoading.mockReturnValue(true);
      mockTrips.mockReturnValue([]);

      render(<TripsPage />);
      expect(screen.getByText("Loading your trips...")).toBeInTheDocument();
    });

    it("renders trips even when loading is true but data exists", () => {
      mockIsLoading.mockReturnValue(true);
      mockTrips.mockReturnValue([
        {
          createdAt: "2024-01-15T10:00:00Z",
          destinations: [{ name: "Paris" }],
          id: "trip-loaded",
          title: "Loaded Trip",
          visibility: "private",
        },
      ]);

      render(<TripsPage />);

      expect(screen.getByTestId("trip-card-trip-loaded")).toBeInTheDocument();
      expect(screen.queryByText("Loading your trips...")).not.toBeInTheDocument();
    });
  });

  describe("Empty state", () => {
    it("renders empty state when no trips exist", () => {
      mockTrips.mockReturnValue([]);
      mockIsLoading.mockReturnValue(false);

      render(<TripsPage />);
      expect(screen.getByText("No trips yet")).toBeInTheDocument();
      expect(
        screen.getByText(
          "Start planning your next adventure by creating your first trip"
        )
      ).toBeInTheDocument();
    });

    it("renders create first trip button in empty state", () => {
      mockTrips.mockReturnValue([]);

      render(<TripsPage />);
      expect(screen.getByText("Create Your First Trip")).toBeInTheDocument();
    });

    it("calls createTrip when empty state CTA is clicked", async () => {
      mockTrips.mockReturnValue([]);
      mockCreateTrip.mockResolvedValue({ id: "new-empty-trip" });

      render(<TripsPage />);
      fireEvent.click(screen.getByText("Create Your First Trip"));

      await waitFor(() => {
        expect(mockCreateTrip).toHaveBeenCalledTimes(1);
      });
    });
  });

  describe("Error state", () => {
    it("renders gracefully when an error occurs", () => {
      mockError.mockReturnValue(new ApiError("Failed to load trips", 500));
      mockTrips.mockReturnValue([]);

      render(<TripsPage />);

      expect(screen.getByText("My Trips")).toBeInTheDocument();
      expect(screen.getByText("No trips yet")).toBeInTheDocument();
    });

    it("renders connection indicator when realtime is disconnected", () => {
      mockTrips.mockReturnValue([
        {
          createdAt: "2024-01-10T10:00:00Z",
          destinations: [{ name: "Paris" }],
          id: "trip-connected",
          title: "Connected Trip",
          visibility: "private",
        },
      ]);
      mockIsConnected.mockReturnValue(false);
      mockRealtimeStatus.mockReturnValue("connected");

      render(<TripsPage />);

      expect(screen.getByTestId("connection-status")).toBeInTheDocument();
    });
  });

  describe("With trips", () => {
    const sampleTrips: MockTrip[] = [
      {
        budget: 5000,
        createdAt: "2024-01-15T10:00:00Z",
        description: "A romantic getaway",
        destinations: [{ name: "Paris" }],
        endDate: "2025-06-10",
        id: "trip-1",
        startDate: "2025-06-01",
        title: "Paris Vacation",
        visibility: "private",
      },
      {
        budget: 8000,
        createdAt: "2024-01-10T10:00:00Z",
        description: "Exploring Japan",
        destinations: [{ name: "Tokyo" }, { name: "Kyoto" }],
        endDate: "2025-07-25",
        id: "trip-2",
        startDate: "2025-07-15",
        title: "Tokyo Adventure",
        visibility: "private",
      },
    ];

    it("renders trips list with correct count", () => {
      mockTrips.mockReturnValue(sampleTrips);

      render(<TripsPage />);
      expect(screen.getByText("My Trips")).toBeInTheDocument();
      expect(screen.getByText("2 trips in your collection")).toBeInTheDocument();
    });

    it("renders all trip cards", () => {
      mockTrips.mockReturnValue(sampleTrips);

      render(<TripsPage />);
      expect(screen.getByTestId("trip-card-trip-1")).toBeInTheDocument();
      expect(screen.getByTestId("trip-card-trip-2")).toBeInTheDocument();
    });

    it("renders status overview cards", () => {
      mockTrips.mockReturnValue(sampleTrips);

      render(<TripsPage />);
      expect(screen.getByText("Draft")).toBeInTheDocument();
      expect(screen.getByText("Upcoming")).toBeInTheDocument();
      expect(screen.getByText("Active")).toBeInTheDocument();
      expect(screen.getByText("Completed")).toBeInTheDocument();
    });

    it("renders search input", () => {
      mockTrips.mockReturnValue(sampleTrips);

      render(<TripsPage />);
      expect(
        screen.getByPlaceholderText("Search trips, destinations...")
      ).toBeInTheDocument();
    });

    it("renders filter dropdown", () => {
      mockTrips.mockReturnValue(sampleTrips);

      render(<TripsPage />);
      // The SelectTrigger renders with the filter icon
      expect(screen.getByTestId("filter-icon")).toBeInTheDocument();
    });

    it("filters trips when status filter changes", async () => {
      mockTrips.mockReturnValue([
        {
          createdAt: "2024-01-10T10:00:00Z",
          destinations: [],
          endDate: "2099-01-10",
          id: "trip-upcoming",
          startDate: "2099-01-01",
          title: "Future Trip",
          visibility: "private",
        },
        {
          createdAt: "2024-01-01T10:00:00Z",
          destinations: [],
          id: "trip-draft",
          title: "Draft Trip",
          visibility: "private",
        },
      ]);

      render(<TripsPage />);

      const filterTrigger = screen.getAllByRole("combobox")[0];

      await userEvent.click(filterTrigger);
      const filterList = (await screen.findAllByRole("listbox"))[0];
      await userEvent.click(
        within(filterList).getByRole("option", { name: "Upcoming" })
      );

      await waitFor(() => {
        expect(screen.getByTestId("trip-card-trip-upcoming")).toBeInTheDocument();
        expect(screen.queryByTestId("trip-card-trip-draft")).not.toBeInTheDocument();
      });
    });

    it("renders view mode toggle buttons", () => {
      mockTrips.mockReturnValue(sampleTrips);

      render(<TripsPage />);
      expect(screen.getByTestId("grid-icon")).toBeInTheDocument();
      expect(screen.getByTestId("list-icon")).toBeInTheDocument();
    });

    it("sorts trips when sort option changes", async () => {
      const tripsForSort: MockTrip[] = [
        {
          createdAt: "2024-01-10T10:00:00Z",
          destinations: [],
          id: "trip-z",
          title: "Zebra Trip",
          visibility: "private",
        },
        {
          createdAt: "2024-01-11T10:00:00Z",
          destinations: [],
          id: "trip-a",
          title: "Alpine Adventure",
          visibility: "private",
        },
      ];
      mockTrips.mockReturnValue(tripsForSort);

      render(<TripsPage />);

      const sortTrigger = screen.getAllByRole("combobox")[1];
      await userEvent.click(sortTrigger);
      const nameOption = await screen.findByRole("option", { name: "Name" });
      await userEvent.click(nameOption);

      const cards = screen.getAllByTestId(/trip-card-/);
      expect(cards[0]).toHaveTextContent("Alpine Adventure");
      expect(cards[1]).toHaveTextContent("Zebra Trip");
    });

    it("toggles view mode to list when list button is clicked", () => {
      mockTrips.mockReturnValue(sampleTrips);

      const { container } = render(<TripsPage />);

      // Grid view by default
      expect(container.querySelector(".grid.grid-cols-1")).toBeTruthy();

      const listButton = screen.getByTestId("list-icon").closest("button");
      expect(listButton).toBeTruthy();
      if (!listButton) return;

      fireEvent.click(listButton);

      expect(container.querySelector(".space-y-4")).toBeTruthy();
    });

    it("renders create trip button", () => {
      mockTrips.mockReturnValue(sampleTrips);

      render(<TripsPage />);
      expect(screen.getByText("Create Trip")).toBeInTheDocument();
    });

    it("calls createTrip when Create Trip button is clicked", async () => {
      mockTrips.mockReturnValue(sampleTrips);
      mockCreateTrip.mockResolvedValue({ id: "new-trip" });

      render(<TripsPage />);

      fireEvent.click(screen.getByText("Create Trip"));

      await waitFor(() => {
        expect(mockCreateTrip).toHaveBeenCalledTimes(1);
      });
    });

    it("renders connection status indicator", () => {
      mockTrips.mockReturnValue(sampleTrips);

      render(<TripsPage />);
      expect(screen.getByTestId("connection-status")).toBeInTheDocument();
    });

    it("deletes a trip when delete button is clicked", async () => {
      mockTrips.mockReturnValue([
        {
          createdAt: "2024-01-10T10:00:00Z",
          destinations: [{ name: "Kyoto" }],
          id: "trip-delete-id",
          title: "Kyoto Escape",
          visibility: "private",
        },
      ]);
      mockDeleteTrip.mockResolvedValue(undefined);
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

      try {
        render(<TripsPage />);

        fireEvent.click(screen.getByText("Delete"));

        await waitFor(() => {
          expect(mockDeleteTrip).toHaveBeenCalledTimes(1);
          expect(mockDeleteTrip).toHaveBeenCalledWith("trip-delete-id");
        });

        expect(confirmSpy).toHaveBeenCalledTimes(1);
      } finally {
        confirmSpy.mockRestore();
      }
    });
  });

  describe("Search functionality", () => {
    const sampleTrips: MockTrip[] = [
      {
        createdAt: "2024-01-15T10:00:00Z",
        destinations: [{ name: "Paris" }],
        id: "trip-1",
        title: "Paris Vacation",
        visibility: "private",
      },
      {
        createdAt: "2024-01-10T10:00:00Z",
        destinations: [{ name: "Tokyo" }],
        id: "trip-2",
        title: "Tokyo Adventure",
        visibility: "private",
      },
    ];

    it("filters trips by search query", async () => {
      mockTrips.mockReturnValue(sampleTrips);

      render(<TripsPage />);
      const searchInput = screen.getByPlaceholderText("Search trips, destinations...");

      fireEvent.change(searchInput, { target: { value: "Paris" } });

      await waitFor(() => {
        expect(screen.getByTestId("trip-card-trip-1")).toBeInTheDocument();
        expect(screen.queryByTestId("trip-card-trip-2")).not.toBeInTheDocument();
      });
    });

    it("shows no results message when search finds nothing", async () => {
      mockTrips.mockReturnValue(sampleTrips);

      render(<TripsPage />);
      const searchInput = screen.getByPlaceholderText("Search trips, destinations...");

      fireEvent.change(searchInput, { target: { value: "nonexistent" } });

      await waitFor(() => {
        expect(screen.getByText("No trips found")).toBeInTheDocument();
        expect(
          screen.getByText("Try adjusting your search or filter criteria")
        ).toBeInTheDocument();
      });
    });

    it("clears filters when Clear Filters is clicked after empty search", async () => {
      mockTrips.mockReturnValue(sampleTrips);

      render(<TripsPage />);
      const searchInput = screen.getByPlaceholderText("Search trips, destinations...");

      fireEvent.change(searchInput, { target: { value: "nonexistent" } });

      await waitFor(() => {
        expect(screen.getByText("No trips found")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("Clear Filters"));

      await waitFor(() => {
        expect(screen.queryByText("No trips found")).not.toBeInTheDocument();
        expect(screen.getByTestId("trip-card-trip-1")).toBeInTheDocument();
        expect(screen.getByTestId("trip-card-trip-2")).toBeInTheDocument();
      });
    });
  });

  describe("Trip count display", () => {
    it("shows singular 'trip' for 1 trip", () => {
      mockTrips.mockReturnValue([
        {
          createdAt: "2024-01-15T10:00:00Z",
          destinations: [],
          id: "trip-1",
          title: "Solo Trip",
          visibility: "private",
        },
      ]);

      render(<TripsPage />);
      expect(screen.getByText("1 trip in your collection")).toBeInTheDocument();
    });

    it("shows plural 'trips' for multiple trips", () => {
      mockTrips.mockReturnValue([
        {
          createdAt: "2024-01-15T10:00:00Z",
          destinations: [],
          id: "trip-1",
          title: "Trip 1",
          visibility: "private",
        },
        {
          createdAt: "2024-01-10T10:00:00Z",
          destinations: [],
          id: "trip-2",
          title: "Trip 2",
          visibility: "private",
        },
      ]);

      render(<TripsPage />);
      expect(screen.getByText("2 trips in your collection")).toBeInTheDocument();
    });
  });
});
