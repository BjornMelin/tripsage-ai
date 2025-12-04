/** @vitest-environment jsdom */

import type { FlightResult } from "@schemas/search";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
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

    const checkboxes = screen.getAllByRole("checkbox");
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
});
