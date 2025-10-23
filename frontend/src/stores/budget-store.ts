import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  Budget,
  BudgetAlert,
  BudgetCategory,
  BudgetSummary,
  CurrencyCode,
  CurrencyRate,
  Expense,
  ExpenseCategory,
} from "@/types/budget";

// Helper functions
const generateId = () =>
  Date.now().toString(36) + Math.random().toString(36).substring(2, 5);
const getCurrentTimestamp = () => new Date().toISOString();

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

const calculateBudgetSummary = (budget: Budget, expenses: Expense[]): BudgetSummary => {
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
    totalBudget,
    totalSpent,
    totalRemaining,
    percentageSpent,
    spentByCategory,
    dailyAverage,
    dailyLimit,
    projectedTotal,
    isOverBudget: totalRemaining < 0,
    daysRemaining,
  };
};

export const useBudgetStore = create<BudgetState>()(
  persist(
    (set, get) => ({
      // Initial state
      budgets: {},
      activeBudgetId: null,
      expenses: {},
      baseCurrency: "USD",
      currencies: {},
      alerts: {},

      // Computed properties
      get activeBudget(): Budget | null {
        const { activeBudgetId, budgets } = get();
        return activeBudgetId ? budgets[activeBudgetId] || null : null;
      },

      get budgetSummary(): BudgetSummary | null {
        const { activeBudget } = get();
        const { expenses } = get();

        if (!activeBudget) return null;

        const budgetExpenses = expenses[activeBudget.id] || [];
        return calculateBudgetSummary(activeBudget, budgetExpenses);
      },

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

      get recentExpenses(): Expense[] {
        const { expenses } = get();

        // Flatten all expenses and sort by date (newest first)
        return Object.values(expenses)
          .flat()
          .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
          .slice(0, 10); // Return the 10 most recent expenses
      },

      // Budget actions
      setBudgets: (budgets) => set({ budgets }),

      addBudget: (budget) =>
        set((state) => {
          const newBudget = {
            ...budget,
            id: budget.id || generateId(),
            createdAt: budget.createdAt || getCurrentTimestamp(),
            updatedAt: getCurrentTimestamp(),
          };

          return {
            budgets: {
              ...state.budgets,
              [newBudget.id]: newBudget,
            },
            // If this is the first budget, set it as active
            activeBudgetId:
              state.activeBudgetId === null ? newBudget.id : state.activeBudgetId,
          };
        }),

      updateBudget: (id, updates) =>
        set((state) => {
          const budget = state.budgets[id];
          if (!budget) return state;

          const updatedBudget = {
            ...budget,
            ...updates,
            updatedAt: getCurrentTimestamp(),
          };

          return {
            budgets: {
              ...state.budgets,
              [id]: updatedBudget,
            },
          };
        }),

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
            budgets: newBudgets,
            expenses: newExpenses,
            alerts: newAlerts,
            activeBudgetId: newActiveBudgetId,
          };
        }),

      setActiveBudget: (id) => set({ activeBudgetId: id }),

      // Budget category actions
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
                updatedAt: getCurrentTimestamp(),
              },
            },
          };
        }),

      addBudgetCategory: (budgetId, category) =>
        set((state) => {
          const budget = state.budgets[budgetId];
          if (!budget) return state;

          const newCategory = {
            ...category,
            id: category.id || generateId(),
          };

          return {
            budgets: {
              ...state.budgets,
              [budgetId]: {
                ...budget,
                categories: [...budget.categories, newCategory],
                updatedAt: getCurrentTimestamp(),
              },
            },
          };
        }),

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
                updatedAt: getCurrentTimestamp(),
              },
            },
          };
        }),

      // Expense actions
      setExpenses: (budgetId, expenses) =>
        set((state) => ({
          expenses: {
            ...state.expenses,
            [budgetId]: expenses,
          },
        })),

      addExpense: (expense) =>
        set((state) => {
          const budgetId = expense.budgetId;
          const currentExpenses = state.expenses[budgetId] || [];

          const newExpense = {
            ...expense,
            id: expense.id || generateId(),
            createdAt: expense.createdAt || getCurrentTimestamp(),
            updatedAt: getCurrentTimestamp(),
          };

          return {
            expenses: {
              ...state.expenses,
              [budgetId]: [...currentExpenses, newExpense],
            },
          };
        }),

      updateExpense: (id, budgetId, updates) =>
        set((state) => {
          const expenses = state.expenses[budgetId] || [];
          const expenseIndex = expenses.findIndex((exp) => exp.id === id);

          if (expenseIndex === -1) return state;

          const updatedExpenses = [...expenses];
          updatedExpenses[expenseIndex] = {
            ...updatedExpenses[expenseIndex],
            ...updates,
            updatedAt: getCurrentTimestamp(),
          };

          return {
            expenses: {
              ...state.expenses,
              [budgetId]: updatedExpenses,
            },
          };
        }),

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

      // Currency actions
      setBaseCurrency: (currency) => set({ baseCurrency: currency }),

      setCurrencies: (currencies) => set({ currencies }),

      updateCurrencyRate: (code, rate) =>
        set((state) => ({
          currencies: {
            ...state.currencies,
            [code]: {
              code,
              rate,
              lastUpdated: getCurrentTimestamp(),
            },
          },
        })),

      // Alert actions
      setAlerts: (budgetId, alerts) =>
        set((state) => ({
          alerts: {
            ...state.alerts,
            [budgetId]: alerts,
          },
        })),

      addAlert: (alert) =>
        set((state) => {
          const budgetId = alert.budgetId;
          const currentAlerts = state.alerts[budgetId] || [];

          const newAlert = {
            ...alert,
            id: alert.id || generateId(),
            isRead: false,
            createdAt: alert.createdAt || getCurrentTimestamp(),
          };

          return {
            alerts: {
              ...state.alerts,
              [budgetId]: [...currentAlerts, newAlert],
            },
          };
        }),

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

      clearAlerts: (budgetId) =>
        set((state) => {
          const newAlerts = { ...state.alerts };
          delete newAlerts[budgetId];

          return {
            alerts: newAlerts,
          };
        }),
    }),
    {
      name: "budget-storage",
      partialize: (state) => ({
        // Only persist certain parts of the state
        budgets: state.budgets,
        expenses: state.expenses,
        baseCurrency: state.baseCurrency,
        activeBudgetId: state.activeBudgetId,
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
