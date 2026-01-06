/**
 * @fileoverview Expenses slice for the budget store.
 */

import type { Expense } from "@schemas/budget";
import type { StateCreator } from "zustand";
import type { BudgetState, BudgetStoreDeps } from "../types";

type BudgetExpensesSlice = Pick<
  BudgetState,
  "addExpense" | "expenses" | "removeExpense" | "setExpenses" | "updateExpense"
>;

export const createBudgetExpensesSlice =
  (deps: BudgetStoreDeps): StateCreator<BudgetState, [], [], BudgetExpensesSlice> =>
  (set) => ({
    addExpense: (expense) =>
      set((state) => {
        const budgetId = expense.budgetId;
        const currentExpenses = state.expenses[budgetId] || [];

        const newExpense: Expense = {
          ...expense,
          createdAt: expense.createdAt || deps.nowIso(),
          id: expense.id || deps.generateId(),
          updatedAt: deps.nowIso(),
        };

        return {
          expenses: {
            ...state.expenses,
            [budgetId]: [...currentExpenses, newExpense],
          },
        };
      }),

    expenses: {},

    removeExpense: (id, budgetId) =>
      set((state) => {
        const expenses = state.expenses[budgetId] || [];

        return {
          expenses: {
            ...state.expenses,
            [budgetId]: expenses.filter((exp) => exp.id !== id),
          },
        };
      }),

    setExpenses: (budgetId, expenses) =>
      set((state) => ({
        expenses: {
          ...state.expenses,
          [budgetId]: expenses,
        },
      })),

    updateExpense: (id, budgetId, updates) =>
      set((state) => {
        const expenses = state.expenses[budgetId] || [];
        const expenseIndex = expenses.findIndex((exp) => exp.id === id);

        if (expenseIndex === -1) {
          deps.logger.error("updateExpense called for missing expense", {
            budgetId,
            expenseId: id,
          });
          return state;
        }

        const updatedExpenses = [...expenses];
        updatedExpenses[expenseIndex] = {
          ...updatedExpenses[expenseIndex],
          ...updates,
          updatedAt: deps.nowIso(),
        };

        return {
          expenses: {
            ...state.expenses,
            [budgetId]: updatedExpenses,
          },
        };
      }),
  });
