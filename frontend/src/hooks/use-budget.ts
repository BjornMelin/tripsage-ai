"use client";

import {
  useApiDeleteMutation,
  useApiMutation,
  useApiPutMutation,
  useApiQuery,
} from "@/hooks/use-api-query";
import { useBudgetStore } from "@/stores/budget-store";
import type {
  AddExpenseRequest,
  Budget,
  BudgetAlert,
  CreateBudgetAlertRequest,
  CreateBudgetRequest,
  Expense,
  UpdateBudgetRequest,
  UpdateExpenseRequest,
} from "@/types/budget";
import { useEffect } from "react";

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
  const { expenses, addExpense, updateExpense, removeExpense } = useBudgetStore();
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

// API hooks for server interaction

/**
 * Hook for fetching all budgets for the current user
 */
export function useFetchBudgets() {
  const { setBudgets } = useBudgetStore();

  const query = useApiQuery<{ budgets: Budget[] }>("/api/budgets", {});

  useEffect(() => {
    if (query.data) {
      // Convert array to record
      const budgetsRecord = query.data.budgets.reduce(
        (acc, budget) => {
          acc[budget.id] = budget;
          return acc;
        },
        {} as Record<string, Budget>
      );

      setBudgets(budgetsRecord);
    }
  }, [query.data, setBudgets]);

  return query;
}

/**
 * Hook for fetching a single budget
 */
export function useFetchBudget(id: string) {
  const { addBudget } = useBudgetStore();

  const query = useApiQuery<Budget>(
    `/api/budgets/${id}`,
    {},
    {
      enabled: !!id,
    }
  );

  useEffect(() => {
    if (query.data) {
      addBudget(query.data);
    }
  }, [query.data, addBudget]);

  return query;
}

/**
 * Hook for creating a new budget
 */
export function useCreateBudget() {
  const { addBudget } = useBudgetStore();

  const mutation = useApiMutation<Budget, CreateBudgetRequest>("/api/budgets");

  useEffect(() => {
    if (mutation.data) {
      addBudget(mutation.data);
    }
  }, [mutation.data, addBudget]);

  return mutation;
}

/**
 * Hook for updating a budget
 */
export function useUpdateBudget() {
  const { updateBudget } = useBudgetStore();

  const mutation = useApiPutMutation<Budget, UpdateBudgetRequest>("/api/budgets");

  useEffect(() => {
    if (mutation.data) {
      updateBudget(mutation.data.id, mutation.data);
    }
  }, [mutation.data, updateBudget]);

  return mutation;
}

/**
 * Hook for deleting a budget
 */
export function useDeleteBudget() {
  const { removeBudget } = useBudgetStore();

  const mutation = useApiDeleteMutation<{ success: boolean; id: string }, string>(
    "/api/budgets"
  );

  useEffect(() => {
    if (mutation.data?.success) {
      removeBudget(mutation.data.id);
    }
  }, [mutation.data, removeBudget]);

  return mutation;
}

/**
 * Hook for fetching expenses for a budget
 */
export function useFetchExpenses(budgetId: string) {
  const { setExpenses } = useBudgetStore();

  const query = useApiQuery<{ expenses: Expense[] }>(
    `/api/budgets/${budgetId}/expenses`,
    {},
    {
      enabled: !!budgetId,
    }
  );

  useEffect(() => {
    if (query.data) {
      setExpenses(budgetId, query.data.expenses);
    }
  }, [query.data, budgetId, setExpenses]);

  return query;
}

/**
 * Hook for adding an expense
 */
export function useAddExpense() {
  const { addExpense } = useBudgetStore();

  const mutation = useApiMutation<Expense, AddExpenseRequest>("/api/expenses");

  useEffect(() => {
    if (mutation.data) {
      addExpense(mutation.data);
    }
  }, [mutation.data, addExpense]);

  return mutation;
}

/**
 * Hook for updating an expense
 */
export function useUpdateExpense() {
  const { updateExpense } = useBudgetStore();

  const mutation = useApiPutMutation<Expense, UpdateExpenseRequest>("/api/expenses");

  useEffect(() => {
    if (mutation.data) {
      updateExpense(mutation.data.id, mutation.data.budgetId, mutation.data);
    }
  }, [mutation.data, updateExpense]);

  return mutation;
}

/**
 * Hook for deleting an expense
 */
export function useDeleteExpense() {
  const { removeExpense } = useBudgetStore();

  const mutation = useApiDeleteMutation<
    { success: boolean; id: string; budgetId: string },
    string
  >("/api/expenses");

  useEffect(() => {
    if (mutation.data?.success) {
      removeExpense(mutation.data.id, mutation.data.budgetId);
    }
  }, [mutation.data, removeExpense]);

  return mutation;
}

/**
 * Hook for fetching budget alerts
 */
export function useFetchAlerts(budgetId: string) {
  const { setAlerts } = useBudgetStore();

  const query = useApiQuery<{ alerts: BudgetAlert[] }>(
    `/api/budgets/${budgetId}/alerts`,
    {},
    {
      enabled: !!budgetId,
    }
  );

  useEffect(() => {
    if (query.data) {
      setAlerts(budgetId, query.data.alerts);
    }
  }, [query.data, budgetId, setAlerts]);

  return query;
}

/**
 * Hook for creating a budget alert
 */
export function useCreateAlert() {
  const { addAlert } = useBudgetStore();

  const mutation = useApiMutation<BudgetAlert, CreateBudgetAlertRequest>("/api/alerts");

  useEffect(() => {
    if (mutation.data) {
      addAlert(mutation.data);
    }
  }, [mutation.data, addAlert]);

  return mutation;
}

/**
 * Hook for marking an alert as read
 */
export function useMarkAlertAsRead() {
  const { markAlertAsRead } = useBudgetStore();

  const mutation = useApiPutMutation<
    { id: string; budgetId: string; isRead: boolean },
    { id: string; budgetId: string }
  >("/api/alerts/read");

  useEffect(() => {
    if (mutation.data) {
      markAlertAsRead(mutation.data.id, mutation.data.budgetId);
    }
  }, [mutation.data, markAlertAsRead]);

  return mutation;
}

/**
 * Hook for fetching currency exchange rates
 */
export function useFetchCurrencyRates() {
  const { setCurrencies } = useBudgetStore();

  const query = useApiQuery<{ rates: Record<string, number> }>(
    "/api/currencies/rates",
    {},
    {
      // Refresh currency rates every hour
      refetchInterval: 60 * 60 * 1000,
    }
  );

  useEffect(() => {
    if (query.data) {
      // Transform response to match our store format
      const formattedRates = Object.entries(query.data.rates).reduce(
        (acc, [code, rate]) => {
          acc[code] = {
            code,
            rate,
            lastUpdated: new Date().toISOString(),
          };
          return acc;
        },
        {} as Record<string, { code: string; rate: number; lastUpdated: string }>
      );

      setCurrencies(formattedRates);
    }
  }, [query.data, setCurrencies]);

  return query;
}
