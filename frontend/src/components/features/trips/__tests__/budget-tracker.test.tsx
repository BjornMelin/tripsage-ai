/**
 * @fileoverview Comprehensive tests for BudgetTracker component, covering budget display,
 * category breakdowns, expense tracking, budget creation, editing, and edge cases
 * including empty states, error handling, and accessibility features.
 */

import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Budget } from "@/lib/schemas/budget";
import { useBudgetStore } from "@/stores/budget-store";
import { BudgetTracker } from "../budget-tracker";

// Mock the stores
const mockSetActiveBudget = vi.fn();

function defaultStore() {
  return {
    budgets: {
      "budget-1": {
        id: "budget-1",
        name: "Europe Trip Budget",
        totalAmount: 3000,
        currency: "USD",
        startDate: "2024-06-15",
        endDate: "2024-06-25",
        tripId: "trip-1",
        categories: [],
        isActive: true,
        createdAt: "2024-01-01",
        updatedAt: "2024-01-01",
      },
      "budget-2": {
        id: "budget-2",
        name: "Asia Adventure Budget",
        totalAmount: 2500,
        currency: "EUR",
        startDate: "2024-08-01",
        endDate: "2024-08-15",
        tripId: "trip-2",
        categories: [],
        isActive: false,
        createdAt: "2024-01-01",
        updatedAt: "2024-01-01",
      },
    } as Record<string, Budget>,
    activeBudget: {
      id: "budget-1",
      name: "Europe Trip Budget",
      totalAmount: 3000,
      currency: "USD",
      startDate: "2024-06-15",
      endDate: "2024-06-25",
      tripId: "trip-1",
      categories: [],
      isActive: true,
      createdAt: "2024-01-01",
      updatedAt: "2024-01-01",
    } as Budget,
    budgetSummary: {
      totalBudget: 3000,
      totalSpent: 1200,
      totalRemaining: 1800,
      percentageSpent: 40,
      spentByCategory: {
        food: 500,
        accommodation: 700,
      },
      dailyAverage: 120,
      dailyLimit: 150,
      projectedTotal: 1800,
      isOverBudget: false,
      daysRemaining: 10,
    },
    budgetsByTrip: {
      "trip-1": ["budget-1"],
      "trip-2": ["budget-2"],
    },
    setActiveBudget: mockSetActiveBudget,
  };
}

vi.mock("@/stores/budget-store", () => ({
  useBudgetStore: vi.fn(defaultStore),
}));

vi.mock("@/stores/currency-store", () => ({
  useCurrencyStore: vi.fn(() => ({
    baseCurrency: "USD",
  })),
}));

describe("BudgetTracker", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mock implementation to default for each test
    vi.mocked(useBudgetStore).mockImplementation(defaultStore as any);
  });

  describe("Budget Display", () => {
    it("should render active budget correctly", () => {
      render(<BudgetTracker />);

      expect(screen.getByText("Europe Trip Budget")).toBeInTheDocument();
      expect(
        screen.getByText("Budget for 2024-06-15 - 2024-06-25")
      ).toBeInTheDocument();
      expect(screen.getByText("$1,200.00 of $3,000.00")).toBeInTheDocument();
      expect(screen.getByText("40.0% used")).toBeInTheDocument();
      expect(screen.getByText("$1,800.00 remaining")).toBeInTheDocument();
    });

    it("should render specific budget by ID", () => {
      render(<BudgetTracker budgetId="budget-2" />);

      expect(screen.getByText("Asia Adventure Budget")).toBeInTheDocument();
      expect(
        screen.getByText("Budget for 2024-08-01 - 2024-08-15")
      ).toBeInTheDocument();
    });

    it("should render first budget for specific trip", () => {
      render(<BudgetTracker tripId="trip-1" />);

      expect(screen.getByText("Europe Trip Budget")).toBeInTheDocument();
    });

    it("falls back to active budget when trip has no budgets", () => {
      render(<BudgetTracker tripId="nonexistent-trip" />);

      // Component falls back to active budget rather than empty state
      expect(screen.getByText("Europe Trip Budget")).toBeInTheDocument();
      expect(
        screen.queryByText("No budget found for this trip")
      ).not.toBeInTheDocument();
    });
  });

  describe("Budget Progress and Indicators", () => {
    it("should display budget progress correctly", () => {
      render(<BudgetTracker />);

      const progressbars = screen.getAllByRole("progressbar");
      expect(progressbars.length).toBeGreaterThan(0);
      expect(progressbars[0]).toHaveAttribute("aria-valuenow", "40");
    });

    it("should show over budget text when remaining is negative", () => {
      // Mock over budget scenario
      vi.mocked(useBudgetStore).mockReturnValue({
        budgets: {
          "budget-1": {
            id: "budget-1",
            name: "Over Budget Trip",
            totalAmount: 1000,
            currency: "USD",
            startDate: "2024-06-15",
            endDate: "2024-06-25",
            tripId: "trip-1",
            categories: [],
            createdAt: "2024-01-01",
            updatedAt: "2024-01-01",
          },
        },
        activeBudget: {
          id: "budget-1",
          name: "Over Budget Trip",
          totalAmount: 1000,
          currency: "USD",
          startDate: "2024-06-15",
          endDate: "2024-06-25",
          tripId: "trip-1",
          categories: [],
          createdAt: "2024-01-01",
          updatedAt: "2024-01-01",
        },
        budgetSummary: {
          totalBudget: 1000,
          totalSpent: 1200,
          totalRemaining: -200,
          percentageSpent: 120,
          spentByCategory: {},
          dailyAverage: 120,
          dailyLimit: 100,
          projectedTotal: 1400,
          isOverBudget: true,
          daysRemaining: 5,
        },
        budgetsByTrip: { "trip-1": ["budget-1"] },
        setActiveBudget: mockSetActiveBudget,
      });

      render(<BudgetTracker />);

      // UI shows explicit over-budget amount in the summary line
      expect(screen.getByText("$200.00 over budget")).toBeInTheDocument();
    });

    it("should cap progress at 100%", () => {
      vi.mocked(useBudgetStore).mockReturnValue({
        budgets: {
          "budget-1": {
            id: "budget-1",
            name: "Over Budget Trip",
            totalAmount: 1000,
            currency: "USD",
            startDate: "2024-06-15",
            endDate: "2024-06-25",
            tripId: "trip-1",
            categories: [],
            createdAt: "2024-01-01",
            updatedAt: "2024-01-01",
          },
        },
        activeBudget: {
          id: "budget-1",
          name: "Over Budget Trip",
          totalAmount: 1000,
          currency: "USD",
          startDate: "2024-06-15",
          endDate: "2024-06-25",
          tripId: "trip-1",
          categories: [],
          createdAt: "2024-01-01",
          updatedAt: "2024-01-01",
        },
        budgetSummary: {
          totalBudget: 1000,
          totalSpent: 1500,
          totalRemaining: -500,
          percentageSpent: 150,
          spentByCategory: {},
          dailyAverage: 0,
          dailyLimit: 0,
          projectedTotal: 1500,
          isOverBudget: true,
          daysRemaining: 0,
        },
        budgetsByTrip: { "trip-1": ["budget-1"] },
        setActiveBudget: mockSetActiveBudget,
      });

      render(<BudgetTracker />);

      const progressbars = screen.getAllByRole("progressbar");
      expect(progressbars[0]).toHaveAttribute("aria-valuenow", "100");
    });
  });

  describe("Daily Metrics", () => {
    it("should display daily metrics when available", () => {
      render(<BudgetTracker />);

      expect(screen.getByText("Daily Average")).toBeInTheDocument();
      expect(screen.getByText("$120.00")).toBeInTheDocument();
      expect(screen.getByText("Daily Limit")).toBeInTheDocument();
      expect(screen.getByText("$150.00")).toBeInTheDocument();
    });

    it("should hide daily metrics when not available", () => {
      vi.mocked(useBudgetStore).mockReturnValue({
        budgets: {
          "budget-1": {
            id: "budget-1",
            name: "Simple Budget",
            totalAmount: 1000,
            currency: "USD",
            startDate: "2024-06-15",
            endDate: "2024-06-25",
            tripId: "trip-1",
            categories: [],
            createdAt: "2024-01-01",
            updatedAt: "2024-01-01",
          },
        },
        activeBudget: {
          id: "budget-1",
          name: "Simple Budget",
          totalAmount: 1000,
          currency: "USD",
          startDate: "2024-06-15",
          endDate: "2024-06-25",
          tripId: "trip-1",
          categories: [],
          createdAt: "2024-01-01",
          updatedAt: "2024-01-01",
        },
        budgetSummary: {
          totalBudget: 1000,
          totalSpent: 400,
          totalRemaining: 600,
          percentageSpent: 40,
          spentByCategory: {},
          dailyAverage: 0,
          dailyLimit: 0,
          projectedTotal: 400,
          isOverBudget: false,
          daysRemaining: 10,
        },
        budgetsByTrip: { "trip-1": ["budget-1"] },
        setActiveBudget: mockSetActiveBudget,
      });

      render(<BudgetTracker />);

      expect(screen.queryByText("Daily Average")).not.toBeInTheDocument();
      expect(screen.queryByText("Daily Limit")).not.toBeInTheDocument();
    });
  });

  describe("Projected Total", () => {
    it("should display projected total when different from spent", () => {
      render(<BudgetTracker />);

      expect(screen.getByText("Projected Total")).toBeInTheDocument();
      expect(screen.getByText("$1,800.00")).toBeInTheDocument();
    });

    it("should highlight projected total when over budget", () => {
      vi.mocked(useBudgetStore).mockReturnValue({
        budgets: {
          "budget-1": {
            id: "budget-1",
            name: "Projected Over Budget",
            totalAmount: 1000,
            currency: "USD",
            startDate: "2024-06-15",
            endDate: "2024-06-25",
            tripId: "trip-1",
            categories: [],
            createdAt: "2024-01-01",
            updatedAt: "2024-01-01",
          },
        },
        activeBudget: {
          id: "budget-1",
          name: "Projected Over Budget",
          totalAmount: 1000,
          currency: "USD",
          startDate: "2024-06-15",
          endDate: "2024-06-25",
          tripId: "trip-1",
          categories: [],
          createdAt: "2024-01-01",
          updatedAt: "2024-01-01",
        },
        budgetSummary: {
          totalBudget: 1000,
          totalSpent: 800,
          totalRemaining: 200,
          percentageSpent: 80,
          spentByCategory: {},
          dailyAverage: 80,
          dailyLimit: 100,
          projectedTotal: 1200,
          isOverBudget: false,
          daysRemaining: 5,
        },
        budgetsByTrip: { "trip-1": ["budget-1"] },
        setActiveBudget: mockSetActiveBudget,
      });

      render(<BudgetTracker />);

      const projectedAmount = screen.getByText("$1,200.00");
      expect(projectedAmount).toHaveClass("text-destructive");
    });

    it("should not display projected total when same as spent", () => {
      vi.mocked(useBudgetStore).mockReturnValue({
        budgets: {
          "budget-1": {
            id: "budget-1",
            name: "Simple Budget",
            totalAmount: 1000,
            currency: "USD",
            startDate: "2024-06-15",
            endDate: "2024-06-25",
            tripId: "trip-1",
            categories: [],
            createdAt: "2024-01-01",
            updatedAt: "2024-01-01",
          },
        },
        activeBudget: {
          id: "budget-1",
          name: "Simple Budget",
          totalAmount: 1000,
          currency: "USD",
          startDate: "2024-06-15",
          endDate: "2024-06-25",
          tripId: "trip-1",
          categories: [],
          createdAt: "2024-01-01",
          updatedAt: "2024-01-01",
        },
        budgetSummary: {
          totalBudget: 1000,
          totalSpent: 400,
          totalRemaining: 600,
          percentageSpent: 40,
          spentByCategory: {},
          dailyAverage: 0,
          dailyLimit: 0,
          projectedTotal: 400, // Same as spent
          isOverBudget: false,
          daysRemaining: 10,
        },
        budgetsByTrip: { "trip-1": ["budget-1"] },
        setActiveBudget: mockSetActiveBudget,
      });

      render(<BudgetTracker />);

      expect(screen.queryByText("Projected Total")).not.toBeInTheDocument();
    });
  });

  describe("Category Breakdown", () => {
    it("should display category breakdown when available", () => {
      render(<BudgetTracker />);

      expect(screen.getByText("Category Breakdown")).toBeInTheDocument();
      expect(screen.getByText("food")).toBeInTheDocument();
      expect(screen.getByText("$500.00")).toBeInTheDocument();
      expect(screen.getByText("accommodation")).toBeInTheDocument();
      expect(screen.getByText("$700.00")).toBeInTheDocument();
    });

    it("should hide category breakdown when no categories", () => {
      vi.mocked(useBudgetStore).mockReturnValue({
        budgets: {
          "budget-1": {
            id: "budget-1",
            name: "Simple Budget",
            totalAmount: 1000,
            currency: "USD",
            startDate: "2024-06-15",
            endDate: "2024-06-25",
            tripId: "trip-1",
            categories: [],
            createdAt: "2024-01-01",
            updatedAt: "2024-01-01",
          },
        },
        activeBudget: {
          id: "budget-1",
          name: "Simple Budget",
          totalAmount: 1000,
          currency: "USD",
          startDate: "2024-06-15",
          endDate: "2024-06-25",
          tripId: "trip-1",
          categories: [],
          createdAt: "2024-01-01",
          updatedAt: "2024-01-01",
        },
        budgetSummary: {
          totalBudget: 1000,
          totalSpent: 400,
          totalRemaining: 600,
          percentageSpent: 40,
          spentByCategory: {},
          dailyAverage: 0,
          dailyLimit: 0,
          projectedTotal: 400,
          isOverBudget: false,
          daysRemaining: 10,
        },
        budgetsByTrip: { "trip-1": ["budget-1"] },
        setActiveBudget: mockSetActiveBudget,
      });

      render(<BudgetTracker />);

      expect(screen.queryByText("Category Breakdown")).not.toBeInTheDocument();
    });
  });

  describe("Action Buttons", () => {
    it("should show action buttons by default", () => {
      render(<BudgetTracker />);

      expect(screen.getByText("View Details")).toBeInTheDocument();
    });

    it("should call onAddExpense when add expense button is clicked", () => {
      const mockOnAddExpense = vi.fn();
      render(<BudgetTracker onAddExpense={mockOnAddExpense} />);

      const addExpenseButton = screen.getByText("Add Expense");
      fireEvent.click(addExpenseButton);

      expect(mockOnAddExpense).toHaveBeenCalled();
    });

    it("should call setActiveBudget when view details button is clicked", () => {
      render(<BudgetTracker />);

      const viewDetailsButton = screen.getByText("View Details");
      fireEvent.click(viewDetailsButton);

      expect(mockSetActiveBudget).toHaveBeenCalledWith("budget-1");
    });

    it("should hide action buttons when showActions is false", () => {
      render(<BudgetTracker showActions={false} />);

      expect(screen.queryByText("View Details")).not.toBeInTheDocument();
      expect(screen.queryByText("Add Expense")).not.toBeInTheDocument();
    });

    it("should show create budget button when no active or trip budget exists", () => {
      const mockOnCreateBudget = vi.fn();
      // Override store to simulate no active budget and no budgets for trip
      vi.mocked(useBudgetStore).mockReturnValue({
        budgets: {},
        activeBudget: null as any,
        budgetSummary: null as any,
        budgetsByTrip: {},
        setActiveBudget: mockSetActiveBudget,
      });
      render(
        <BudgetTracker tripId="nonexistent-trip" onCreateBudget={mockOnCreateBudget} />
      );

      const createBudgetButton = screen.getByText("Create Budget");
      fireEvent.click(createBudgetButton);
      expect(mockOnCreateBudget).toHaveBeenCalled();
    });
  });

  describe("Currency Handling", () => {
    it("should format currency correctly for EUR", () => {
      render(<BudgetTracker budgetId="budget-2" />);

      // The budget-2 uses EUR currency
      expect(screen.getByText(/€0.00 of €2,500.00/)).toBeInTheDocument();
    });

    it("should use budget currency for formatting", () => {
      render(<BudgetTracker />);

      // Should format with USD since that's the budget's currency
      expect(screen.getByText(/\$1,200.00 of \$3,000.00/)).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("should handle budget without dates", () => {
      vi.mocked(useBudgetStore).mockReturnValue({
        budgets: {
          "budget-1": {
            id: "budget-1",
            name: "Budget Without Dates",
            totalAmount: 1000,
            currency: "USD",
            startDate: undefined,
            endDate: undefined,
            tripId: "trip-1",
            categories: [],
            createdAt: "2024-01-01",
            updatedAt: "2024-01-01",
          },
        },
        activeBudget: {
          id: "budget-1",
          name: "Budget Without Dates",
          totalAmount: 1000,
          currency: "USD",
          startDate: undefined,
          endDate: undefined,
          tripId: "trip-1",
          categories: [],
          createdAt: "2024-01-01",
          updatedAt: "2024-01-01",
        },
        budgetSummary: {
          totalBudget: 1000,
          totalSpent: 400,
          totalRemaining: 600,
          percentageSpent: 40,
          spentByCategory: {},
          dailyAverage: 0,
          dailyLimit: 0,
          projectedTotal: 400,
          isOverBudget: false,
          daysRemaining: 10,
        },
        budgetsByTrip: { "trip-1": ["budget-1"] },
        setActiveBudget: mockSetActiveBudget,
      });

      render(<BudgetTracker />);

      expect(screen.getByText("Budget for trip planning")).toBeInTheDocument();
    });

    it("should handle zero budget", () => {
      vi.mocked(useBudgetStore).mockReturnValue({
        budgets: {
          "budget-1": {
            id: "budget-1",
            name: "Zero Budget",
            totalAmount: 0,
            currency: "USD",
            startDate: "2024-06-15",
            endDate: "2024-06-25",
            tripId: "trip-1",
            categories: [],
            createdAt: "2024-01-01",
            updatedAt: "2024-01-01",
          },
        },
        activeBudget: {
          id: "budget-1",
          name: "Zero Budget",
          totalAmount: 0,
          currency: "USD",
          startDate: "2024-06-15",
          endDate: "2024-06-25",
          tripId: "trip-1",
          categories: [],
          createdAt: "2024-01-01",
          updatedAt: "2024-01-01",
        },
        budgetSummary: {
          totalBudget: 0,
          totalSpent: 0,
          totalRemaining: 0,
          percentageSpent: 0,
          spentByCategory: {},
          dailyAverage: 0,
          dailyLimit: 0,
          projectedTotal: 0,
          isOverBudget: false,
          daysRemaining: 10,
        },
        budgetsByTrip: { "trip-1": ["budget-1"] },
        setActiveBudget: mockSetActiveBudget,
      });

      render(<BudgetTracker />);

      expect(screen.getByText("$0.00 of $0.00")).toBeInTheDocument();
      expect(screen.getByText("0.0% used")).toBeInTheDocument();
    });

    it("should apply custom className", () => {
      const { container } = render(<BudgetTracker className="custom-budget-class" />);

      const card = container.firstChild as HTMLElement;
      expect(card).toHaveClass("custom-budget-class");
    });
  });

  describe("Accessibility", () => {
    it("should have proper roles and labels", () => {
      render(<BudgetTracker />);

      const progressbars = screen.getAllByRole("progressbar");
      expect(progressbars.length).toBeGreaterThan(0);
      expect(progressbars[0]).toHaveAttribute("aria-valuenow", "40");

      const buttons = screen.getAllByRole("button");
      expect(buttons.length).toBeGreaterThan(0);
    });

    it("should have proper heading structure", () => {
      render(<BudgetTracker />);

      const heading = screen.getByText("Europe Trip Budget");
      expect(heading.tagName).toBe("H3"); // CardTitle typically renders as h3
    });
  });
});
