/**
 * @fileoverview Budgets slice for the budget store.
 */

import type { Budget, BudgetCategory } from "@schemas/budget";
import type { StateCreator } from "zustand";
import type { BudgetState, BudgetStoreDeps } from "../types";

type BudgetBudgetsSlice = Pick<
  BudgetState,
  | "activeBudgetId"
  | "addBudget"
  | "addBudgetCategory"
  | "budgets"
  | "removeBudget"
  | "removeBudgetCategory"
  | "setActiveBudget"
  | "setBudgets"
  | "updateBudget"
  | "updateBudgetCategory"
>;

export const createBudgetBudgetsSlice =
  (deps: BudgetStoreDeps): StateCreator<BudgetState, [], [], BudgetBudgetsSlice> =>
  (set) => ({
    activeBudgetId: null,

    addBudget: (budget) =>
      set((state) => {
        const newBudget: Budget = {
          ...budget,
          createdAt: budget.createdAt || deps.nowIso(),
          id: budget.id || deps.generateId(),
          updatedAt: deps.nowIso(),
        };

        return {
          // If this is the first budget, set it as active
          activeBudgetId:
            state.activeBudgetId === null ? newBudget.id : state.activeBudgetId,
          budgets: {
            ...state.budgets,
            [newBudget.id]: newBudget,
          },
        };
      }),

    addBudgetCategory: (budgetId, category) =>
      set((state) => {
        const budget = state.budgets[budgetId];
        if (!budget) {
          deps.logger.error("addBudgetCategory called for missing budget", {
            budgetId,
          });
          return state;
        }

        const newCategory: BudgetCategory = {
          ...category,
          id: category.id || deps.generateId(),
        };

        return {
          budgets: {
            ...state.budgets,
            [budgetId]: {
              ...budget,
              categories: [...budget.categories, newCategory],
              updatedAt: deps.nowIso(),
            },
          },
        };
      }),

    budgets: {},

    removeBudget: (id) =>
      set((state) => {
        const newBudgets = { ...state.budgets };
        delete newBudgets[id];

        const newExpenses = { ...state.expenses };
        delete newExpenses[id];

        const newAlerts = { ...state.alerts };
        delete newAlerts[id];

        // If the active budget is removed, set the active budget to null
        const newActiveBudgetId =
          state.activeBudgetId === id ? null : state.activeBudgetId;

        return {
          activeBudgetId: newActiveBudgetId,
          alerts: newAlerts,
          budgets: newBudgets,
          expenses: newExpenses,
        };
      }),

    removeBudgetCategory: (budgetId, categoryId) =>
      set((state) => {
        const budget = state.budgets[budgetId];
        if (!budget) {
          deps.logger.error("removeBudgetCategory called for missing budget", {
            budgetId,
            categoryId,
          });
          return state;
        }

        return {
          budgets: {
            ...state.budgets,
            [budgetId]: {
              ...budget,
              categories: budget.categories.filter((cat) => cat.id !== categoryId),
              updatedAt: deps.nowIso(),
            },
          },
        };
      }),

    setActiveBudget: (id) => set({ activeBudgetId: id }),

    setBudgets: (budgets) => set({ budgets }),

    updateBudget: (id, updates) =>
      set((state) => {
        const budget = state.budgets[id];
        if (!budget) {
          deps.logger.error("updateBudget called for missing budget", { budgetId: id });
          return state;
        }

        const updatedBudget: Budget = {
          ...budget,
          ...updates,
          updatedAt: deps.nowIso(),
        };

        return {
          budgets: {
            ...state.budgets,
            [id]: updatedBudget,
          },
        };
      }),

    updateBudgetCategory: (budgetId, categoryId, updates) =>
      set((state) => {
        const budget = state.budgets[budgetId];
        if (!budget) {
          deps.logger.error("updateBudgetCategory called for missing budget", {
            budgetId,
            categoryId,
          });
          return state;
        }

        const categoryIndex = budget.categories.findIndex(
          (cat) => cat.id === categoryId
        );
        if (categoryIndex === -1) {
          deps.logger.error("updateBudgetCategory called for missing category", {
            budgetId,
            categoryId,
          });
          return state;
        }

        const updatedCategories = [...budget.categories];
        updatedCategories[categoryIndex] = {
          ...updatedCategories[categoryIndex],
          ...updates,
        };

        return {
          budgets: {
            ...state.budgets,
            [budgetId]: {
              ...budget,
              categories: updatedCategories,
              updatedAt: deps.nowIso(),
            },
          },
        };
      }),
  });
