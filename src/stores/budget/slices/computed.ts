/**
 * @fileoverview Initial computed fields for the budget store.
 */

import type { StateCreator } from "zustand";
import type { BudgetState } from "../types";

type BudgetComputedSlice = Pick<
  BudgetState,
  "activeBudget" | "budgetSummary" | "budgetsByTrip" | "recentExpenses"
>;

export const createBudgetComputedSlice: StateCreator<
  BudgetState,
  [],
  [],
  BudgetComputedSlice
> = () => ({
  activeBudget: null,
  budgetSummary: null,
  budgetsByTrip: {},
  recentExpenses: [],
});
