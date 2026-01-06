/**
 * @fileoverview Shared types for the budget Zustand store slices.
 */

import type {
  Budget,
  BudgetAlert,
  BudgetCategory,
  BudgetSummary,
  CurrencyRate,
  Expense,
} from "@schemas/budget";
import type { CurrencyCode } from "@schemas/currency";

export type BudgetStoreLogger = {
  error: (message: string, context?: Record<string, unknown>) => void;
};

export type BudgetStoreDeps = {
  generateId: () => string;
  logger: BudgetStoreLogger;
  nowIso: () => string;
};

/**
 * Interface for the budget store state and actions.
 */
export interface BudgetState {
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
