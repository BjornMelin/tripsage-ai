/** @vitest-environment jsdom */

import type { Budget } from "@schemas/budget";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useBudgetStore } from "@/stores/budget-store";
import { BudgetTracker } from "../budget-tracker";

// Mock the stores
const MockSetActiveBudget = vi.fn();

function DefaultStore() {
  return {
    activeBudget: {
      categories: [],
      createdAt: "2024-01-01",
      currency: "USD",
      endDate: "2024-06-25",
      id: "budget-1",
      isActive: true,
      name: "Europe Trip Budget",
      startDate: "2024-06-15",
      totalAmount: 3000,
      tripId: "trip-1",
      updatedAt: "2024-01-01",
    } as Budget,
    budgetSummary: {
      dailyAverage: 120,
      dailyLimit: 150,
      daysRemaining: 10,
      isOverBudget: false,
      percentageSpent: 40,
      projectedTotal: 1800,
      spentByCategory: {
        accommodation: 700,
        food: 500,
      },
      totalBudget: 3000,
      totalRemaining: 1800,
      totalSpent: 1200,
    },
    budgets: {
      "budget-1": {
        categories: [],
        createdAt: "2024-01-01",
        currency: "USD",
        endDate: "2024-06-25",
        id: "budget-1",
        isActive: true,
        name: "Europe Trip Budget",
        startDate: "2024-06-15",
        totalAmount: 3000,
        tripId: "trip-1",
        updatedAt: "2024-01-01",
      },
      "budget-2": {
        categories: [],
        createdAt: "2024-01-01",
        currency: "EUR",
        endDate: "2024-08-15",
        id: "budget-2",
        isActive: false,
        name: "Asia Adventure Budget",
        startDate: "2024-08-01",
        totalAmount: 2500,
        tripId: "trip-2",
        updatedAt: "2024-01-01",
      },
    } as Record<string, Budget>,
    budgetsByTrip: {
      "trip-1": ["budget-1"],
      "trip-2": ["budget-2"],
    },
    setActiveBudget: MockSetActiveBudget,
  };
}

vi.mock("@/stores/budget-store", () => ({
  useBudgetStore: vi.fn(DefaultStore),
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
    vi.mocked(useBudgetStore).mockImplementation(DefaultStore);
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
        activeBudget: {
          categories: [],
          createdAt: "2024-01-01",
          currency: "USD",
          endDate: "2024-06-25",
          id: "budget-1",
          name: "Over Budget Trip",
          startDate: "2024-06-15",
          totalAmount: 1000,
          tripId: "trip-1",
          updatedAt: "2024-01-01",
        },
        budgetSummary: {
          dailyAverage: 120,
          dailyLimit: 100,
          daysRemaining: 5,
          isOverBudget: true,
          percentageSpent: 120,
          projectedTotal: 1400,
          spentByCategory: {},
          totalBudget: 1000,
          totalRemaining: -200,
          totalSpent: 1200,
        },
        budgets: {
          "budget-1": {
            categories: [],
            createdAt: "2024-01-01",
            currency: "USD",
            endDate: "2024-06-25",
            id: "budget-1",
            name: "Over Budget Trip",
            startDate: "2024-06-15",
            totalAmount: 1000,
            tripId: "trip-1",
            updatedAt: "2024-01-01",
          },
        },
        budgetsByTrip: { "trip-1": ["budget-1"] },
        setActiveBudget: MockSetActiveBudget,
      });

      render(<BudgetTracker />);

      // UI shows explicit over-budget amount in the summary line
      expect(screen.getByText("$200.00 over budget")).toBeInTheDocument();
    });

    it("should cap progress at 100%", () => {
      vi.mocked(useBudgetStore).mockReturnValue({
        activeBudget: {
          categories: [],
          createdAt: "2024-01-01",
          currency: "USD",
          endDate: "2024-06-25",
          id: "budget-1",
          name: "Over Budget Trip",
          startDate: "2024-06-15",
          totalAmount: 1000,
          tripId: "trip-1",
          updatedAt: "2024-01-01",
        },
        budgetSummary: {
          dailyAverage: 0,
          dailyLimit: 0,
          daysRemaining: 0,
          isOverBudget: true,
          percentageSpent: 150,
          projectedTotal: 1500,
          spentByCategory: {},
          totalBudget: 1000,
          totalRemaining: -500,
          totalSpent: 1500,
        },
        budgets: {
          "budget-1": {
            categories: [],
            createdAt: "2024-01-01",
            currency: "USD",
            endDate: "2024-06-25",
            id: "budget-1",
            name: "Over Budget Trip",
            startDate: "2024-06-15",
            totalAmount: 1000,
            tripId: "trip-1",
            updatedAt: "2024-01-01",
          },
        },
        budgetsByTrip: { "trip-1": ["budget-1"] },
        setActiveBudget: MockSetActiveBudget,
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
        activeBudget: {
          categories: [],
          createdAt: "2024-01-01",
          currency: "USD",
          endDate: "2024-06-25",
          id: "budget-1",
          name: "Simple Budget",
          startDate: "2024-06-15",
          totalAmount: 1000,
          tripId: "trip-1",
          updatedAt: "2024-01-01",
        },
        budgetSummary: {
          dailyAverage: 0,
          dailyLimit: 0,
          daysRemaining: 10,
          isOverBudget: false,
          percentageSpent: 40,
          projectedTotal: 400,
          spentByCategory: {},
          totalBudget: 1000,
          totalRemaining: 600,
          totalSpent: 400,
        },
        budgets: {
          "budget-1": {
            categories: [],
            createdAt: "2024-01-01",
            currency: "USD",
            endDate: "2024-06-25",
            id: "budget-1",
            name: "Simple Budget",
            startDate: "2024-06-15",
            totalAmount: 1000,
            tripId: "trip-1",
            updatedAt: "2024-01-01",
          },
        },
        budgetsByTrip: { "trip-1": ["budget-1"] },
        setActiveBudget: MockSetActiveBudget,
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
        activeBudget: {
          categories: [],
          createdAt: "2024-01-01",
          currency: "USD",
          endDate: "2024-06-25",
          id: "budget-1",
          name: "Projected Over Budget",
          startDate: "2024-06-15",
          totalAmount: 1000,
          tripId: "trip-1",
          updatedAt: "2024-01-01",
        },
        budgetSummary: {
          dailyAverage: 80,
          dailyLimit: 100,
          daysRemaining: 5,
          isOverBudget: false,
          percentageSpent: 80,
          projectedTotal: 1200,
          spentByCategory: {},
          totalBudget: 1000,
          totalRemaining: 200,
          totalSpent: 800,
        },
        budgets: {
          "budget-1": {
            categories: [],
            createdAt: "2024-01-01",
            currency: "USD",
            endDate: "2024-06-25",
            id: "budget-1",
            name: "Projected Over Budget",
            startDate: "2024-06-15",
            totalAmount: 1000,
            tripId: "trip-1",
            updatedAt: "2024-01-01",
          },
        },
        budgetsByTrip: { "trip-1": ["budget-1"] },
        setActiveBudget: MockSetActiveBudget,
      });

      render(<BudgetTracker />);

      const projectedAmount = screen.getByText("$1,200.00");
      expect(projectedAmount).toHaveClass("text-destructive");
    });

    it("should not display projected total when same as spent", () => {
      vi.mocked(useBudgetStore).mockReturnValue({
        activeBudget: {
          categories: [],
          createdAt: "2024-01-01",
          currency: "USD",
          endDate: "2024-06-25",
          id: "budget-1",
          name: "Simple Budget",
          startDate: "2024-06-15",
          totalAmount: 1000,
          tripId: "trip-1",
          updatedAt: "2024-01-01",
        },
        budgetSummary: {
          dailyAverage: 0,
          dailyLimit: 0,
          daysRemaining: 10,
          isOverBudget: false,
          percentageSpent: 40,
          projectedTotal: 400, // Same as spent
          spentByCategory: {},
          totalBudget: 1000,
          totalRemaining: 600,
          totalSpent: 400,
        },
        budgets: {
          "budget-1": {
            categories: [],
            createdAt: "2024-01-01",
            currency: "USD",
            endDate: "2024-06-25",
            id: "budget-1",
            name: "Simple Budget",
            startDate: "2024-06-15",
            totalAmount: 1000,
            tripId: "trip-1",
            updatedAt: "2024-01-01",
          },
        },
        budgetsByTrip: { "trip-1": ["budget-1"] },
        setActiveBudget: MockSetActiveBudget,
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
        activeBudget: {
          categories: [],
          createdAt: "2024-01-01",
          currency: "USD",
          endDate: "2024-06-25",
          id: "budget-1",
          name: "Simple Budget",
          startDate: "2024-06-15",
          totalAmount: 1000,
          tripId: "trip-1",
          updatedAt: "2024-01-01",
        },
        budgetSummary: {
          dailyAverage: 0,
          dailyLimit: 0,
          daysRemaining: 10,
          isOverBudget: false,
          percentageSpent: 40,
          projectedTotal: 400,
          spentByCategory: {},
          totalBudget: 1000,
          totalRemaining: 600,
          totalSpent: 400,
        },
        budgets: {
          "budget-1": {
            categories: [],
            createdAt: "2024-01-01",
            currency: "USD",
            endDate: "2024-06-25",
            id: "budget-1",
            name: "Simple Budget",
            startDate: "2024-06-15",
            totalAmount: 1000,
            tripId: "trip-1",
            updatedAt: "2024-01-01",
          },
        },
        budgetsByTrip: { "trip-1": ["budget-1"] },
        setActiveBudget: MockSetActiveBudget,
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

      expect(MockSetActiveBudget).toHaveBeenCalledWith("budget-1");
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
        activeBudget: null,
        budgetSummary: null,
        budgets: {},
        budgetsByTrip: {},
        setActiveBudget: MockSetActiveBudget,
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
        activeBudget: {
          categories: [],
          createdAt: "2024-01-01",
          currency: "USD",
          endDate: undefined,
          id: "budget-1",
          name: "Budget Without Dates",
          startDate: undefined,
          totalAmount: 1000,
          tripId: "trip-1",
          updatedAt: "2024-01-01",
        },
        budgetSummary: {
          dailyAverage: 0,
          dailyLimit: 0,
          daysRemaining: 10,
          isOverBudget: false,
          percentageSpent: 40,
          projectedTotal: 400,
          spentByCategory: {},
          totalBudget: 1000,
          totalRemaining: 600,
          totalSpent: 400,
        },
        budgets: {
          "budget-1": {
            categories: [],
            createdAt: "2024-01-01",
            currency: "USD",
            endDate: undefined,
            id: "budget-1",
            name: "Budget Without Dates",
            startDate: undefined,
            totalAmount: 1000,
            tripId: "trip-1",
            updatedAt: "2024-01-01",
          },
        },
        budgetsByTrip: { "trip-1": ["budget-1"] },
        setActiveBudget: MockSetActiveBudget,
      });

      render(<BudgetTracker />);

      expect(screen.getByText("Budget for trip planning")).toBeInTheDocument();
    });

    it("should handle zero budget", () => {
      vi.mocked(useBudgetStore).mockReturnValue({
        activeBudget: {
          categories: [],
          createdAt: "2024-01-01",
          currency: "USD",
          endDate: "2024-06-25",
          id: "budget-1",
          name: "Zero Budget",
          startDate: "2024-06-15",
          totalAmount: 0,
          tripId: "trip-1",
          updatedAt: "2024-01-01",
        },
        budgetSummary: {
          dailyAverage: 0,
          dailyLimit: 0,
          daysRemaining: 10,
          isOverBudget: false,
          percentageSpent: 0,
          projectedTotal: 0,
          spentByCategory: {},
          totalBudget: 0,
          totalRemaining: 0,
          totalSpent: 0,
        },
        budgets: {
          "budget-1": {
            categories: [],
            createdAt: "2024-01-01",
            currency: "USD",
            endDate: "2024-06-25",
            id: "budget-1",
            name: "Zero Budget",
            startDate: "2024-06-15",
            totalAmount: 0,
            tripId: "trip-1",
            updatedAt: "2024-01-01",
          },
        },
        budgetsByTrip: { "trip-1": ["budget-1"] },
        setActiveBudget: MockSetActiveBudget,
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
