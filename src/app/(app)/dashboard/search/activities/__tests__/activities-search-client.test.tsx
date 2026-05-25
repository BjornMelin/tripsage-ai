/** @vitest-environment jsdom */

import type { Activity, ActivitySearchParams } from "@schemas/search";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const sampleActivity: Activity = {
  date: "2099-06-01",
  description: "Guided museum visit",
  duration: 2,
  id: "activity-1",
  location: "Paris",
  name: "Museum Tour",
  price: 25,
  rating: 4.5,
  type: "Museum",
};

const {
  mockExecuteSearch,
  mockGetPlanningTrips,
  mockInitializeSearch,
  mockRecordClientErrorOnActiveSpan,
  mockToast,
} = vi.hoisted(() => ({
  mockExecuteSearch: vi.fn(),
  mockGetPlanningTrips: vi.fn(),
  mockInitializeSearch: vi.fn(),
  mockRecordClientErrorOnActiveSpan: vi.fn(),
  mockToast: vi.fn(),
}));

const { mockSearchResultsState } = vi.hoisted(() => ({
  mockSearchResultsState: {
    error: null as Error | null,
    metrics: { provider: "TestProvider" },
    results: { activities: [] as Activity[] },
  },
}));

const { mockComparisonState, mockUseComparisonStore } = vi.hoisted(() => {
  const comparisonState = {
    addItem: vi.fn(),
    clearByType: vi.fn(),
    getItemsByType: vi.fn(() => []),
    hasItem: vi.fn(() => false),
    removeItem: vi.fn(),
  };
  const useStore = <T,>(selector: (state: typeof comparisonState) => T): T =>
    selector(comparisonState);
  return {
    mockComparisonState: comparisonState,
    mockUseComparisonStore: Object.assign(useStore, {
      getState: () => comparisonState,
    }),
  };
});

vi.mock("@/components/layouts/search-layout", () => ({
  SearchLayout: ({ children }: { children: React.ReactNode }) => (
    <main>{children}</main>
  ),
}));

vi.mock("@/components/ui/use-toast", () => ({
  useToast: () => ({ toast: mockToast }),
}));

vi.mock("@/features/search/components/cards/activity-card", () => ({
  ActivityCard: ({
    activity,
    onSelect,
  }: {
    activity: Activity;
    onSelect?: (activity: Activity) => void;
  }) => (
    <button type="button" onClick={() => onSelect?.(activity)}>
      Select {activity.name}
    </button>
  ),
}));

vi.mock("@/features/search/components/forms/activity-search-form", () => ({
  ActivitySearchForm: () => <div data-testid="activity-search-form" />,
}));

vi.mock("@/features/search/components/modals/activity-comparison-modal", () => ({
  ActivityComparisonModal: () => null,
}));

vi.mock("@/features/search/components/modals/trip-selection-modal", () => ({
  TripSelectionModal: () => null,
}));

vi.mock("@/features/search/hooks/search/use-search-orchestration", () => ({
  useSearchOrchestration: () => ({
    executeSearch: mockExecuteSearch,
    initializeSearch: mockInitializeSearch,
    isSearching: false,
  }),
}));

vi.mock("@/features/search/store/comparison-store", () => ({
  useComparisonStore: mockUseComparisonStore,
}));

vi.mock("@/features/search/store/search-results-store", () => ({
  useSearchResultsStore: <T,>(
    selector: (state: typeof mockSearchResultsState) => T
  ): T => selector(mockSearchResultsState),
}));

vi.mock("@/lib/telemetry/client-errors", () => ({
  recordClientErrorOnActiveSpan: mockRecordClientErrorOnActiveSpan,
}));

vi.mock("../actions", () => ({
  addActivityToTrip: vi.fn(),
  getPlanningTrips: mockGetPlanningTrips,
}));

vi.mock("../activities-selection-dialog", () => ({
  ActivitiesSelectionDialog: ({
    isOpen,
    onAddToTrip,
    selectedActivity,
  }: {
    isOpen: boolean;
    onAddToTrip: () => void;
    selectedActivity: Activity | null;
  }) =>
    isOpen && selectedActivity ? (
      <button type="button" onClick={onAddToTrip}>
        Add {selectedActivity.name} to trip
      </button>
    ) : null,
}));

import ActivitiesSearchClient from "../activities-search-client";

describe("ActivitiesSearchClient", () => {
  beforeEach(() => {
    mockComparisonState.addItem.mockReset();
    mockComparisonState.clearByType.mockReset();
    mockComparisonState.getItemsByType.mockReset();
    mockComparisonState.getItemsByType.mockReturnValue([]);
    mockComparisonState.hasItem.mockReset();
    mockComparisonState.hasItem.mockReturnValue(false);
    mockComparisonState.removeItem.mockReset();
    mockExecuteSearch.mockReset();
    mockGetPlanningTrips.mockReset();
    mockInitializeSearch.mockReset();
    mockRecordClientErrorOnActiveSpan.mockReset();
    mockToast.mockReset();
    mockSearchResultsState.error = null;
    mockSearchResultsState.metrics = { provider: "TestProvider" };
    mockSearchResultsState.results = { activities: [sampleActivity] };
  });

  it("reports trip-loading failures through telemetry", async () => {
    const loadError = new Error("trip fetch failed");
    mockGetPlanningTrips.mockRejectedValueOnce(loadError);
    const onSubmitServer = vi.fn<(params: ActivitySearchParams) => Promise<never>>();

    render(<ActivitiesSearchClient onSubmitServer={onSubmitServer} />);

    fireEvent.click(screen.getByRole("button", { name: "Select Museum Tour" }));
    fireEvent.click(screen.getByRole("button", { name: "Add Museum Tour to trip" }));

    await waitFor(() => {
      expect(mockRecordClientErrorOnActiveSpan).toHaveBeenCalledWith(loadError, {
        action: "loadTrips",
        context: "ActivitiesSearchClient",
      });
    });
    expect(mockToast).toHaveBeenCalledWith({
      description: "trip fetch failed",
      title: "Error",
      variant: "destructive",
    });
  });
});
