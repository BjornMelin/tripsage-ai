/**
 * @fileoverview Zustand store for budget state and actions.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { nowIso, secureId } from "@/lib/security/random";
import type {
  Budget,
  BudgetAlert,
  BudgetCategory,
  BudgetSummary,
  CurrencyRate,
  Expense,
  ExpenseCategory,
} from "@/lib/schemas/budget";
import type { CurrencyCode } from "@/types/currency";

// Helper functions
const GENERATE_ID = () => secureId(12);
const GET_CURRENT_TIMESTAMP = () => nowIso();

/**
 * Interface for the budget state.
 */
interface BudgetState {
  // Budgets
  budgets: Record<string, Budget>;
  activeBudgetId: string | null;

  // Expenses
  expenses: Record<string, Expense[]>;

  // Currency
  baseCurrency: CurrencyCode;
  currencies: Record<CurrencyCode, CurrencyRate>;

  // Alerts
  alerts: Record<string, BudgetAlert[]>;

  // Computed properties
  activeBudget: Budget | null;
  budgetSummary: BudgetSummary | null;
  budgetsByTrip: Record<string, string[]>;
  recentExpenses: Expense[];

  // Budget actions
  setBudgets: (budgets: Record<string, Budget>) => void;
  addBudget: (budget: Budget) => void;
  updateBudget: (id: string, updates: Partial<Budget>) => void;
  removeBudget: (id: string) => void;
  setActiveBudget: (id: string | null) => void;

  // Budget category actions
  updateBudgetCategory: (
    budgetId: string,
    categoryId: string,
    updates: Partial<BudgetCategory>
  ) => void;
  addBudgetCategory: (budgetId: string, category: BudgetCategory) => void;
  removeBudgetCategory: (budgetId: string, categoryId: string) => void;

  // Expense actions
  setExpenses: (budgetId: string, expenses: Expense[]) => void;
  addExpense: (expense: Expense) => void;
  updateExpense: (id: string, budgetId: string, updates: Partial<Expense>) => void;
  removeExpense: (id: string, budgetId: string) => void;

  // Currency actions
  setBaseCurrency: (currency: CurrencyCode) => void;
  setCurrencies: (currencies: Record<CurrencyCode, CurrencyRate>) => void;
  updateCurrencyRate: (code: CurrencyCode, rate: number) => void;

  // Alert actions
  setAlerts: (budgetId: string, alerts: BudgetAlert[]) => void;
  addAlert: (alert: BudgetAlert) => void;
  markAlertAsRead: (id: string, budgetId: string) => void;
  clearAlerts: (budgetId: string) => void;
}

/**
 * Calculate the budget summary.
 * 
 * @param budget - The budget to calculate the summary for.
 * @param expenses - The expenses to calculate the summary for.
 * @returns The budget summary.
 */
const CALCULATE_BUDGET_SUMMARY = (
  budget: Budget,
  expenses: Expense[]
): BudgetSummary => {
  const totalBudget = budget.totalAmount;
  const totalSpent = expenses.reduce((sum, expense) => sum + expense.amount, 0);
  const totalRemaining = totalBudget - totalSpent;
  const percentageSpent = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0;

  // Calculate spent by category
  const spentByCategory = expenses.reduce(
    (acc, expense) => {
      const category = expense.category;
      acc[category] = (acc[category] || 0) + expense.amount;
      return acc;
    },
    {} as Record<ExpenseCategory, number>
  );

  // Calculate days remaining if dates are provided
  let daysRemaining: number | undefined;
  if (budget.startDate && budget.endDate) {
    const endDate = new Date(budget.endDate);
    const today = new Date();
    const diffTime = endDate.getTime() - today.getTime();
    daysRemaining = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    daysRemaining = daysRemaining < 0 ? 0 : daysRemaining;
  }

  // Calculate daily metrics
  const startDate = budget.startDate ? new Date(budget.startDate) : undefined;
  const endDate = budget.endDate ? new Date(budget.endDate) : undefined;

  let dailyAverage = 0;
  let dailyLimit = 0;
  let projectedTotal = totalSpent;

  if (startDate && endDate) {
    const totalDays = Math.max(
      1,
      Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24))
    );
    const elapsedDays = Math.max(
      1,
      Math.ceil((Date.now() - startDate.getTime()) / (1000 * 60 * 60 * 24))
    );

    dailyAverage = elapsedDays > 0 ? totalSpent / elapsedDays : 0;
    dailyLimit =
      daysRemaining && daysRemaining > 0 ? totalRemaining / daysRemaining : 0;
    projectedTotal = dailyAverage * totalDays;
  }

  return {
    dailyAverage,
    dailyLimit,
    daysRemaining,
    isOverBudget: totalRemaining < 0,
    percentageSpent,
    projectedTotal,
    spentByCategory,
    totalBudget,
    totalRemaining,
    totalSpent,
  };
};

/**
 * The budget store.
 */
export const useBudgetStore = create<BudgetState>()(
  persist(
    (set, get) => ({
      // Computed properties
      get activeBudget(): Budget | null {
        const { activeBudgetId, budgets } = get();
        return activeBudgetId ? budgets[activeBudgetId] || null : null;
      },
      activeBudgetId: null,

      /**
       * Add an alert to the budget.
       * 
       * @param alert - The alert to add.
       * @returns The updated state.
       */
      addAlert: (alert) =>
        set((state) => {
          const budgetId = alert.budgetId;
          const currentAlerts = state.alerts[budgetId] || [];

          const newAlert = {
            ...alert,
            createdAt: alert.createdAt || GET_CURRENT_TIMESTAMP(),
            id: alert.id || GENERATE_ID(),
            isRead: false,
          };

          return {
            alerts: {
              ...state.alerts,
              [budgetId]: [...currentAlerts, newAlert],
            },
          };
        }),

      /**
       * Add a budget to the budget.
       * 
       * @param budget - The budget to add.
       * @returns The updated state.
       */
      addBudget: (budget) =>
        set((state) => {
          const newBudget = {
            ...budget,
            createdAt: budget.createdAt || GET_CURRENT_TIMESTAMP(),
            id: budget.id || GENERATE_ID(),
            updatedAt: GET_CURRENT_TIMESTAMP(),
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

      /**
       * Add a budget category to the budget.
       * 
       * @param budgetId - The ID of the budget to add the category to.
       * @param category - The category to add.
       * @returns The updated state.
       */
      addBudgetCategory: (budgetId, category) =>
        set((state) => {
          const budget = state.budgets[budgetId];
          if (!budget) return state;

          const newCategory = {
            ...category,
            id: category.id || GENERATE_ID(),
          };

          return {
            budgets: {
              ...state.budgets,
              [budgetId]: {
                ...budget,
                categories: [...budget.categories, newCategory],
                updatedAt: GET_CURRENT_TIMESTAMP(),
              },
            },
          };
        }),

      /**
       * Add an expense to the budget.
       * 
       * @param expense - The expense to add.
       * @returns The updated state.
       */
      addExpense: (expense) =>
        set((state) => {
          const budgetId = expense.budgetId;
          const currentExpenses = state.expenses[budgetId] || [];

          const newExpense = {
            ...expense,
            createdAt: expense.createdAt || GET_CURRENT_TIMESTAMP(),
            id: expense.id || GENERATE_ID(),
            updatedAt: GET_CURRENT_TIMESTAMP(),
          };

          return {
            expenses: {
              ...state.expenses,
              [budgetId]: [...currentExpenses, newExpense],
            },
          };
        }),
      alerts: {},
      baseCurrency: "USD",

      /**
       * Get the budget summary.
       * 
       * @returns The budget summary.
       */
      get budgetSummary(): BudgetSummary | null {
        const { activeBudget } = get();
        const { expenses } = get();

        if (!activeBudget) return null;

        const budgetExpenses = expenses[activeBudget.id] || [];
        return CALCULATE_BUDGET_SUMMARY(activeBudget, budgetExpenses);
      },
      // Initial state
      budgets: {},

      /**
       * Get the budgets by trip.
       * 
       * @returns The budgets by trip.
       */
      get budgetsByTrip(): Record<string, string[]> {
        const { budgets } = get();

        return Object.values(budgets).reduce(
          (acc, budget) => {
            if (budget.tripId) {
              if (!acc[budget.tripId]) {
                acc[budget.tripId] = [];
              }
              acc[budget.tripId].push(budget.id);
            }
            return acc;
          },
          {} as Record<string, string[]>
        );
      },

      /**
       * Clear the alerts for a budget.
       * 
       * @param budgetId - The ID of the budget to clear the alerts for.
       * @returns The updated state.
       */
      clearAlerts: (budgetId) =>
        set((state) => {
          const newAlerts = { ...state.alerts };
          delete newAlerts[budgetId];

          return {
            alerts: newAlerts,
          };
        }),
      currencies: {},
      expenses: {},

      /**
       * Mark an alert as read.
       * 
       * @param id - The ID of the alert to mark as read.
       * @param budgetId - The ID of the budget to mark the alert for.
       * @returns The updated state.
       */
      markAlertAsRead: (id, budgetId) =>
        set((state) => {
          const alerts = state.alerts[budgetId] || [];
          const alertIndex = alerts.findIndex((alert) => alert.id === id);

          if (alertIndex === -1) return state;

          const updatedAlerts = [...alerts];
          updatedAlerts[alertIndex] = {
            ...updatedAlerts[alertIndex],
            isRead: true,
          };

          return {
            alerts: {
              ...state.alerts,
              [budgetId]: updatedAlerts,
            },
          };
        }),

      /**
       * Get the recent expenses.
       * 
       * @returns The recent expenses.
       */
      get recentExpenses(): Expense[] {
        const { expenses } = get();

        // Flatten all expenses and sort by date (newest first)
        return Object.values(expenses)
          .flat()
          .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
          .slice(0, 10); // Return the 10 most recent expenses
      },

      /**
       * Remove a budget.
       * 
       * @param id - The ID of the budget to remove.
       * @returns The updated state.
       */
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

      /**
       * Remove a budget category.
       * 
       * @param budgetId - The ID of the budget to remove the category from.
       * @param categoryId - The ID of the category to remove.
       * @returns The updated state.
       */
      removeBudgetCategory: (budgetId, categoryId) =>
        set((state) => {
          const budget = state.budgets[budgetId];
          if (!budget) return state;

          return {
            budgets: {
              ...state.budgets,
              [budgetId]: {
                ...budget,
                categories: budget.categories.filter((cat) => cat.id !== categoryId),
                updatedAt: GET_CURRENT_TIMESTAMP(),
              },
            },
          };
        }),

      /**
       * Remove an expense.
       * 
       * @param id - The ID of the expense to remove.
       * @param budgetId - The ID of the budget to remove the expense from.
       * @returns The updated state.
       */
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

      /**
       * Set the active budget.
       * 
       * @param id - The ID of the budget to set as active.
       * @returns The updated state.
       */
      setActiveBudget: (id) => set({ activeBudgetId: id }),

      // Alert actions
      /**
       * Set the alerts for a budget.
       * 
       * @param budgetId - The ID of the budget to set the alerts for.
       * @param alerts - The alerts to set.
       * @returns The updated state.
       */
      setAlerts: (budgetId, alerts) =>
        set((state) => ({
          alerts: {
            ...state.alerts,
            [budgetId]: alerts,
          },
        })),

      // Currency actions
      setBaseCurrency: (currency) => set({ baseCurrency: currency }),

      // Budget actions
      setBudgets: (budgets) => set({ budgets }),

      /**
       * Set the currencies.
       * 
       * @param currencies - The currencies to set.
       * @returns The updated state.
       */
      setCurrencies: (currencies) => set({ currencies }),

      // Expense actions
      /**
       * Set the expenses for a budget.
       * 
       * @param budgetId - The ID of the budget to set the expenses for.
       * @param expenses - The expenses to set.
       * @returns The updated state.
       */
      setExpenses: (budgetId, expenses) =>
        set((state) => ({
          expenses: {
            ...state.expenses,
            [budgetId]: expenses,
          },
        })),

      /**
       * Update a budget.
       * 
       * @param id - The ID of the budget to update.
       * @param updates - The updates to apply to the budget.
       * @returns The updated state.
       */
      updateBudget: (id, updates) =>
        set((state) => {
          const budget = state.budgets[id];
          if (!budget) return state;

          const updatedBudget = {
            ...budget,
            ...updates,
            updatedAt: GET_CURRENT_TIMESTAMP(),
          };

          return {
            budgets: {
              ...state.budgets,
              [id]: updatedBudget,
            },
          };
        }),

      // Budget category actions
      /**
       * Update a budget category.
       * 
       * @param budgetId - The ID of the budget to update the category for.
       * @param categoryId - The ID of the category to update.
       * @param updates - The updates to apply to the category.
       * @returns The updated state.
       */
      updateBudgetCategory: (budgetId, categoryId, updates) =>
        set((state) => {
          const budget = state.budgets[budgetId];
          if (!budget) return state;

          const categoryIndex = budget.categories.findIndex(
            (cat) => cat.id === categoryId
          );
          if (categoryIndex === -1) return state;

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
                updatedAt: GET_CURRENT_TIMESTAMP(),
              },
            },
          };
        }),

      /**
       * Update a currency rate.
       * 
       * @param code - The code of the currency to update.
       * @param rate - The rate to set for the currency.
       * @returns The updated state.
       */
      updateCurrencyRate: (code, rate) =>
        set((state) => ({
          currencies: {
            ...state.currencies,
            [code]: {
              code,
              lastUpdated: GET_CURRENT_TIMESTAMP(),
              rate,
            },
          },
        })),

      /**
       * Update an expense.
       * 
       * @param id - The ID of the expense to update.
       * @param budgetId - The ID of the budget to update the expense for.
       * @param updates - The updates to apply to the expense.
       * @returns The updated state.
       */
      updateExpense: (id, budgetId, updates) =>
        set((state) => {
          const expenses = state.expenses[budgetId] || [];
          const expenseIndex = expenses.findIndex((exp) => exp.id === id);

          if (expenseIndex === -1) return state;

          const updatedExpenses = [...expenses];
          updatedExpenses[expenseIndex] = {
            ...updatedExpenses[expenseIndex],
            ...updates,
            updatedAt: GET_CURRENT_TIMESTAMP(),
          };

          return {
            expenses: {
              ...state.expenses,
              [budgetId]: updatedExpenses,
            },
          };
        }),
    }),
    {
      name: "budget-storage",
      partialize: (state) => ({
        activeBudgetId: state.activeBudgetId,
        baseCurrency: state.baseCurrency,
        // Only persist certain parts of the state
        budgets: state.budgets,
        expenses: state.expenses,
        // Do not persist computed properties
      }),
    }
  )
);

// Selector hooks for computed properties
export const useActiveBudget = () => useBudgetStore((state) => state.activeBudget);
export const useBudgetSummary = () => useBudgetStore((state) => state.budgetSummary);
export const useBudgetsByTrip = () => useBudgetStore((state) => state.budgetsByTrip);
export const useRecentExpenses = () => useBudgetStore((state) => state.recentExpenses);
