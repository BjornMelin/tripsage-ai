/** @vitest-environment jsdom */

import type { Activity } from "@schemas/search";
import type { UiTrip } from "@schemas/trips";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TripSelectionModal } from "../trip-selection-modal";

const MOCK_ACTIVITY: Activity = {
  coordinates: { lat: 48.8566, lng: 2.3522 },
  date: "2026-06-01T00:00:00Z",
  description: "Guided museum tour",
  duration: 120,
  id: "activity-1",
  images: [],
  location: "Paris",
  name: "Louvre Highlights",
  price: 75,
  rating: 4.7,
  type: "tour",
};

const NEXT_ACTIVITY: Activity = {
  ...MOCK_ACTIVITY,
  id: "activity-2",
  name: "Seine Evening Cruise",
};

const MOCK_TRIPS: UiTrip[] = [
  {
    currency: "USD",
    destination: "Paris",
    destinations: [],
    id: "trip-1",
    startDate: "2026-06-01",
    title: "Paris Spring",
  },
  {
    currency: "USD",
    destination: "Rome",
    destinations: [],
    id: "trip-2",
    title: "Rome Weekend",
  },
];

/** Renders the modal with default props and user-event helpers. */
function RenderTripSelectionModal(
  overrides: Partial<Parameters<typeof TripSelectionModal>[0]> = {}
) {
  const props: Parameters<typeof TripSelectionModal>[0] = {
    activity: MOCK_ACTIVITY,
    isAdding: false,
    isOpen: true,
    onAddToTrip: vi.fn().mockResolvedValue(undefined),
    onClose: vi.fn(),
    trips: MOCK_TRIPS,
    ...overrides,
  };

  return {
    props,
    user: userEvent.setup(),
    ...render(<TripSelectionModal {...props} />),
  };
}

/** Finds the clickable label for a trip name in the modal list. */
function GetTripLabel(name: string): HTMLLabelElement {
  const label = screen.getByText(name).closest("label");
  if (!(label instanceof HTMLLabelElement)) {
    throw new Error(`Missing label for trip: ${name}`);
  }
  return label;
}

describe("TripSelectionModal", () => {
  it("adds the selected trip", async () => {
    const { props, user } = RenderTripSelectionModal();
    const addButton = screen.getByRole("button", { name: "Add to Trip" });

    expect(screen.getByText("Jun 1, 2026")).toBeInTheDocument();
    expect(addButton).toBeDisabled();

    await user.click(GetTripLabel("Paris Spring"));

    expect(addButton).toBeEnabled();

    await user.click(addButton);

    expect(props.onAddToTrip).toHaveBeenCalledWith("trip-1");
  });

  it("resets the selected trip when the activity changes", async () => {
    const { props, rerender, user } = RenderTripSelectionModal();

    await user.click(GetTripLabel("Paris Spring"));
    expect(screen.getByRole("button", { name: "Add to Trip" })).toBeEnabled();

    rerender(<TripSelectionModal {...props} activity={NEXT_ACTIVITY} />);

    expect(screen.getByRole("button", { name: "Add to Trip" })).toBeDisabled();
  });

  it("resets the selected trip when reopened", async () => {
    const { props, rerender, user } = RenderTripSelectionModal();

    await user.click(GetTripLabel("Paris Spring"));
    expect(screen.getByRole("button", { name: "Add to Trip" })).toBeEnabled();

    rerender(<TripSelectionModal {...props} isOpen={false} />);
    rerender(<TripSelectionModal {...props} isOpen />);

    expect(screen.getByRole("button", { name: "Add to Trip" })).toBeDisabled();
  });
});
