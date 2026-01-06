/**
 * @fileoverview Zustand store for budget state and actions.
 */

"use client";

import type { Budget, BudgetSummary, Expense } from "@schemas/budget";
import { create } from "zustand";
import { devtools, persist } from "zustand/middleware";
import { generateId, getCurrentTimestamp } from "@/features/shared/store/helpers";
import { createStoreLogger } from "@/lib/telemetry/store-logger";
import { withComputed } from "@/stores/middleware/computed";
import {
  calculateBudgetSummary,
  computeBudgetState,
  getBudgetsByTrip,
  selectRecentExpensesFromExpenses,
} from "./computed";
import { createBudgetAlertsSlice } from "./slices/alerts";
import { createBudgetBudgetsSlice } from "./slices/budgets";
import { createBudgetComputedSlice } from "./slices/computed";
import { createBudgetCurrencySlice } from "./slices/currency";
import { createBudgetExpensesSlice } from "./slices/expenses";
import type { BudgetState, BudgetStoreDeps } from "./types";

const logger = createStoreLogger({ storeName: "budget-store" });

const deps: BudgetStoreDeps = {
  generateId: () => generateId(12),
  logger,
  nowIso: () => getCurrentTimestamp(),
};

export const useBudgetStore = create<BudgetState>()(
  devtools(
    persist(
      withComputed({ compute: computeBudgetState }, (...args) => ({
        ...createBudgetComputedSlice(...args),
        ...createBudgetBudgetsSlice(deps)(...args),
        ...createBudgetExpensesSlice(deps)(...args),
        ...createBudgetCurrencySlice(deps)(...args),
        ...createBudgetAlertsSlice(deps)(...args),
      })),
      {
        name: "budget-storage",
        partialize: (state) => ({
          activeBudgetId: state.activeBudgetId,
          baseCurrency: state.baseCurrency,
          budgets: state.budgets,
          expenses: state.expenses,
        }),
      }
    ),
    { name: "BudgetStore" }
  )
);

// Selector hooks for computed properties
export const useActiveBudget = () => useBudgetStore((state) => state.activeBudget);
export const useBudgetSummary = () => useBudgetStore((state) => state.budgetSummary);
export const useBudgetsByTrip = () => useBudgetStore((state) => state.budgetsByTrip);
export const useRecentExpenses = () => useBudgetStore((state) => state.recentExpenses);

/**
 * Compute the active budget from a given budget state.
 *
 * @param state - The budget store state snapshot.
 * @returns The active budget or null.
 */
export const selectActiveBudgetFrom = (state: BudgetState): Budget | null => {
  const { activeBudgetId, budgets } = state;
  return activeBudgetId ? (budgets[activeBudgetId] ?? null) : null;
};

/**
 * Compute the budget summary for the current active budget.
 *
 * @param state - The budget store state snapshot.
 * @returns The summary or null when no active budget exists.
 */
export const selectBudgetSummaryFrom = (state: BudgetState): BudgetSummary | null => {
  const active = selectActiveBudgetFrom(state);
  if (!active) return null;
  const budgetExpenses = state.expenses[active.id] ?? [];
  return calculateBudgetSummary(active, budgetExpenses);
};

/**
 * Compute a map of tripId to the list of budget IDs belonging to that trip.
 *
 * @param state - The budget store state snapshot.
 * @returns A map of trip IDs to budget ID arrays.
 */
export const selectBudgetsByTripFrom = (
  state: BudgetState
): Record<string, string[]> => {
  return getBudgetsByTrip(state.budgets);
};

/**
 * Compute the 10 most recent expenses across all budgets.
 *
 * @param state - The budget store state snapshot.
 * @returns A list of recent expenses sorted by date descending.
 */
export const selectRecentExpensesFrom = (state: BudgetState): Expense[] => {
  return selectRecentExpensesFromExpenses(state.expenses);
};
