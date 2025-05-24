"use client";

import {
  useApiQuery,
  useApiMutation,
  useApiPutMutation,
  useApiDeleteMutation,
} from "@/lib/hooks/use-api-query";
import { useBudgetStore } from "@/stores/budget-store";
import type {
  Budget,
  Expense,
  BudgetAlert,
  BudgetCategory,
  CreateBudgetRequest,
  UpdateBudgetRequest,
  AddExpenseRequest,
  UpdateExpenseRequest,
  CreateBudgetAlertRequest,
} from "@/types/budget";

/**
 * Hook for using the budget store
 */
export function useBudget() {
  const {
    budgets,
    activeBudgetId,
    activeBudget,
    budgetSummary,
    recentExpenses,
    setActiveBudget,
  } = useBudgetStore();

  return {
    budgets,
    activeBudgetId,
    activeBudget,
    budgetSummary,
    recentExpenses,
    setActiveBudget,
  };
}

/**
 * Hook for budget management actions
 */
export function useBudgetActions() {
  const {
    addBudget,
    updateBudget,
    removeBudget,
    addBudgetCategory,
    updateBudgetCategory,
    removeBudgetCategory,
  } = useBudgetStore();

  return {
    addBudget,
    updateBudget,
    removeBudget,
    addBudgetCategory,
    updateBudgetCategory,
    removeBudgetCategory,
  };
}

/**
 * Hook for expense management
 */
export function useExpenses(budgetId?: string) {
  const { expenses, addExpense, updateExpense, removeExpense } =
    useBudgetStore();
  const budgetExpenses = budgetId ? expenses[budgetId] || [] : [];

  return {
    expenses: budgetExpenses,
    addExpense,
    updateExpense,
    removeExpense,
  };
}

/**
 * Hook for alerts management
 */
export function useAlerts(budgetId?: string) {
  const { alerts, addAlert, markAlertAsRead, clearAlerts } = useBudgetStore();
  const budgetAlerts = budgetId ? alerts[budgetId] || [] : [];

  return {
    alerts: budgetAlerts,
    addAlert,
    markAlertAsRead,
    clearAlerts,
  };
}

/**
 * Hook for currency management
 */
export function useCurrency() {
  const { baseCurrency, currencies, setBaseCurrency, updateCurrencyRate } =
    useBudgetStore();

  return {
    baseCurrency,
    currencies,
    setBaseCurrency,
    updateCurrencyRate,
  };
}

// API hooks for server interaction

/**
 * Hook for fetching all budgets for the current user
 */
export function useFetchBudgets() {
  const { setBudgets } = useBudgetStore();

  return useApiQuery<{ budgets: Budget[] }>(
    "/api/budgets",
    {},
    {
      onSuccess: (data) => {
        // Convert array to record
        const budgetsRecord = data.budgets.reduce(
          (acc, budget) => {
            acc[budget.id] = budget;
            return acc;
          },
          {} as Record<string, Budget>
        );

        setBudgets(budgetsRecord);
      },
    }
  );
}

/**
 * Hook for fetching a single budget
 */
export function useFetchBudget(id: string) {
  const { addBudget } = useBudgetStore();

  return useApiQuery<Budget>(
    `/api/budgets/${id}`,
    {},
    {
      onSuccess: (data) => {
        addBudget(data);
      },
      enabled: !!id,
    }
  );
}

/**
 * Hook for creating a new budget
 */
export function useCreateBudget() {
  const { addBudget } = useBudgetStore();

  return useApiMutation<Budget, CreateBudgetRequest>("/api/budgets", {
    onSuccess: (data) => {
      addBudget(data);
    },
  });
}

/**
 * Hook for updating a budget
 */
export function useUpdateBudget() {
  const { updateBudget } = useBudgetStore();

  return useApiPutMutation<Budget, UpdateBudgetRequest>("/api/budgets", {
    onSuccess: (data) => {
      updateBudget(data.id, data);
    },
  });
}

/**
 * Hook for deleting a budget
 */
export function useDeleteBudget() {
  const { removeBudget } = useBudgetStore();

  return useApiDeleteMutation<{ success: boolean; id: string }, string>(
    "/api/budgets",
    {
      onSuccess: (data) => {
        if (data.success) {
          removeBudget(data.id);
        }
      },
    }
  );
}

/**
 * Hook for fetching expenses for a budget
 */
export function useFetchExpenses(budgetId: string) {
  const { setExpenses } = useBudgetStore();

  return useApiQuery<{ expenses: Expense[] }>(
    `/api/budgets/${budgetId}/expenses`,
    {},
    {
      onSuccess: (data) => {
        setExpenses(budgetId, data.expenses);
      },
      enabled: !!budgetId,
    }
  );
}

/**
 * Hook for adding an expense
 */
export function useAddExpense() {
  const { addExpense } = useBudgetStore();

  return useApiMutation<Expense, AddExpenseRequest>("/api/expenses", {
    onSuccess: (data) => {
      addExpense(data);
    },
  });
}

/**
 * Hook for updating an expense
 */
export function useUpdateExpense() {
  const { updateExpense } = useBudgetStore();

  return useApiPutMutation<Expense, UpdateExpenseRequest>("/api/expenses", {
    onSuccess: (data) => {
      updateExpense(data.id, data.budgetId, data);
    },
  });
}

/**
 * Hook for deleting an expense
 */
export function useDeleteExpense() {
  const { removeExpense } = useBudgetStore();

  return useApiDeleteMutation<
    { success: boolean; id: string; budgetId: string },
    string
  >("/api/expenses", {
    onSuccess: (data) => {
      if (data.success) {
        removeExpense(data.id, data.budgetId);
      }
    },
  });
}

/**
 * Hook for fetching budget alerts
 */
export function useFetchAlerts(budgetId: string) {
  const { setAlerts } = useBudgetStore();

  return useApiQuery<{ alerts: BudgetAlert[] }>(
    `/api/budgets/${budgetId}/alerts`,
    {},
    {
      onSuccess: (data) => {
        setAlerts(budgetId, data.alerts);
      },
      enabled: !!budgetId,
    }
  );
}

/**
 * Hook for creating a budget alert
 */
export function useCreateAlert() {
  const { addAlert } = useBudgetStore();

  return useApiMutation<BudgetAlert, CreateBudgetAlertRequest>("/api/alerts", {
    onSuccess: (data) => {
      addAlert(data);
    },
  });
}

/**
 * Hook for marking an alert as read
 */
export function useMarkAlertAsRead() {
  const { markAlertAsRead } = useBudgetStore();

  return useApiPutMutation<
    { id: string; budgetId: string; isRead: boolean },
    { id: string; budgetId: string }
  >("/api/alerts/read", {
    onSuccess: (data) => {
      markAlertAsRead(data.id, data.budgetId);
    },
  });
}

/**
 * Hook for fetching currency exchange rates
 */
export function useFetchCurrencyRates() {
  const { setCurrencies } = useBudgetStore();

  return useApiQuery<{ rates: Record<string, number> }>(
    "/api/currencies/rates",
    {},
    {
      onSuccess: (data) => {
        // Transform response to match our store format
        const formattedRates = Object.entries(data.rates).reduce(
          (acc, [code, rate]) => {
            acc[code] = {
              code,
              rate,
              lastUpdated: new Date().toISOString(),
            };
            return acc;
          },
          {} as Record<
            string,
            { code: string; rate: number; lastUpdated: string }
          >
        );

        setCurrencies(formattedRates);
      },
      // Refresh currency rates every hour
      refetchInterval: 60 * 60 * 1000,
    }
  );
}
