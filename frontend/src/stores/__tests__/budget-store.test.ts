import { describe, it, expect, beforeEach } from "vitest";
import { useBudgetStore } from "../budget-store";
import { act } from "@testing-library/react";
import { renderHook } from "@testing-library/react";
import type { Budget, Expense, BudgetCategory } from "@/types/budget";
import { vi } from "vitest";

// Mock the store to avoid persistence issues in tests
vi.mock("zustand/middleware", () => ({
  persist: (fn) => fn,
}));

describe("useBudgetStore", () => {
  // Clear the store before each test
  beforeEach(() => {
    act(() => {
      useBudgetStore.setState({
        budgets: {},
        activeBudgetId: null,
        expenses: {},
        baseCurrency: "USD",
        currencies: {},
        alerts: {},
      });
    });
  });

  describe("Budget Management", () => {
    it("initializes with default values", () => {
      const { result } = renderHook(() => useBudgetStore());

      expect(result.current.budgets).toEqual({});
      expect(result.current.activeBudgetId).toBeNull();
      expect(result.current.expenses).toEqual({});
      expect(result.current.baseCurrency).toBe("USD");
      expect(result.current.currencies).toEqual({});
      expect(result.current.alerts).toEqual({});
    });

    it("adds a new budget", () => {
      const { result } = renderHook(() => useBudgetStore());

      const mockBudget: Budget = {
        id: "budget-1",
        name: "Summer Vacation",
        totalAmount: 5000,
        currency: "USD",
        categories: [
          {
            id: "cat-1",
            category: "flights",
            amount: 1500,
            spent: 0,
            remaining: 1500,
            percentage: 0,
          },
          {
            id: "cat-2",
            category: "accommodations",
            amount: 2000,
            spent: 0,
            remaining: 2000,
            percentage: 0,
          },
        ],
        isActive: true,
        createdAt: "2025-05-20T12:00:00Z",
        updatedAt: "2025-05-20T12:00:00Z",
      };

      act(() => {
        result.current.addBudget(mockBudget);
      });

      expect(result.current.budgets["budget-1"]).toEqual(mockBudget);
      // First budget should automatically become active
      expect(result.current.activeBudgetId).toBe("budget-1");
    });

    it("updates an existing budget", () => {
      const { result } = renderHook(() => useBudgetStore());

      // Add a budget first
      const mockBudget: Budget = {
        id: "budget-1",
        name: "Summer Vacation",
        totalAmount: 5000,
        currency: "USD",
        categories: [
          {
            id: "cat-1",
            category: "flights",
            amount: 1500,
            spent: 0,
            remaining: 1500,
            percentage: 0,
          },
        ],
        isActive: true,
        createdAt: "2025-05-20T12:00:00Z",
        updatedAt: "2025-05-20T12:00:00Z",
      };

      act(() => {
        result.current.addBudget(mockBudget);
      });

      // Update the budget
      act(() => {
        result.current.updateBudget("budget-1", {
          name: "Updated Vacation",
          totalAmount: 6000,
        });
      });

      expect(result.current.budgets["budget-1"].name).toBe("Updated Vacation");
      expect(result.current.budgets["budget-1"].totalAmount).toBe(6000);
      // Make sure the updatedAt timestamp was updated
      expect(result.current.budgets["budget-1"].updatedAt).not.toBe(
        "2025-05-20T12:00:00Z"
      );
    });

    it("removes a budget", () => {
      const { result } = renderHook(() => useBudgetStore());

      // Add a budget
      const mockBudget: Budget = {
        id: "budget-1",
        name: "Summer Vacation",
        totalAmount: 5000,
        currency: "USD",
        categories: [],
        isActive: true,
        createdAt: "2025-05-20T12:00:00Z",
        updatedAt: "2025-05-20T12:00:00Z",
      };

      act(() => {
        result.current.addBudget(mockBudget);
        // Add some expenses for this budget
        result.current.setExpenses("budget-1", [
          {
            id: "expense-1",
            budgetId: "budget-1",
            category: "flights",
            description: "Flight to NYC",
            amount: 500,
            currency: "USD",
            date: "2025-06-01",
            isShared: false,
            createdAt: "2025-05-20T12:00:00Z",
            updatedAt: "2025-05-20T12:00:00Z",
          },
        ]);
        // Add some alerts for this budget
        result.current.setAlerts("budget-1", [
          {
            id: "alert-1",
            budgetId: "budget-1",
            type: "threshold",
            threshold: 80,
            message: "Almost at budget limit",
            isRead: false,
            createdAt: "2025-05-20T12:00:00Z",
          },
        ]);
      });

      // Remove the budget
      act(() => {
        result.current.removeBudget("budget-1");
      });

      expect(result.current.budgets["budget-1"]).toBeUndefined();
      expect(result.current.expenses["budget-1"]).toBeUndefined();
      expect(result.current.alerts["budget-1"]).toBeUndefined();
      expect(result.current.activeBudgetId).toBeNull();
    });

    it("sets the active budget", () => {
      const { result } = renderHook(() => useBudgetStore());

      // Add two budgets
      act(() => {
        result.current.addBudget({
          id: "budget-1",
          name: "Summer Vacation",
          totalAmount: 5000,
          currency: "USD",
          categories: [],
          isActive: true,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        });

        result.current.addBudget({
          id: "budget-2",
          name: "Winter Vacation",
          totalAmount: 3000,
          currency: "USD",
          categories: [],
          isActive: true,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        });
      });

      // Set the second budget as active
      act(() => {
        result.current.setActiveBudget("budget-2");
      });

      expect(result.current.activeBudgetId).toBe("budget-2");
    });
  });

  describe("Budget Categories", () => {
    it("adds a budget category", () => {
      const { result } = renderHook(() => useBudgetStore());

      // Add a budget first
      act(() => {
        result.current.addBudget({
          id: "budget-1",
          name: "Summer Vacation",
          totalAmount: 5000,
          currency: "USD",
          categories: [],
          isActive: true,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        });
      });

      // Add a category
      const newCategory: BudgetCategory = {
        id: "cat-1",
        category: "flights",
        amount: 1500,
        spent: 0,
        remaining: 1500,
        percentage: 0,
      };

      act(() => {
        result.current.addBudgetCategory("budget-1", newCategory);
      });

      expect(result.current.budgets["budget-1"].categories).toContainEqual(
        newCategory
      );
      // Check that updatedAt was changed
      expect(result.current.budgets["budget-1"].updatedAt).not.toBe(
        "2025-05-20T12:00:00Z"
      );
    });

    it("updates a budget category", () => {
      const { result } = renderHook(() => useBudgetStore());

      // Add a budget with a category
      act(() => {
        result.current.addBudget({
          id: "budget-1",
          name: "Summer Vacation",
          totalAmount: 5000,
          currency: "USD",
          categories: [
            {
              id: "cat-1",
              category: "flights",
              amount: 1500,
              spent: 0,
              remaining: 1500,
              percentage: 0,
            },
          ],
          isActive: true,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        });
      });

      // Update the category
      act(() => {
        result.current.updateBudgetCategory("budget-1", "cat-1", {
          amount: 2000,
          spent: 500,
          remaining: 1500,
          percentage: 25,
        });
      });

      expect(result.current.budgets["budget-1"].categories[0].amount).toBe(
        2000
      );
      expect(result.current.budgets["budget-1"].categories[0].spent).toBe(500);
      expect(result.current.budgets["budget-1"].categories[0].remaining).toBe(
        1500
      );
      expect(result.current.budgets["budget-1"].categories[0].percentage).toBe(
        25
      );
    });

    it("removes a budget category", () => {
      const { result } = renderHook(() => useBudgetStore());

      // Add a budget with two categories
      act(() => {
        result.current.addBudget({
          id: "budget-1",
          name: "Summer Vacation",
          totalAmount: 5000,
          currency: "USD",
          categories: [
            {
              id: "cat-1",
              category: "flights",
              amount: 1500,
              spent: 0,
              remaining: 1500,
              percentage: 0,
            },
            {
              id: "cat-2",
              category: "accommodations",
              amount: 2000,
              spent: 0,
              remaining: 2000,
              percentage: 0,
            },
          ],
          isActive: true,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        });
      });

      // Remove one category
      act(() => {
        result.current.removeBudgetCategory("budget-1", "cat-1");
      });

      expect(result.current.budgets["budget-1"].categories.length).toBe(1);
      expect(result.current.budgets["budget-1"].categories[0].id).toBe("cat-2");
    });
  });

  describe("Expenses", () => {
    it("sets expenses for a budget", () => {
      const { result } = renderHook(() => useBudgetStore());

      const mockExpenses: Expense[] = [
        {
          id: "expense-1",
          budgetId: "budget-1",
          category: "flights",
          description: "Flight to NYC",
          amount: 500,
          currency: "USD",
          date: "2025-06-01",
          isShared: false,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        },
        {
          id: "expense-2",
          budgetId: "budget-1",
          category: "accommodations",
          description: "Hotel in NYC",
          amount: 800,
          currency: "USD",
          date: "2025-06-01",
          isShared: false,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        },
      ];

      act(() => {
        result.current.setExpenses("budget-1", mockExpenses);
      });

      expect(result.current.expenses["budget-1"]).toEqual(mockExpenses);
    });

    it("adds an expense", () => {
      const { result } = renderHook(() => useBudgetStore());

      const newExpense: Expense = {
        id: "expense-1",
        budgetId: "budget-1",
        category: "flights",
        description: "Flight to NYC",
        amount: 500,
        currency: "USD",
        date: "2025-06-01",
        isShared: false,
        createdAt: "2025-05-20T12:00:00Z",
        updatedAt: "2025-05-20T12:00:00Z",
      };

      act(() => {
        result.current.addExpense(newExpense);
      });

      expect(result.current.expenses["budget-1"]).toContainEqual(newExpense);
    });

    it("updates an expense", () => {
      const { result } = renderHook(() => useBudgetStore());

      // Add an expense first
      const expense: Expense = {
        id: "expense-1",
        budgetId: "budget-1",
        category: "flights",
        description: "Flight to NYC",
        amount: 500,
        currency: "USD",
        date: "2025-06-01",
        isShared: false,
        createdAt: "2025-05-20T12:00:00Z",
        updatedAt: "2025-05-20T12:00:00Z",
      };

      act(() => {
        result.current.addExpense(expense);
      });

      // Update the expense
      act(() => {
        result.current.updateExpense("expense-1", "budget-1", {
          amount: 600,
          description: "Updated flight to NYC",
        });
      });

      expect(result.current.expenses["budget-1"][0].amount).toBe(600);
      expect(result.current.expenses["budget-1"][0].description).toBe(
        "Updated flight to NYC"
      );
      // Make sure updatedAt was changed
      expect(result.current.expenses["budget-1"][0].updatedAt).not.toBe(
        "2025-05-20T12:00:00Z"
      );
    });

    it("removes an expense", () => {
      const { result } = renderHook(() => useBudgetStore());

      // Add two expenses
      act(() => {
        result.current.addExpense({
          id: "expense-1",
          budgetId: "budget-1",
          category: "flights",
          description: "Flight to NYC",
          amount: 500,
          currency: "USD",
          date: "2025-06-01",
          isShared: false,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        });

        result.current.addExpense({
          id: "expense-2",
          budgetId: "budget-1",
          category: "accommodations",
          description: "Hotel in NYC",
          amount: 800,
          currency: "USD",
          date: "2025-06-02",
          isShared: false,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        });
      });

      // Remove one expense
      act(() => {
        result.current.removeExpense("expense-1", "budget-1");
      });

      expect(result.current.expenses["budget-1"].length).toBe(1);
      expect(result.current.expenses["budget-1"][0].id).toBe("expense-2");
    });
  });

  describe("Currency", () => {
    it("sets the base currency", () => {
      const { result } = renderHook(() => useBudgetStore());

      act(() => {
        result.current.setBaseCurrency("EUR");
      });

      expect(result.current.baseCurrency).toBe("EUR");
    });

    it("updates currency rates", () => {
      const { result } = renderHook(() => useBudgetStore());

      act(() => {
        result.current.updateCurrencyRate("EUR", 0.85);
      });

      expect(result.current.currencies["EUR"].rate).toBe(0.85);
      expect(result.current.currencies["EUR"].code).toBe("EUR");
      expect(result.current.currencies["EUR"].lastUpdated).toBeDefined();
    });
  });

  describe("Alerts", () => {
    it("sets alerts for a budget", () => {
      const { result } = renderHook(() => useBudgetStore());

      const mockAlerts = [
        {
          id: "alert-1",
          budgetId: "budget-1",
          type: "threshold" as const,
          threshold: 80,
          message: "Almost at budget limit",
          isRead: false,
          createdAt: "2025-05-20T12:00:00Z",
        },
      ];

      act(() => {
        result.current.setAlerts("budget-1", mockAlerts);
      });

      expect(result.current.alerts["budget-1"]).toEqual(mockAlerts);
    });

    it("adds an alert", () => {
      const { result } = renderHook(() => useBudgetStore());

      const newAlert = {
        id: "alert-1",
        budgetId: "budget-1",
        type: "threshold" as const,
        threshold: 80,
        message: "Almost at budget limit",
        isRead: false,
        createdAt: "2025-05-20T12:00:00Z",
      };

      act(() => {
        result.current.addAlert(newAlert);
      });

      expect(result.current.alerts["budget-1"]).toContainEqual(newAlert);
    });

    it("marks an alert as read", () => {
      const { result } = renderHook(() => useBudgetStore());

      // Add an alert first
      act(() => {
        result.current.addAlert({
          id: "alert-1",
          budgetId: "budget-1",
          type: "threshold" as const,
          threshold: 80,
          message: "Almost at budget limit",
          isRead: false,
          createdAt: "2025-05-20T12:00:00Z",
        });
      });

      // Mark as read
      act(() => {
        result.current.markAlertAsRead("alert-1", "budget-1");
      });

      expect(result.current.alerts["budget-1"][0].isRead).toBe(true);
    });

    it("clears alerts for a budget", () => {
      const { result } = renderHook(() => useBudgetStore());

      // Add some alerts
      act(() => {
        result.current.addAlert({
          id: "alert-1",
          budgetId: "budget-1",
          type: "threshold" as const,
          threshold: 80,
          message: "Almost at budget limit",
          isRead: false,
          createdAt: "2025-05-20T12:00:00Z",
        });
      });

      // Clear alerts
      act(() => {
        result.current.clearAlerts("budget-1");
      });

      expect(result.current.alerts["budget-1"]).toBeUndefined();
    });
  });

  describe("Computed Properties", () => {
    it("returns the active budget", () => {
      const { result } = renderHook(() => useBudgetStore());

      const mockBudget: Budget = {
        id: "budget-1",
        name: "Summer Vacation",
        totalAmount: 5000,
        currency: "USD",
        categories: [],
        isActive: true,
        createdAt: "2025-05-20T12:00:00Z",
        updatedAt: "2025-05-20T12:00:00Z",
      };

      act(() => {
        result.current.addBudget(mockBudget);
        result.current.setActiveBudget("budget-1");
      });

      expect(result.current.activeBudget).toEqual(mockBudget);
    });

    it("calculates the budget summary for the active budget", () => {
      const { result } = renderHook(() => useBudgetStore());

      // Add a budget with categories
      act(() => {
        result.current.addBudget({
          id: "budget-1",
          name: "Summer Vacation",
          totalAmount: 5000,
          currency: "USD",
          categories: [
            {
              id: "cat-1",
              category: "flights",
              amount: 1500,
              spent: 0,
              remaining: 1500,
              percentage: 0,
            },
            {
              id: "cat-2",
              category: "accommodations",
              amount: 2000,
              spent: 0,
              remaining: 2000,
              percentage: 0,
            },
          ],
          isActive: true,
          startDate: "2025-06-01",
          endDate: "2025-06-15",
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        });
        result.current.setActiveBudget("budget-1");

        // Add some expenses
        result.current.addExpense({
          id: "expense-1",
          budgetId: "budget-1",
          category: "flights",
          description: "Flight to NYC",
          amount: 1000,
          currency: "USD",
          date: "2025-06-01",
          isShared: false,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        });

        result.current.addExpense({
          id: "expense-2",
          budgetId: "budget-1",
          category: "accommodations",
          description: "Hotel in NYC",
          amount: 800,
          currency: "USD",
          date: "2025-06-02",
          isShared: false,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        });
      });

      // Since the current date affects daysRemaining and some calculations,
      // we'll only test non-time-dependent properties
      expect(result.current.budgetSummary).toBeDefined();
      expect(result.current.budgetSummary?.totalBudget).toBe(5000);
      expect(result.current.budgetSummary?.totalSpent).toBe(1800);
      expect(result.current.budgetSummary?.totalRemaining).toBe(3200);
      expect(result.current.budgetSummary?.percentageSpent).toBe(36);

      // Verify the spent by category
      expect(result.current.budgetSummary?.spentByCategory.flights).toBe(1000);
      expect(result.current.budgetSummary?.spentByCategory.accommodations).toBe(
        800
      );
    });

    it("returns budgets by trip ID", () => {
      const { result } = renderHook(() => useBudgetStore());

      // Add budgets with trip IDs
      act(() => {
        result.current.addBudget({
          id: "budget-1",
          name: "Summer Vacation",
          tripId: "trip-1",
          totalAmount: 5000,
          currency: "USD",
          categories: [],
          isActive: true,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        });

        result.current.addBudget({
          id: "budget-2",
          name: "Winter Vacation",
          tripId: "trip-2",
          totalAmount: 3000,
          currency: "USD",
          categories: [],
          isActive: true,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        });

        result.current.addBudget({
          id: "budget-3",
          name: "Trip 1 - Food Budget",
          tripId: "trip-1",
          totalAmount: 1000,
          currency: "USD",
          categories: [],
          isActive: true,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        });
      });

      expect(result.current.budgetsByTrip["trip-1"]).toContain("budget-1");
      expect(result.current.budgetsByTrip["trip-1"]).toContain("budget-3");
      expect(result.current.budgetsByTrip["trip-1"].length).toBe(2);

      expect(result.current.budgetsByTrip["trip-2"]).toContain("budget-2");
      expect(result.current.budgetsByTrip["trip-2"].length).toBe(1);
    });

    it("returns recent expenses", () => {
      const { result } = renderHook(() => useBudgetStore());

      // Add expenses with different dates
      act(() => {
        result.current.addExpense({
          id: "expense-1",
          budgetId: "budget-1",
          category: "flights",
          description: "Flight to NYC",
          amount: 500,
          currency: "USD",
          date: "2025-06-01",
          isShared: false,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        });

        result.current.addExpense({
          id: "expense-2",
          budgetId: "budget-1",
          category: "accommodations",
          description: "Hotel in NYC",
          amount: 800,
          currency: "USD",
          date: "2025-06-05",
          isShared: false,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        });

        result.current.addExpense({
          id: "expense-3",
          budgetId: "budget-2",
          category: "food",
          description: "Dinner in NYC",
          amount: 100,
          currency: "USD",
          date: "2025-06-10",
          isShared: false,
          createdAt: "2025-05-20T12:00:00Z",
          updatedAt: "2025-05-20T12:00:00Z",
        });
      });

      // Recent expenses should be sorted by date (newest first)
      expect(result.current.recentExpenses.length).toBe(3);
      expect(result.current.recentExpenses[0].id).toBe("expense-3"); // June 10
      expect(result.current.recentExpenses[1].id).toBe("expense-2"); // June 5
      expect(result.current.recentExpenses[2].id).toBe("expense-1"); // June 1
    });
  });
});
