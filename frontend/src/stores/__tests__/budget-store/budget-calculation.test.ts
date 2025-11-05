import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { Budget } from "@/lib/schemas/budget";
import {
  selectActiveBudgetFrom,
  selectBudgetSummaryFrom,
  selectBudgetsByTripFrom,
  selectRecentExpensesFrom,
  useBudgetStore,
} from "@/stores/budget-store";
import { resetBudgetStore } from "./_shared";

// Note: persist middleware is already mocked globally in test-setup.ts

describe("Budget Store - Budget Calculation", () => {
  beforeEach(() => {
    resetBudgetStore();
  });

  describe("Computed Properties", () => {
    it("returns the active budget", () => {
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
        result.current.setActiveBudget("budget-1");
      });

      // Validate via pure selector as well to avoid middleware quirks
      expect(selectActiveBudgetFrom(useBudgetStore.getState())).toMatchObject({
        ...mockBudget,
        updatedAt: expect.any(String),
      });
    });

    it("calculates the budget summary for the active budget", () => {
      const { result } = renderHook(() => useBudgetStore());

      act(() => {
        result.current.addBudget({
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
          endDate: "2025-06-15",
          id: "budget-1",
          isActive: true,
          name: "Summer Vacation",
          startDate: "2025-06-01",
          totalAmount: 5000,
          updatedAt: "2025-05-20T12:00:00Z",
        });
        result.current.setActiveBudget("budget-1");

        result.current.addExpense({
          amount: 1000,
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

        result.current.addExpense({
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

      const summary = selectBudgetSummaryFrom(useBudgetStore.getState());
      expect(summary).toBeDefined();
      expect(summary?.totalBudget).toBe(5000);
      expect(summary?.totalSpent).toBe(1800);
      expect(summary?.totalRemaining).toBe(3200);
      expect(summary?.percentageSpent).toBe(36);
      expect(summary?.spentByCategory.flights).toBe(1000);
      expect(summary?.spentByCategory.accommodations).toBe(800);
    });

    it("returns budgets by trip ID", () => {
      const { result } = renderHook(() => useBudgetStore());

      act(() => {
        result.current.addBudget({
          categories: [],
          createdAt: "2025-05-20T12:00:00Z",
          currency: "USD",
          id: "budget-1",
          isActive: true,
          name: "Summer Vacation",
          totalAmount: 5000,
          tripId: "trip-1",
          updatedAt: "2025-05-20T12:00:00Z",
        });

        result.current.addBudget({
          categories: [],
          createdAt: "2025-05-20T12:00:00Z",
          currency: "USD",
          id: "budget-2",
          isActive: true,
          name: "Winter Vacation",
          totalAmount: 3000,
          tripId: "trip-2",
          updatedAt: "2025-05-20T12:00:00Z",
        });

        result.current.addBudget({
          categories: [],
          createdAt: "2025-05-20T12:00:00Z",
          currency: "USD",
          id: "budget-3",
          isActive: true,
          name: "Trip 1 - Food Budget",
          totalAmount: 1000,
          tripId: "trip-1",
          updatedAt: "2025-05-20T12:00:00Z",
        });
      });

      const byTrip = selectBudgetsByTripFrom(useBudgetStore.getState());
      expect(byTrip).toBeDefined();
      expect(byTrip["trip-1"]).toBeDefined();
      expect(Array.isArray(byTrip["trip-1"])).toBe(true);
      expect(byTrip["trip-1"]).toContain("budget-1");
      expect(byTrip["trip-1"]).toContain("budget-3");
      expect(byTrip["trip-1"].length).toBe(2);
      expect(byTrip["trip-2"]).toBeDefined();
      expect(Array.isArray(byTrip["trip-2"])).toBe(true);
      expect(byTrip["trip-2"]).toContain("budget-2");
      expect(byTrip["trip-2"].length).toBe(1);
    });

    it("returns recent expenses", () => {
      const { result } = renderHook(() => useBudgetStore());

      act(() => {
        result.current.addExpense({
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

        result.current.addExpense({
          amount: 800,
          budgetId: "budget-1",
          category: "accommodations",
          createdAt: "2025-05-20T12:00:00Z",
          currency: "USD",
          date: "2025-06-05",
          description: "Hotel in NYC",
          id: "expense-2",
          isShared: false,
          updatedAt: "2025-05-20T12:00:00Z",
        });

        result.current.addExpense({
          amount: 100,
          budgetId: "budget-2",
          category: "food",
          createdAt: "2025-05-20T12:00:00Z",
          currency: "USD",
          date: "2025-06-10",
          description: "Dinner in NYC",
          id: "expense-3",
          isShared: false,
          updatedAt: "2025-05-20T12:00:00Z",
        });
      });

      // Validate via pure selector to avoid middleware quirks
      const recentExpenses = selectRecentExpensesFrom(useBudgetStore.getState());
      expect(recentExpenses.length).toBeGreaterThanOrEqual(3);
      expect(recentExpenses.length).toBeLessThanOrEqual(10);
      const expenseIds = recentExpenses.map((e) => e.id);
      expect(expenseIds).toContain("expense-1");
      expect(expenseIds).toContain("expense-2");
      expect(expenseIds).toContain("expense-3");
      // Most recent first (sorted by date descending)
      expect(recentExpenses[0].id).toBe("expense-3");
      expect(recentExpenses[1].id).toBe("expense-2");
      expect(recentExpenses[2].id).toBe("expense-1");
    });
  });
});
