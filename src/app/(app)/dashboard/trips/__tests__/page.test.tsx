/** @vitest-environment jsdom */

import type { UiTrip } from "@schemas/trips";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  type MockInstance,
  test,
  vi,
} from "vitest";
import { ApiError, type AppError } from "@/lib/api/error-types";

// Mock Lucide icons
vi.mock("lucide-react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("lucide-react")>();
  return {
    ...actual,
    FilterIcon: () => <span data-testid="filter-icon" />,
    GridIcon: () => <span data-testid="grid-icon" />,
    ListIcon: () => <span data-testid="list-icon" />,
    Loader2Icon: ({ className }: { className?: string }) => (
      <span data-testid="loader-icon" className={className} />
    ),
    PlusIcon: () => <span data-testid="plus-icon" />,
    SearchIcon: () => <span data-testid="search-icon" />,
  };
});

// Mock trip data
const mockTrips = vi.hoisted(() => vi.fn((): UiTrip[] => []));
const mockIsLoading = vi.hoisted(() => vi.fn(() => false));
const mockError = vi.hoisted(() => vi.fn((): AppError | null => null));
const mockIsConnected = vi.hoisted(() => vi.fn(() => true));
const mockRealtimeStatus = vi.hoisted(() =>
  vi.fn(() => ({ errors: [] as Error[], isConnected: true }))
);
const mockCreateTrip = vi.hoisted(() => vi.fn());
const mockCreateIsPending = vi.hoisted(() => vi.fn(() => false));
const mockDeleteTrip = vi.hoisted(() => vi.fn());
const mockDeleteIsPending = vi.hoisted(() => vi.fn(() => false));
const mockToast = vi.hoisted(() => vi.fn());

const DEFAULT_USER_ID = "11111111-1111-4111-8aaa-111111111111";

vi.mock("@/hooks/use-trips", () => ({
  useCreateTrip: () => ({
    isPending: mockCreateIsPending(),
    mutateAsync: mockCreateTrip,
  }),
  useDeleteTrip: () => ({
    isPending: mockDeleteIsPending(),
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

vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({ toast: mockToast }),
}));

// Mock child components
vi.mock("@/features/realtime/components/connection-status-monitor", () => ({
  ConnectionStatusIndicator: () => <div data-testid="connection-status" />,
}));

vi.mock("@/features/trips/components/trip-card", () => ({
  TripCard: ({ trip, onDelete }: { trip: UiTrip; onDelete?: (id: string) => void }) => (
    <div data-testid={`trip-card-${trip.id}`}>
      <span>{trip.title}</span>
      {onDelete ? (
        <button type="button" onClick={() => onDelete(trip.id)}>
          Delete
        </button>
      ) : null}
    </div>
  ),
}));

// Import after mocks so Vitest applies them before module evaluation.
import TripsClient from "../trips-client";

function TripsPage() {
  return <TripsClient userId={DEFAULT_USER_ID} />;
}

const DEFAULT_CURRENCY: UiTrip["currency"] = "USD";
const destination = (
  name: string,
  country: string
): UiTrip["destinations"][number] => ({
  country,
  id: `${name.toLowerCase()}-${country.toLowerCase()}`,
  name,
});

describe("TripsPage", () => {
  beforeEach(() => {
    mockTrips.mockReset();
    mockIsLoading.mockReset();
    mockError.mockReset();
    mockIsConnected.mockReset();
    mockRealtimeStatus.mockReset();
    mockCreateTrip.mockReset();
    mockCreateIsPending.mockReset();
    mockDeleteTrip.mockReset();
    mockDeleteIsPending.mockReset();
    mockToast.mockReset();
    mockTrips.mockReturnValue([]);
    mockIsLoading.mockReturnValue(false);
    mockError.mockReturnValue(null);
    mockIsConnected.mockReturnValue(true);
    mockRealtimeStatus.mockReturnValue({ errors: [], isConnected: true });
    mockCreateIsPending.mockReturnValue(false);
    mockDeleteIsPending.mockReturnValue(false);
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
          currency: DEFAULT_CURRENCY,
          destinations: [destination("Paris", "France")],
          id: "trip-loaded",
          title: "Loaded Trip",
          userId: DEFAULT_USER_ID,
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
      await userEvent.click(screen.getByText("Create Your First Trip"));

      await waitFor(() => {
        expect(mockCreateTrip).toHaveBeenCalledTimes(1);
      });
    });

    it("shows an error toast when createTrip fails", async () => {
      mockTrips.mockReturnValue([]);
      mockCreateTrip.mockRejectedValueOnce(new Error("fail"));

      render(<TripsPage />);
      await userEvent.click(screen.getByText("Create Your First Trip"));

      await waitFor(() => {
        expect(mockCreateTrip).toHaveBeenCalledTimes(1);
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            title: "Unable to create trip",
            variant: "destructive",
          })
        );
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
          currency: DEFAULT_CURRENCY,
          destinations: [destination("Paris", "France")],
          id: "trip-connected",
          title: "Connected Trip",
          visibility: "private",
        },
      ]);
      mockIsConnected.mockReturnValue(false);
      mockRealtimeStatus.mockReturnValue({ errors: [], isConnected: false });

      render(<TripsPage />);

      expect(screen.getByTestId("connection-status")).toBeInTheDocument();
    });

    it("logs trips errors to console in development mode", async () => {
      const originalNodeEnv = process.env.NODE_ENV;
      vi.stubEnv("NODE_ENV", "development");

      const consoleErrorSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => undefined);
      const error = new ApiError("Failed to load trips", 500);
      mockError.mockReturnValue(error);

      try {
        render(<TripsPage />);

        await waitFor(() => {
          expect(consoleErrorSpy).toHaveBeenCalledWith("Trips error:", error);
        });
      } finally {
        vi.stubEnv("NODE_ENV", originalNodeEnv);
        consoleErrorSpy.mockRestore();
      }
    });
  });

  describe("With trips", () => {
    const sampleTrips: UiTrip[] = [
      {
        budget: 5000,
        createdAt: "2024-01-15T10:00:00Z",
        currency: DEFAULT_CURRENCY,
        description: "A romantic getaway",
        destinations: [destination("Paris", "France")],
        endDate: "2099-06-10",
        id: "trip-1",
        startDate: "2099-06-01",
        title: "Paris Vacation",
        userId: DEFAULT_USER_ID,
        visibility: "private",
      },
      {
        budget: 8000,
        createdAt: "2024-01-10T10:00:00Z",
        currency: DEFAULT_CURRENCY,
        description: "Exploring Japan",
        destinations: [destination("Tokyo", "Japan"), destination("Kyoto", "Japan")],
        endDate: "2099-07-25",
        id: "trip-2",
        startDate: "2099-07-15",
        title: "Tokyo Adventure",
        userId: DEFAULT_USER_ID,
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
          currency: DEFAULT_CURRENCY,
          destinations: [],
          endDate: "2099-01-10",
          id: "trip-upcoming",
          startDate: "2099-01-01",
          title: "Future Trip",
          userId: DEFAULT_USER_ID,
          visibility: "private",
        },
        {
          createdAt: "2024-01-01T10:00:00Z",
          currency: DEFAULT_CURRENCY,
          destinations: [],
          id: "trip-draft",
          title: "Draft Trip",
          userId: DEFAULT_USER_ID,
          visibility: "private",
        },
      ]);

      render(<TripsPage />);

      const filterTrigger = screen.getByRole("combobox", { name: /filter trips/i });

      await userEvent.click(filterTrigger);
      const filterList = await screen.findByRole("listbox");
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
      expect(screen.getByRole("button", { name: "Grid view" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "List view" })).toBeInTheDocument();
    });

    it("sorts trips when sort option changes", async () => {
      const tripsForSort: UiTrip[] = [
        {
          createdAt: "2024-01-10T10:00:00Z",
          currency: DEFAULT_CURRENCY,
          destinations: [],
          id: "trip-z",
          title: "Zebra Trip",
          userId: DEFAULT_USER_ID,
          visibility: "private",
        },
        {
          createdAt: "2024-01-11T10:00:00Z",
          currency: DEFAULT_CURRENCY,
          destinations: [],
          id: "trip-a",
          title: "Alpine Adventure",
          userId: DEFAULT_USER_ID,
          visibility: "private",
        },
      ];
      mockTrips.mockReturnValue(tripsForSort);

      render(<TripsPage />);

      const sortTrigger = screen.getByRole("combobox", { name: /sort trips/i });
      await userEvent.click(sortTrigger);
      const nameOption = await screen.findByRole("option", { name: "Name" });
      await userEvent.click(nameOption);

      const cards = screen.getAllByTestId(/trip-card-/);
      expect(cards[0]).toHaveTextContent("Alpine Adventure");
      expect(cards[1]).toHaveTextContent("Zebra Trip");
    });

    it("supports additional sort options for budget and destinations", async () => {
      const tripsForSort: UiTrip[] = [
        {
          budget: 2000,
          createdAt: "2024-01-11T10:00:00Z",
          currency: DEFAULT_CURRENCY,
          destinations: [destination("Tokyo", "Japan")],
          id: "trip-budget-low",
          title: "Budget Low",
          userId: DEFAULT_USER_ID,
          visibility: "private",
        },
        {
          budget: 8000,
          createdAt: "2024-01-10T10:00:00Z",
          currency: DEFAULT_CURRENCY,
          destinations: [destination("Paris", "France"), destination("Lyon", "France")],
          id: "trip-budget-high",
          title: "Budget High",
          userId: DEFAULT_USER_ID,
          visibility: "private",
        },
      ];
      mockTrips.mockReturnValue(tripsForSort);

      render(<TripsPage />);

      const sortTrigger = screen.getByRole("combobox", { name: /sort trips/i });
      await userEvent.click(sortTrigger);
      await userEvent.click(await screen.findByRole("option", { name: "Budget" }));

      await waitFor(() => {
        const cards = screen.getAllByTestId(/trip-card-/);
        expect(cards[0]).toHaveAttribute("data-testid", "trip-card-trip-budget-high");
      });

      await userEvent.click(sortTrigger);
      await userEvent.click(
        await screen.findByRole("option", { name: "Destinations" })
      );

      await waitFor(() => {
        const cards = screen.getAllByTestId(/trip-card-/);
        expect(cards[0]).toHaveAttribute("data-testid", "trip-card-trip-budget-high");
        expect(cards[1]).toHaveAttribute("data-testid", "trip-card-trip-budget-low");
      });
    });

    it("toggles view mode to list when list button is clicked", async () => {
      mockTrips.mockReturnValue(sampleTrips);

      render(<TripsPage />);

      const listButton = screen.getByRole("button", { name: "List view" });
      await userEvent.click(listButton);

      expect(listButton).toHaveAttribute("data-state", "on");
      const gridButton = screen.getByRole("button", { name: "Grid view" });
      expect(gridButton).toHaveAttribute("data-state", "off");
      expect(screen.getByTestId("trips-view")).toHaveAttribute(
        "data-view-mode",
        "list"
      );
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

      await userEvent.click(screen.getByText("Create Trip"));

      await waitFor(() => {
        expect(mockCreateTrip).toHaveBeenCalledTimes(1);
      });
    });

    it("renders connection status indicator", () => {
      mockTrips.mockReturnValue(sampleTrips);

      render(<TripsPage />);
      expect(screen.getByTestId("connection-status")).toBeInTheDocument();
    });

    it("shows connection state attributes for disconnected and error states", () => {
      mockTrips.mockReturnValue(sampleTrips);
      mockIsConnected.mockReturnValue(false);
      mockRealtimeStatus.mockReturnValue({ errors: [], isConnected: false });

      const { rerender } = render(<TripsPage />);

      let connectionWrapper = screen.getByTestId("trips-connection");
      let indicator = within(connectionWrapper).getByTestId("connection-status");
      expect(indicator.parentElement).toHaveAttribute(
        "data-connection-state",
        "disconnected"
      );

      mockRealtimeStatus.mockReturnValue({
        errors: [new Error("lost")],
        isConnected: false,
      });
      rerender(<TripsPage />);

      connectionWrapper = screen.getByTestId("trips-connection");
      indicator = within(connectionWrapper).getByTestId("connection-status");
      expect(indicator.parentElement).toHaveAttribute("data-connection-state", "error");
    });

    it("deletes a trip when delete button is clicked", async () => {
      mockTrips.mockReturnValue([
        {
          createdAt: "2024-01-10T10:00:00Z",
          currency: DEFAULT_CURRENCY,
          destinations: [destination("Kyoto", "Japan")],
          id: "trip-delete-id",
          title: "Kyoto Escape",
          userId: DEFAULT_USER_ID,
          visibility: "private",
        },
      ]);
      mockDeleteTrip.mockResolvedValue(undefined);

      render(<TripsPage />);

      await userEvent.click(screen.getByText("Delete"));

      const dialog = await screen.findByRole("alertdialog");
      await userEvent.click(within(dialog).getByRole("button", { name: "Delete" }));

      await waitFor(() => {
        expect(mockDeleteTrip).toHaveBeenCalledTimes(1);
        expect(mockDeleteTrip).toHaveBeenCalledWith("trip-delete-id");
      });
    });

    it("shows an error toast when delete fails and keeps the trip visible", async () => {
      mockTrips.mockReturnValue([
        {
          createdAt: "2024-01-10T10:00:00Z",
          currency: DEFAULT_CURRENCY,
          destinations: [destination("Kyoto", "Japan")],
          id: "trip-delete-id",
          title: "Kyoto Escape",
          userId: DEFAULT_USER_ID,
          visibility: "private",
        },
      ]);
      mockDeleteTrip.mockRejectedValueOnce(new Error("fail"));

      render(<TripsPage />);

      await userEvent.click(screen.getByText("Delete"));

      const dialog = await screen.findByRole("alertdialog");
      await userEvent.click(within(dialog).getByRole("button", { name: "Delete" }));

      await waitFor(() => {
        expect(mockDeleteTrip).toHaveBeenCalledTimes(1);
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            title: "Unable to delete trip",
            variant: "destructive",
          })
        );
      });

      expect(screen.getByTestId("trip-card-trip-delete-id")).toBeInTheDocument();
    });

    it("shows loading state on delete button while deletion is pending", async () => {
      mockTrips.mockReturnValue([
        {
          createdAt: "2024-01-10T10:00:00Z",
          currency: DEFAULT_CURRENCY,
          destinations: [destination("Kyoto", "Japan")],
          id: "trip-delete-id",
          title: "Kyoto Escape",
          userId: DEFAULT_USER_ID,
          visibility: "private",
        },
      ]);
      mockDeleteIsPending.mockReturnValue(true);

      render(<TripsPage />);

      await userEvent.click(screen.getByText("Delete"));

      const dialog = await screen.findByRole("alertdialog");
      const deleteButton = within(dialog).getByRole("button", { name: /deleting/i });

      expect(deleteButton).toBeDisabled();
      expect(deleteButton).toHaveAttribute("aria-busy", "true");
      expect(within(deleteButton).getByTestId("loader-icon")).toBeInTheDocument();
    });
  });

  describe("Search functionality", () => {
    const sampleTrips: UiTrip[] = [
      {
        createdAt: "2024-01-15T10:00:00Z",
        currency: DEFAULT_CURRENCY,
        destinations: [destination("Paris", "France")],
        id: "trip-1",
        title: "Paris Vacation",
        userId: DEFAULT_USER_ID,
        visibility: "private",
      },
      {
        createdAt: "2024-01-10T10:00:00Z",
        currency: DEFAULT_CURRENCY,
        destinations: [destination("Tokyo", "Japan")],
        id: "trip-2",
        title: "Tokyo Adventure",
        userId: DEFAULT_USER_ID,
        visibility: "private",
      },
    ];

    it("filters trips by search query", async () => {
      mockTrips.mockReturnValue(sampleTrips);

      render(<TripsPage />);
      const searchInput = screen.getByPlaceholderText("Search trips, destinations...");

      await userEvent.clear(searchInput);
      await userEvent.type(searchInput, "Paris");

      await waitFor(() => {
        expect(screen.getByTestId("trip-card-trip-1")).toBeInTheDocument();
        expect(screen.queryByTestId("trip-card-trip-2")).not.toBeInTheDocument();
      });
    });

    it("shows no results message when search finds nothing", async () => {
      mockTrips.mockReturnValue(sampleTrips);

      render(<TripsPage />);
      const searchInput = screen.getByPlaceholderText("Search trips, destinations...");

      await userEvent.clear(searchInput);
      await userEvent.type(searchInput, "nonexistent");

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

      await userEvent.clear(searchInput);
      await userEvent.type(searchInput, "nonexistent");

      await waitFor(() => {
        expect(screen.getByText("No trips found")).toBeInTheDocument();
      });

      await userEvent.click(screen.getByText("Clear Filters"));

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
          currency: DEFAULT_CURRENCY,
          destinations: [],
          id: "trip-1",
          title: "Solo Trip",
          userId: DEFAULT_USER_ID,
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
          currency: DEFAULT_CURRENCY,
          destinations: [],
          id: "trip-1",
          title: "Trip 1",
          userId: DEFAULT_USER_ID,
          visibility: "private",
        },
        {
          createdAt: "2024-01-10T10:00:00Z",
          currency: DEFAULT_CURRENCY,
          destinations: [],
          id: "trip-2",
          title: "Trip 2",
          userId: DEFAULT_USER_ID,
          visibility: "private",
        },
      ]);

      render(<TripsPage />);
      expect(screen.getByText("2 trips in your collection")).toBeInTheDocument();
    });
  });

  describe("Additional filters", () => {
    const baseTrips: UiTrip[] = [
      {
        createdAt: "2024-01-10T10:00:00Z",
        currency: DEFAULT_CURRENCY,
        destinations: [],
        id: "trip-draft",
        title: "Draft Trip",
        userId: DEFAULT_USER_ID,
        visibility: "private",
      },
      {
        createdAt: "2024-01-12T10:00:00Z",
        currency: DEFAULT_CURRENCY,
        destinations: [],
        endDate: "2025-12-31",
        id: "trip-active",
        startDate: "2025-01-01",
        title: "Active Trip",
        userId: DEFAULT_USER_ID,
        visibility: "private",
      },
      {
        createdAt: "2024-01-15T10:00:00Z",
        currency: DEFAULT_CURRENCY,
        destinations: [],
        endDate: "2024-02-01",
        id: "trip-completed",
        startDate: "2024-01-01",
        title: "Completed Trip",
        userId: DEFAULT_USER_ID,
        visibility: "private",
      },
    ];

    let nowSpy: MockInstance<() => number> | null = null;

    beforeEach(() => {
      nowSpy = vi
        .spyOn(Date, "now")
        .mockReturnValue(new Date("2025-06-15T00:00:00Z").getTime());
    });

    afterEach(() => {
      nowSpy?.mockRestore();
      nowSpy = null;
    });

    const selectFilter = async (name: string) => {
      const trigger = screen.getByRole("combobox", { name: /filter trips/i });
      await userEvent.click(trigger);
      const list = await screen.findByRole("listbox");
      await userEvent.click(within(list).getByRole("option", { name }));
    };

    test.each([
      ["Draft", "trip-draft"],
      ["Active", "trip-active"],
      ["Completed", "trip-completed"],
    ])("filters %s trips", async (filterName, expectedTripId) => {
      const allTripIds = ["trip-draft", "trip-active", "trip-completed"] as const;

      mockTrips.mockReturnValue(baseTrips);
      render(<TripsPage />);
      await selectFilter(filterName);

      await waitFor(() => {
        expect(screen.getByTestId(`trip-card-${expectedTripId}`)).toBeInTheDocument();
        for (const tripId of allTripIds) {
          if (tripId === expectedTripId) continue;
          expect(screen.queryByTestId(`trip-card-${tripId}`)).not.toBeInTheDocument();
        }
      });
    });
  });
});
