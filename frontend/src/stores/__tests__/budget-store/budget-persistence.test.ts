/** @vitest-environment jsdom */

import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { Budget, BudgetCategory, Expense } from "@/lib/schemas/budget";
import { useBudgetStore } from "@/stores/budget-store";

// Mock the store to avoid persistence issues in tests
vi.mock("zustand/middleware", () => ({
  // biome-ignore lint/suspicious/noExplicitAny: Test mock doesn't need type safety
  persist: (fn: any) => fn,
}));

describe("Budget Store - Budget Persistence", () => {
  beforeEach(() => {
    act(() => {
      useBudgetStore.setState({
        activeBudgetId: null,
        alerts: {},
        baseCurrency: "USD",
        budgets: {},
        currencies: {},
        expenses: {},
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
        categories: [
          {
            amount: 1500,
            category: "flights",
            id: "cat-1",
            percentage: 0,
            remaining: 1500,
            spent: 0,
          },
          {
            amount: 2000,
            category: "accommodations",
            id: "cat-2",
            percentage: 0,
            remaining: 2000,
            spent: 0,
          },
        ],
        createdAt: "2025-05-20T12:00:00Z",
        currency: "USD",
        id: "budget-1",
        isActive: true,
        name: "Summer Vacation",
        totalAmount: 5000,
        updatedAt: "2025-05-20T12:00:00Z",
      };

      act(() => {
        result.current.addBudget(mockBudget);
      });

      expect(result.current.budgets["budget-1"]).toMatchObject({
        ...mockBudget,
        updatedAt: expect.any(String),
      });
      expect(result.current.activeBudgetId).toBe("budget-1");
    });

    it("updates an existing budget", () => {
      const { result } = renderHook(() => useBudgetStore());

      const mockBudget: Budget = {
        categories: [
          {
            amount: 1500,
            category: "flights",
            id: "cat-1",
            percentage: 0,
            remaining: 1500,
            spent: 0,
          },
        ],
        createdAt: "2025-05-20T12:00:00Z",
        currency: "USD",
        id: "budget-1",
        isActive: true,
        name: "Summer Vacation",
        totalAmount: 5000,
        updatedAt: "2025-05-20T12:00:00Z",
      };

      act(() => {
        result.current.addBudget(mockBudget);
      });

      act(() => {
        result.current.updateBudget("budget-1", {
          name: "Updated Vacation",
          totalAmount: 6000,
        });
      });

      expect(result.current.budgets["budget-1"].name).toBe("Updated Vacation");
      expect(result.current.budgets["budget-1"].totalAmount).toBe(6000);
      expect(result.current.budgets["budget-1"].updatedAt).not.toBe(
        "2025-05-20T12:00:00Z"
      );
    });

    it("removes a budget", () => {
      const { result } = renderHook(() => useBudgetStore());

      const mockBudget: Budget = {
        categories: [],
        createdAt: "2025-05-20T12:00:00Z",
        currency: "USD",
        id: "budget-1",
        isActive: true,
        name: "Summer Vacation",
        totalAmount: 5000,
        updatedAt: "2025-05-20T12:00:00Z",
      };

      act(() => {
        result.current.addBudget(mockBudget);
        result.current.setExpenses("budget-1", [
          {
            amount: 500,
            budgetId: "budget-1",
            category: "flights",
            createdAt: "2025-05-20T12:00:00Z",
            currency: "USD",
            date: "2025-06-01",
            description: "Flight to NYC",
            id: "expense-1",
            isShared: false,
            updatedAt: "2025-05-20T12:00:00Z",
          },
        ]);
        result.current.setAlerts("budget-1", [
          {
            budgetId: "budget-1",
            createdAt: "2025-05-20T12:00:00Z",
            id: "alert-1",
            isRead: false,
            message: "Almost at budget limit",
            threshold: 80,
            type: "threshold",
          },
        ]);
      });

      act(() => {
        result.current.removeBudget("budget-1");
      });

      expect(result.current.budgets["budget-1"]).toBeUndefined();
      expect(result.current.expenses["budget-1"]).toBeUndefined();
      expect(result.current.alerts["budget-1"]).toBeUndefined();
      expect(result.current.activeBudgetId).toBeNull();
    });

    it("sets the active budget", () => {
      const { result: storeResult } = renderHook(() => useBudgetStore());

      act(() => {
        storeResult.current.addBudget({
          categories: [],
          createdAt: "2025-05-20T12:00:00Z",
          currency: "USD",
          id: "budget-1",
          isActive: true,
          name: "Summer Vacation",
          totalAmount: 5000,
          updatedAt: "2025-05-20T12:00:00Z",
        });

        storeResult.current.addBudget({
          categories: [],
          createdAt: "2025-05-20T12:00:00Z",
          currency: "USD",
          id: "budget-2",
          isActive: true,
          name: "Winter Vacation",
          totalAmount: 3000,
          updatedAt: "2025-05-20T12:00:00Z",
        });
      });

      act(() => {
        storeResult.current.setActiveBudget("budget-2");
      });

      expect(storeResult.current.activeBudgetId).toBe("budget-2");
    });
  });

  describe("Budget Categories", () => {
    it("adds a budget category", () => {
      const { result: storeResult } = renderHook(() => useBudgetStore());

      act(() => {
        storeResult.current.addBudget({
          categories: [],
          createdAt: "2025-05-20T12:00:00Z",
          currency: "USD",
          id: "budget-1",
          isActive: true,
          name: "Summer Vacation",
          totalAmount: 5000,
          updatedAt: "2025-05-20T12:00:00Z",
        });
      });

      const newCategory: BudgetCategory = {
        amount: 1500,
        category: "flights",
        id: "cat-1",
        percentage: 0,
        remaining: 1500,
        spent: 0,
      };

      act(() => {
        storeResult.current.addBudgetCategory("budget-1", newCategory);
      });

      expect(storeResult.current.budgets["budget-1"].categories).toContainEqual(
        newCategory
      );
      expect(storeResult.current.budgets["budget-1"].updatedAt).not.toBe(
        "2025-05-20T12:00:00Z"
      );
    });

    it("updates a budget category", () => {
      const { result: storeResult } = renderHook(() => useBudgetStore());

      act(() => {
        storeResult.current.addBudget({
          categories: [
            {
              amount: 1500,
              category: "flights",
              id: "cat-1",
              percentage: 0,
              remaining: 1500,
              spent: 0,
            },
          ],
          createdAt: "2025-05-20T12:00:00Z",
          currency: "USD",
          id: "budget-1",
          isActive: true,
          name: "Summer Vacation",
          totalAmount: 5000,
          updatedAt: "2025-05-20T12:00:00Z",
        });
      });

      act(() => {
        storeResult.current.updateBudgetCategory("budget-1", "cat-1", {
          amount: 2000,
          percentage: 25,
          remaining: 1500,
          spent: 500,
        });
      });

      expect(storeResult.current.budgets["budget-1"].categories[0].amount).toBe(2000);
      expect(storeResult.current.budgets["budget-1"].categories[0].spent).toBe(500);
      expect(storeResult.current.budgets["budget-1"].categories[0].remaining).toBe(
        1500
      );
      expect(storeResult.current.budgets["budget-1"].categories[0].percentage).toBe(25);
    });

    it("removes a budget category", () => {
      const { result: storeResult } = renderHook(() => useBudgetStore());

      act(() => {
        storeResult.current.addBudget({
          categories: [
            {
              amount: 1500,
              category: "flights",
              id: "cat-1",
              percentage: 0,
              remaining: 1500,
              spent: 0,
            },
            {
              amount: 2000,
              category: "accommodations",
              id: "cat-2",
              percentage: 0,
              remaining: 2000,
              spent: 0,
            },
          ],
          createdAt: "2025-05-20T12:00:00Z",
          currency: "USD",
          id: "budget-1",
          isActive: true,
          name: "Summer Vacation",
          totalAmount: 5000,
          updatedAt: "2025-05-20T12:00:00Z",
        });
      });

      act(() => {
        storeResult.current.removeBudgetCategory("budget-1", "cat-1");
      });

      expect(storeResult.current.budgets["budget-1"].categories.length).toBe(1);
      expect(storeResult.current.budgets["budget-1"].categories[0].id).toBe("cat-2");
    });
  });

  describe("Expenses", () => {
    it("sets expenses for a budget", () => {
      const { result } = renderHook(() => useBudgetStore());

      const mockExpenses: Expense[] = [
        {
          amount: 500,
          budgetId: "budget-1",
          category: "flights",
          createdAt: "2025-05-20T12:00:00Z",
          currency: "USD",
          date: "2025-06-01",
          description: "Flight to NYC",
          id: "expense-1",
          isShared: false,
          updatedAt: "2025-05-20T12:00:00Z",
        },
        {
          amount: 800,
          budgetId: "budget-1",
          category: "accommodations",
          createdAt: "2025-05-20T12:00:00Z",
          currency: "USD",
          date: "2025-06-01",
          description: "Hotel in NYC",
          id: "expense-2",
          isShared: false,
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
        amount: 500,
        budgetId: "budget-1",
        category: "flights",
        createdAt: "2025-05-20T12:00:00Z",
        currency: "USD",
        date: "2025-06-01",
        description: "Flight to NYC",
        id: "expense-1",
        isShared: false,
        updatedAt: "2025-05-20T12:00:00Z",
      };

      act(() => {
        result.current.addExpense(newExpense);
      });

      expect(result.current.expenses["budget-1"]).toContainEqual(
        expect.objectContaining({
          ...newExpense,
          updatedAt: expect.any(String),
        })
      );
    });

    it("updates an expense", () => {
      const { result } = renderHook(() => useBudgetStore());

      const expense: Expense = {
        amount: 500,
        budgetId: "budget-1",
        category: "flights",
        createdAt: "2025-05-20T12:00:00Z",
        currency: "USD",
        date: "2025-06-01",
        description: "Flight to NYC",
        id: "expense-1",
        isShared: false,
        updatedAt: "2025-05-20T12:00:00Z",
      };

      act(() => {
        result.current.addExpense(expense);
      });

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
      expect(result.current.expenses["budget-1"][0].updatedAt).not.toBe(
        "2025-05-20T12:00:00Z"
      );
    });

    it("removes an expense", () => {
      const { result: storeResult } = renderHook(() => useBudgetStore());

      act(() => {
        storeResult.current.addExpense({
          amount: 500,
          budgetId: "budget-1",
          category: "flights",
          createdAt: "2025-05-20T12:00:00Z",
          currency: "USD",
          date: "2025-06-01",
          description: "Flight to NYC",
          id: "expense-1",
          isShared: false,
          updatedAt: "2025-05-20T12:00:00Z",
        });

        storeResult.current.addExpense({
          amount: 800,
          budgetId: "budget-1",
          category: "accommodations",
          createdAt: "2025-05-20T12:00:00Z",
          currency: "USD",
          date: "2025-06-02",
          description: "Hotel in NYC",
          id: "expense-2",
          isShared: false,
          updatedAt: "2025-05-20T12:00:00Z",
        });
      });

      act(() => {
        storeResult.current.removeExpense("expense-1", "budget-1");
      });

      expect(storeResult.current.expenses["budget-1"].length).toBe(1);
      expect(storeResult.current.expenses["budget-1"][0].id).toBe("expense-2");
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

      expect(result.current.currencies.EUR.rate).toBe(0.85);
      expect(result.current.currencies.EUR.code).toBe("EUR");
      expect(result.current.currencies.EUR.lastUpdated).toBeDefined();
    });
  });

  describe("Alerts", () => {
    it("sets alerts for a budget", () => {
      const { result } = renderHook(() => useBudgetStore());

      const mockAlerts = [
        {
          budgetId: "budget-1",
          createdAt: "2025-05-20T12:00:00Z",
          id: "alert-1",
          isRead: false,
          message: "Almost at budget limit",
          threshold: 80,
          type: "threshold" as const,
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
        budgetId: "budget-1",
        createdAt: "2025-05-20T12:00:00Z",
        id: "alert-1",
        isRead: false,
        message: "Almost at budget limit",
        threshold: 80,
        type: "threshold" as const,
      };

      act(() => {
        result.current.addAlert(newAlert);
      });

      expect(result.current.alerts["budget-1"]).toContainEqual(newAlert);
    });

    it("marks an alert as read", () => {
      const { result } = renderHook(() => useBudgetStore());

      act(() => {
        result.current.addAlert({
          budgetId: "budget-1",
          createdAt: "2025-05-20T12:00:00Z",
          id: "alert-1",
          isRead: false,
          message: "Almost at budget limit",
          threshold: 80,
          type: "threshold" as const,
        });
      });

      act(() => {
        result.current.markAlertAsRead("alert-1", "budget-1");
      });

      expect(result.current.alerts["budget-1"][0].isRead).toBe(true);
    });

    it("clears alerts for a budget", () => {
      const { result } = renderHook(() => useBudgetStore());

      act(() => {
        result.current.addAlert({
          budgetId: "budget-1",
          createdAt: "2025-05-20T12:00:00Z",
          id: "alert-1",
          isRead: false,
          message: "Almost at budget limit",
          threshold: 80,
          type: "threshold" as const,
        });
      });

      act(() => {
        result.current.clearAlerts("budget-1");
      });

      expect(result.current.alerts["budget-1"]).toBeUndefined();
    });
  });
});
