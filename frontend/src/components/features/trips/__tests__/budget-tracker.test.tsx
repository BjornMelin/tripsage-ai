import type { Budget, BudgetSummary } from "@/types/budget";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { BudgetTracker } from "../budget-tracker";

// Mock the stores
const mockBudget: Budget = {
  id: "budget-1",
  tripId: "trip-1",
  name: "Test Budget",
  totalAmount: 2000,
  currency: "USD",
  startDate: "2024-06-01",
  endDate: "2024-06-10",
  categories: [],
  isActive: true,
  createdAt: "2024-01-01T00:00:00Z",
  updatedAt: "2024-01-01T00:00:00Z",
};

const mockSummary: BudgetSummary = {
  totalBudget: 2000,
  totalSpent: 800,
  totalRemaining: 1200,
  percentageSpent: 40,
  spentByCategory: {
    flights: 400,
    accommodations: 300,
    food: 100,
    transportation: 0,
    activities: 0,
    shopping: 0,
    other: 0,
  },
  dailyAverage: 80,
  dailyLimit: 120,
  projectedTotal: 1600,
  isOverBudget: false,
  daysRemaining: 5,
};

vi.mock("@/stores/budget-store", () => ({
  useBudgetStore: vi.fn(() => ({
    budgets: { "budget-1": mockBudget },
    activeBudget: mockBudget,
    budgetSummary: mockSummary,
    budgetsByTrip: { "trip-1": ["budget-1"] },
    setActiveBudget: vi.fn(),
  })),
}));

vi.mock("@/stores/currency-store", () => ({
  useCurrencyStore: vi.fn(() => ({
    convertCurrency: vi.fn((amount: number) => amount),
    baseCurrency: "USD",
  })),
}));

describe("BudgetTracker", () => {
  it("renders budget information correctly", () => {
    render(<BudgetTracker tripId="trip-1" />);

    expect(screen.getByText("Test Budget")).toBeInTheDocument();
    expect(screen.getByText(/\$800\.00 of \$2,000\.00/)).toBeInTheDocument();
    expect(screen.getByText("40.0% used")).toBeInTheDocument();
    expect(screen.getByText(/\$1,200\.00 remaining/)).toBeInTheDocument();
  });

  it("displays daily metrics when available", () => {
    render(<BudgetTracker tripId="trip-1" />);

    expect(screen.getByText("Daily Average")).toBeInTheDocument();
    expect(screen.getByText("$80.00")).toBeInTheDocument();
    expect(screen.getByText("Daily Limit")).toBeInTheDocument();
    expect(screen.getByText("$120.00")).toBeInTheDocument();
  });

  it("shows projected total when different from spent", () => {
    render(<BudgetTracker tripId="trip-1" />);

    expect(screen.getByText("Projected Total")).toBeInTheDocument();
    expect(screen.getByText("$1,600.00")).toBeInTheDocument();
  });

  it("displays category breakdown", () => {
    render(<BudgetTracker tripId="trip-1" />);

    expect(screen.getByText("Category Breakdown")).toBeInTheDocument();
    expect(screen.getByText("flights")).toBeInTheDocument();
    expect(screen.getByText("$400.00")).toBeInTheDocument();
    expect(screen.getByText("accommodations")).toBeInTheDocument();
    expect(screen.getByText("$300.00")).toBeInTheDocument();
  });

  it("shows over budget warning when budget is exceeded", () => {
    const overBudgetSummary = {
      ...mockSummary,
      totalSpent: 2500,
      totalRemaining: -500,
      percentageSpent: 125,
      isOverBudget: true,
    };

    vi.mocked(
      vi.mocked(require("@/stores/budget-store").useBudgetStore)
    ).mockReturnValue({
      budgets: { "budget-1": mockBudget },
      activeBudget: mockBudget,
      budgetSummary: overBudgetSummary,
      budgetsByTrip: { "trip-1": ["budget-1"] },
      setActiveBudget: vi.fn(),
    });

    render(<BudgetTracker tripId="trip-1" />);

    expect(screen.getByText("Over Budget")).toBeInTheDocument();
  });

  it("calls onAddExpense when add expense button is clicked", () => {
    const onAddExpense = vi.fn();
    render(<BudgetTracker tripId="trip-1" onAddExpense={onAddExpense} />);

    fireEvent.click(screen.getByText("Add Expense"));
    expect(onAddExpense).toHaveBeenCalled();
  });

  it("shows create budget option when no budget exists", () => {
    vi.mocked(
      vi.mocked(require("@/stores/budget-store").useBudgetStore)
    ).mockReturnValue({
      budgets: {},
      activeBudget: null,
      budgetSummary: null,
      budgetsByTrip: {},
      setActiveBudget: vi.fn(),
    });

    const onCreateBudget = vi.fn();
    render(<BudgetTracker tripId="trip-1" onCreateBudget={onCreateBudget} />);

    expect(screen.getByText("No budget found for this trip")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Create Budget"));
    expect(onCreateBudget).toHaveBeenCalled();
  });

  it("handles different currency formatting", () => {
    const euroBudget = { ...mockBudget, currency: "EUR" };

    vi.mocked(
      vi.mocked(require("@/stores/budget-store").useBudgetStore)
    ).mockReturnValue({
      budgets: { "budget-1": euroBudget },
      activeBudget: euroBudget,
      budgetSummary: mockSummary,
      budgetsByTrip: { "trip-1": ["budget-1"] },
      setActiveBudget: vi.fn(),
    });

    render(<BudgetTracker tripId="trip-1" />);

    // Should format as EUR currency
    expect(screen.getByText(/EUR/)).toBeInTheDocument();
  });

  it("hides actions when showActions is false", () => {
    render(<BudgetTracker tripId="trip-1" showActions={false} />);

    expect(screen.queryByText("Add Expense")).not.toBeInTheDocument();
    expect(screen.queryByText("View Details")).not.toBeInTheDocument();
  });
});
