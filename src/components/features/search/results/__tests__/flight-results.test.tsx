/** @vitest-environment jsdom */

import type { FlightResult } from "@schemas/search";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import * as ClientErrors from "@/lib/telemetry/client-errors";
import { render } from "@/test/test-utils";
import { FlightResults } from "../flight-results";

const BaseFlight: FlightResult = {
  aircraft: "A320",
  airline: "Test Air",
  amenities: ["wifi", "meals"],
  arrival: { date: "2025-01-01", time: "10:00" },
  departure: { date: "2025-01-01", time: "08:00" },
  destination: { city: "Beta", code: "BBB" },
  duration: 120,
  emissions: { compared: "low", kg: 50 },
  flexibility: { changeable: true, refundable: false },
  flightNumber: "TA123",
  id: "f1",
  origin: { city: "Alpha", code: "AAA" },
  prediction: { confidence: 80, priceAlert: "buy_now", reason: "Stable prices" },
  price: { base: 100, currency: "USD", total: 120 },
  stops: { count: 0 },
};

describe("FlightResults", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading skeleton when loading is true", () => {
    render(
      <FlightResults loading results={[]} onSelect={vi.fn()} onCompare={vi.fn()} />
    );

    expect(screen.getByTestId("flight-results-loading")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /select flight/i })
    ).not.toBeInTheDocument();
  });

  it("calls onSelect when Select Flight is clicked", async () => {
    const onSelect = vi.fn().mockResolvedValue(undefined);
    render(
      <FlightResults results={[BaseFlight]} onSelect={onSelect} onCompare={vi.fn()} />
    );

    fireEvent.click(screen.getByRole("button", { name: /select flight/i }));

    await waitFor(() => {
      expect(onSelect).toHaveBeenCalledTimes(1);
      expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "f1" }));
    });
  });

  it("enables compare after selecting two flights and passes selected flights", () => {
    const flights = [
      BaseFlight,
      {
        ...BaseFlight,
        flightNumber: "TA456",
        id: "f2",
        price: { ...BaseFlight.price, total: 140 },
      },
    ];
    const onCompare = vi.fn();
    render(
      <FlightResults
        results={flights}
        onSelect={vi.fn().mockResolvedValue(undefined)}
        onCompare={onCompare}
      />
    );

    const checkboxes = screen.getAllByRole("checkbox", { name: /compare/i });
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);

    const compareButton = screen.getByRole("button", { name: /compare \(2\)/i });
    expect(compareButton).not.toBeDisabled();

    fireEvent.click(compareButton);

    expect(onCompare).toHaveBeenCalledTimes(1);
    expect(onCompare).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({ id: "f1" }),
        expect.objectContaining({ id: "f2" }),
      ])
    );
  });

  it("calls onModifySearch when provided and no results", () => {
    const onModifySearch = vi.fn();

    render(
      <FlightResults
        results={[]}
        onSelect={vi.fn().mockResolvedValue(undefined)}
        onCompare={vi.fn()}
        onModifySearch={onModifySearch}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /modify search/i }));

    expect(onModifySearch).toHaveBeenCalledTimes(1);
  });

  it("disables modify search button when handler is not provided", () => {
    render(
      <FlightResults
        results={[]}
        onSelect={vi.fn().mockResolvedValue(undefined)}
        onCompare={vi.fn()}
      />
    );

    const modifySearchButton = screen.getByRole("button", { name: /modify search/i });
    expect(modifySearchButton).toBeDisabled();
  });

  it("sorts flights by duration and toggles direction", async () => {
    const flights: FlightResult[] = [
      {
        ...BaseFlight,
        duration: 200,
        flightNumber: "TA111",
        id: "f1",
        price: { ...BaseFlight.price, total: 200 },
      },
      {
        ...BaseFlight,
        duration: 100,
        flightNumber: "TA222",
        id: "f2",
        price: { ...BaseFlight.price, total: 200 },
      },
    ];

    render(
      <FlightResults
        results={flights}
        onSelect={vi.fn().mockResolvedValue(undefined)}
        onCompare={vi.fn()}
      />
    );

    const sortTrigger = screen.getByRole("combobox", { name: /sort flights/i });
    fireEvent.click(sortTrigger);
    fireEvent.click(screen.getByRole("option", { name: /Duration/i }));

    await waitFor(() => {
      const cards = screen.getAllByTestId(/flight-card-/);
      expect(cards[0]).toHaveAttribute("data-testid", "flight-card-f2");
    });

    const directionButton = screen.getByRole("button", { name: /Sort direction/i });
    fireEvent.click(directionButton);

    await waitFor(() => {
      const cards = screen.getAllByTestId(/flight-card-/);
      expect(cards[0]).toHaveAttribute("data-testid", "flight-card-f1");
    });
  });

  it("limits comparison selection to three flights", () => {
    const flights = [
      BaseFlight,
      { ...BaseFlight, flightNumber: "TA222", id: "f2" },
      { ...BaseFlight, flightNumber: "TA333", id: "f3" },
      { ...BaseFlight, flightNumber: "TA444", id: "f4" },
    ];

    render(
      <FlightResults
        results={flights}
        onSelect={vi.fn().mockResolvedValue(undefined)}
        onCompare={vi.fn()}
      />
    );

    const checkboxes = screen.getAllByTestId("compare-checkbox");
    for (const checkbox of checkboxes.slice(0, 4)) {
      fireEvent.click(checkbox);
    }

    const compareButton = screen.getByRole("button", { name: /compare \(3\)/i });
    expect(compareButton).toBeInTheDocument();
    expect(checkboxes[0]).toBeChecked();
    expect(checkboxes[1]).toBeChecked();
    expect(checkboxes[2]).toBeChecked();
    expect(checkboxes[3]).not.toBeChecked();
  });

  it("switches to grid view when grid button is clicked", () => {
    render(
      <FlightResults
        results={[BaseFlight]}
        onSelect={vi.fn().mockResolvedValue(undefined)}
        onCompare={vi.fn()}
      />
    );

    const viewContainer = screen.getByTestId("flight-results-container");
    expect(viewContainer).toHaveAttribute("data-view-mode", "list");

    const gridButton = screen.getByRole("button", { name: /grid view/i });
    fireEvent.click(gridButton);

    const updatedContainer = screen.getByTestId("flight-results-container");
    expect(updatedContainer).toHaveAttribute("data-view-mode", "grid");
  });

  it("logs errors and resets optimistic state when selection fails", async () => {
    const onSelect = vi.fn().mockRejectedValue(new Error("network"));
    const telemetrySpy = vi.spyOn(ClientErrors, "recordClientErrorOnActiveSpan");

    render(
      <FlightResults results={[BaseFlight]} onSelect={onSelect} onCompare={vi.fn()} />
    );

    const selectButton = screen.getByRole("button", { name: /select flight/i });
    fireEvent.click(selectButton);

    expect(selectButton).toHaveTextContent("Selecting...");

    await waitFor(() => expect(selectButton).toHaveTextContent("Select Flight"));
    expect(telemetrySpy).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        action: "handleSelect",
        context: "FlightResults",
        itemId: "f1",
      })
    );
  });
});
