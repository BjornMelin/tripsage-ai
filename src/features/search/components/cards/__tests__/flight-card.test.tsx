/** @vitest-environment jsdom */

import type { FlightResult } from "@schemas/search";
import { fireEvent, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { render } from "@/test/test-utils";
import {
  FLIGHT_COLORS,
  FlightCard,
  PredictionBadge,
  PriceChangeIcon,
} from "../flight-card";

const BaseFlight: FlightResult = {
  aircraft: "A320",
  airline: "Test Air",
  amenities: ["wifi", "meals", "entertainment"],
  arrival: { date: "2025-01-01", time: "10:00" },
  departure: { date: "2025-01-01", time: "08:00" },
  destination: { city: "Beta", code: "BBB", terminal: "T2" },
  duration: 120,
  emissions: { compared: "low", kg: 50 },
  flexibility: { changeable: true, refundable: false },
  flightNumber: "TA123",
  id: "f1",
  origin: { city: "Alpha", code: "AAA", terminal: "T1" },
  prediction: { confidence: 80, priceAlert: "buy_now", reason: "Stable prices" },
  price: { base: 100, currency: "USD", dealScore: 9, total: 120 },
  stops: { count: 0 },
};

describe("FlightCard", () => {
  const defaultProps = {
    flight: BaseFlight,
    isOptimisticSelecting: false,
    isPending: false,
    isSelected: false,
    onSelect: vi.fn(),
    onToggleComparison: vi.fn(),
    viewMode: "list" as const,
  };

  it("renders flight details correctly", () => {
    render(<FlightCard {...defaultProps} />);

    expect(screen.getByText("Test Air")).toBeInTheDocument();
    expect(screen.getByText("TA123")).toBeInTheDocument();
    expect(screen.getByText("08:00")).toBeInTheDocument();
    expect(screen.getByText("10:00")).toBeInTheDocument();
    expect(screen.getByText("AAA")).toBeInTheDocument();
    expect(screen.getByText("BBB")).toBeInTheDocument();
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
    expect(screen.getByText("$120")).toBeInTheDocument();
  });

  it("renders terminal info in list view", () => {
    render(<FlightCard {...defaultProps} viewMode="list" />);

    expect(screen.getByText("Terminal T1")).toBeInTheDocument();
    expect(screen.getByText("Terminal T2")).toBeInTheDocument();
  });

  it("hides terminal info in grid view", () => {
    render(<FlightCard {...defaultProps} viewMode="grid" />);

    expect(screen.queryByText("Terminal T1")).not.toBeInTheDocument();
    expect(screen.queryByText("Terminal T2")).not.toBeInTheDocument();
  });

  it("renders amenities in list view", () => {
    render(<FlightCard {...defaultProps} viewMode="list" />);

    expect(screen.getByText("WiFi")).toBeInTheDocument();
    expect(screen.getByText("Meals")).toBeInTheDocument();
    expect(screen.getByText("Entertainment")).toBeInTheDocument();
  });

  it("hides amenities in grid view", () => {
    render(<FlightCard {...defaultProps} viewMode="grid" />);

    expect(screen.queryByText("WiFi")).not.toBeInTheDocument();
    expect(screen.queryByText("Meals")).not.toBeInTheDocument();
    expect(screen.queryByText("Entertainment")).not.toBeInTheDocument();
  });

  it("shows Great Deal badge when dealScore >= 8", () => {
    render(<FlightCard {...defaultProps} />);

    expect(screen.getByText("Great Deal")).toBeInTheDocument();
  });

  it("hides Great Deal badge when dealScore < 8", () => {
    const flight = {
      ...BaseFlight,
      price: { ...BaseFlight.price, dealScore: 5 },
    };
    render(<FlightCard {...defaultProps} flight={flight} />);

    expect(screen.queryByText("Great Deal")).not.toBeInTheDocument();
  });

  it("calls onSelect when select button is clicked", () => {
    const onSelect = vi.fn();
    render(<FlightCard {...defaultProps} onSelect={onSelect} />);

    fireEvent.click(screen.getByRole("button", { name: /select flight/i }));

    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("disables select button when isPending", () => {
    render(<FlightCard {...defaultProps} isPending />);

    expect(screen.getByRole("button", { name: /select flight/i })).toBeDisabled();
  });

  it("shows Selecting… when isOptimisticSelecting", () => {
    render(<FlightCard {...defaultProps} isOptimisticSelecting />);

    expect(screen.getByRole("button", { name: /selecting/i })).toBeInTheDocument();
  });

  it("calls onToggleComparison when compare button is clicked", () => {
    const onToggleComparison = vi.fn();
    render(<FlightCard {...defaultProps} onToggleComparison={onToggleComparison} />);

    fireEvent.click(screen.getByRole("button", { name: /compare/i }));

    expect(onToggleComparison).toHaveBeenCalledTimes(1);
  });

  it("shows Selected state when isSelected", () => {
    render(<FlightCard {...defaultProps} isSelected />);

    expect(screen.getByRole("button", { name: /selected/i })).toBeInTheDocument();
  });

  it("shows checkbox as checked when isSelected", () => {
    render(<FlightCard {...defaultProps} isSelected />);

    expect(screen.getByRole("checkbox")).toBeChecked();
  });

  it("applies ring style when isSelected", () => {
    const { container } = render(<FlightCard {...defaultProps} isSelected />);

    const card = container.querySelector('[data-testid="flight-card-f1"]');
    expect(card).toHaveClass("ring-2", "ring-blue-500");
  });

  it("applies opacity style when isOptimisticSelecting", () => {
    const { container } = render(
      <FlightCard {...defaultProps} isOptimisticSelecting />
    );

    const card = container.querySelector('[data-testid="flight-card-f1"]');
    expect(card).toHaveClass("opacity-75");
  });

  it("renders promotions banner when flight has promotions", () => {
    const flight = {
      ...BaseFlight,
      promotions: {
        description: "Holiday Sale",
        savings: 50,
        type: "flash_deal" as const,
      },
    };
    render(<FlightCard {...defaultProps} flight={flight} />);

    expect(screen.getByText("Holiday Sale")).toBeInTheDocument();
  });

  it("renders AI prediction section in list view", () => {
    render(<FlightCard {...defaultProps} viewMode="list" />);

    expect(screen.getByText(/AI Prediction:.*Stable prices/)).toBeInTheDocument();
  });

  it("hides AI prediction section in grid view", () => {
    render(<FlightCard {...defaultProps} viewMode="grid" />);

    expect(screen.queryByText(/AI Prediction:/)).not.toBeInTheDocument();
  });

  it("displays emissions info in list view", () => {
    render(<FlightCard {...defaultProps} viewMode="list" />);

    expect(screen.getByText("50kg CO2")).toBeInTheDocument();
  });

  it("renders flight stops correctly", () => {
    render(<FlightCard {...defaultProps} />);
    expect(screen.getByText("Direct")).toBeInTheDocument();

    const flightWithStops = { ...BaseFlight, stops: { count: 1 } };
    render(<FlightCard {...defaultProps} flight={flightWithStops} />);
    expect(screen.getByText("1 stop")).toBeInTheDocument();
  });
});

describe("PriceChangeIcon", () => {
  it.each([
    {
      change: "down" as const,
      expectedClass: FLIGHT_COLORS.priceTrendDown,
      rotated: true,
    },
    {
      change: "up" as const,
      expectedClass: FLIGHT_COLORS.priceTrendUp,
      rotated: false,
    },
  ])("renders icon for $change prices", ({ change, expectedClass, rotated }) => {
    const { container } = render(<PriceChangeIcon change={change} />);
    const icon = container.querySelector("svg");
    expect(icon).toHaveClass(expectedClass);
    if (rotated) {
      expect(icon).toHaveClass("rotate-180");
    } else {
      expect(icon).not.toHaveClass("rotate-180");
    }
  });

  it.each([
    { change: "stable" as const, desc: "stable prices" },
    { change: undefined, desc: "undefined" },
  ])("renders nothing for $desc", ({ change }) => {
    const { container } = render(<PriceChangeIcon change={change} />);
    expect(container.querySelector("svg")).toBeNull();
  });
});

describe("PredictionBadge", () => {
  it.each([
    { confidence: 85, expectedText: "Book Now (85%)", priceAlert: "buy_now" as const },
    { confidence: 70, expectedText: "Wait (70%)", priceAlert: "wait" as const },
    { confidence: 50, expectedText: "Monitor (50%)", priceAlert: "neutral" as const },
  ])("renders $expectedText for $priceAlert alert", ({
    priceAlert,
    confidence,
    expectedText,
  }) => {
    render(<PredictionBadge prediction={{ confidence, priceAlert, reason: "test" }} />);
    expect(screen.getByText(expectedText)).toBeInTheDocument();
  });
});

describe("FLIGHT_COLORS", () => {
  it.each([
    { key: "airlineIcon" as const, value: "bg-blue-50 text-blue-700" },
    { key: "dealBadge" as const, value: "bg-green-50 text-green-700" },
    { key: "emissionLow" as const, value: "bg-green-500" },
    { key: "emissionMedium" as const, value: "bg-amber-500" },
    { key: "emissionHigh" as const, value: "bg-red-500" },
    { key: "priceTrendDown" as const, value: "text-green-700" },
    { key: "priceTrendUp" as const, value: "text-red-700" },
    { key: "promotionBadge" as const, value: "bg-red-600 text-white" },
  ])("exports $key as $value", ({ key, value }) => {
    expect(FLIGHT_COLORS[key]).toBe(value);
  });
});
