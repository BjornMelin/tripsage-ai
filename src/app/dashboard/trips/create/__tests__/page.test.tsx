/** @vitest-environment jsdom */

import { ISO_DATETIME_STRING } from "@schemas/shared/time";
import type { TripSuggestion, UiTrip } from "@schemas/trips";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { queryKeys } from "@/lib/query-keys";
import { unsafeCast } from "@/test/helpers/unsafe-cast";
import { getTestQueryClient, render } from "@/test/test-utils";

const { mockCancelRequests, mockCreateTrip, mockGetSuggestions, mockPush, mockToast } =
  vi.hoisted(() => ({
    mockCancelRequests: vi.fn(),
    mockCreateTrip: vi.fn(),
    mockGetSuggestions: vi.fn(),
    mockPush: vi.fn(),
    mockToast: vi.fn(),
  }));

const navigationState = vi.hoisted(() => ({
  params: new URLSearchParams(),
}));

const searchParamsApi = {
  get: (key: string) => navigationState.params.get(key),
};

const authenticatedApiMock = {
  get: mockGetSuggestions,
};

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  useSearchParams: () => searchParamsApi,
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("lucide-react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("lucide-react")>();
  const Icon = ({ className }: { className?: string }) => (
    <span data-testid="icon" className={className} />
  );

  return {
    ...actual,
    ArrowLeftIcon: Icon,
    CalendarIcon: Icon,
    CheckIcon: Icon,
    Loader2Icon: Icon,
    MapPinIcon: Icon,
    SparklesIcon: Icon,
  };
});

vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({ toast: mockToast }),
}));

vi.mock("@/hooks/use-authenticated-api", () => ({
  useAuthenticatedApi: () => ({
    authenticatedApi: authenticatedApiMock,
    cancelRequests: mockCancelRequests,
  }),
}));

const mockIsPending = vi.hoisted(() => vi.fn(() => false));

vi.mock("@/hooks/use-trips", () => ({
  useCreateTrip: () => ({
    isPending: mockIsPending(),
    mutateAsync: mockCreateTrip,
  }),
}));

// Import after mocks so Vitest applies them before module evaluation.
import CreateTripPage from "../page";

const apiSuggestion = (overrides?: Partial<TripSuggestion>): TripSuggestion => ({
  bestTimeToVisit: "Spring",
  category: "culture",
  currency: "USD",
  description: "A great trip",
  destination: "Paris",
  duration: 5,
  estimatedPrice: 2000,
  highlights: ["A", "B", "C"],
  id: "sug-1",
  rating: 4.5,
  title: "Paris Getaway",
  ...overrides,
});

describe("CreateTripPage", () => {
  beforeEach(() => {
    navigationState.params = new URLSearchParams();
    vi.clearAllMocks();
    mockIsPending.mockReturnValue(false);
  });

  it("disables submit until the destination is valid", async () => {
    render(<CreateTripPage />);

    const createButton = screen.getByRole("button", { name: /create trip/i });
    expect(createButton).toBeDisabled();

    const destinationInput = screen.getByPlaceholderText("Tokyo, Japan");
    fireEvent.change(destinationInput, { target: { value: "Tokyo, Japan" } });

    await waitFor(() => {
      expect(createButton).toBeEnabled();
    });
  });

  it("prefills from cached suggestions when the suggestion is available", async () => {
    navigationState.params = new URLSearchParams(
      "suggestion=sug-1&limit=6&budget_max=2500"
    );
    const queryClient = getTestQueryClient();
    queryClient.setQueryData(
      queryKeys.trips.suggestions({ budget_max: 2500, limit: 6 }),
      [apiSuggestion()]
    );

    render(<CreateTripPage />, { queryClient });

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Tokyo, Japan")).toHaveValue("Paris");
    });

    expect(screen.getByPlaceholderText("Trip to Paris")).toHaveValue("Paris Getaway");
    expect(mockGetSuggestions).not.toHaveBeenCalled();
  });

  it("fetches suggestions when not cached and shows a loading indicator", async () => {
    navigationState.params = new URLSearchParams(
      "suggestion=sug-2&limit=6&budget_max=3000"
    );

    let resolveRequest: (value: TripSuggestion[]) => void = () => undefined;
    const deferred = new Promise<TripSuggestion[]>((resolve) => {
      resolveRequest = resolve;
    });
    mockGetSuggestions.mockReturnValueOnce(deferred);

    render(<CreateTripPage />);
    expect(screen.getByText(/loading details/i)).toBeInTheDocument();

    resolveRequest([
      apiSuggestion({ destination: "Rome", id: "sug-2", title: "Rome Break" }),
    ]);

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Tokyo, Japan")).toHaveValue("Rome");
    });

    expect(mockGetSuggestions).toHaveBeenCalledWith("/api/trips/suggestions", {
      params: { budget_max: 3000, limit: 6 },
    });
  });

  it("submits a create payload and navigates to the created trip", async () => {
    mockCreateTrip.mockResolvedValueOnce(unsafeCast<UiTrip>({ id: "trip-123" }));

    render(<CreateTripPage />);

    const destinationInput = screen.getByPlaceholderText("Tokyo, Japan");
    fireEvent.change(destinationInput, { target: { value: "Tokyo, Japan" } });

    const createButton = screen.getByRole("button", { name: /create trip/i });
    await waitFor(() => {
      expect(createButton).toBeEnabled();
    });

    fireEvent.click(createButton);

    await waitFor(() => {
      expect(mockCreateTrip).toHaveBeenCalledTimes(1);
    });
    const payload = mockCreateTrip.mock.calls[0]?.[0] as unknown;
    expect(payload).toEqual(
      expect.objectContaining({
        currency: "USD",
        destination: "Tokyo, Japan",
        status: "planning",
        title: "Trip to Tokyo, Japan",
        travelers: 1,
        tripType: "leisure",
        visibility: "private",
      })
    );

    const parsed = payload as { startDate: string; endDate: string };
    expect(ISO_DATETIME_STRING.safeParse(parsed.startDate).success).toBe(true);
    expect(ISO_DATETIME_STRING.safeParse(parsed.endDate).success).toBe(true);

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/dashboard/trips/trip-123");
    });
  });

  it("shows a destructive toast when create fails", async () => {
    mockCreateTrip.mockRejectedValueOnce(new Error("boom"));

    render(<CreateTripPage />);

    const destinationInput = screen.getByPlaceholderText("Tokyo, Japan");
    fireEvent.change(destinationInput, { target: { value: "Tokyo, Japan" } });

    const createButton = screen.getByRole("button", { name: /create trip/i });
    await waitFor(() => {
      expect(createButton).toBeEnabled();
    });

    fireEvent.click(createButton);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: "Unable to create trip",
          variant: "destructive",
        })
      );
    });
  });
});
