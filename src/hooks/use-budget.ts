/**
 * @fileoverview React hooks for budget and expense management.
 */

"use client";

import type {
  AddExpenseRequest,
  Budget,
  BudgetAlert,
  CreateBudgetAlertRequest,
  CreateBudgetRequest,
  Expense,
  UpdateBudgetRequest,
  UpdateExpenseRequest,
} from "@schemas/budget";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useShallow } from "zustand/react/shallow";
import { useBudgetStore } from "@/features/budget/store/budget-store";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { useCurrentUserId } from "@/hooks/use-current-user-id";
import { type AppError, handleApiError } from "@/lib/api/error-types";
import { keys } from "@/lib/keys";
import { staleTimes } from "@/lib/query/config";

/**
 * Hook for accessing budget store state.
 */
export function useBudget() {
  const {
    activeBudget,
    activeBudgetId,
    budgetSummary,
    budgets,
    recentExpenses,
    setActiveBudget,
  } = useBudgetStore(
    useShallow((state) => ({
      activeBudget: state.activeBudget,
      activeBudgetId: state.activeBudgetId,
      budgetSummary: state.budgetSummary,
      budgets: state.budgets,
      recentExpenses: state.recentExpenses,
      setActiveBudget: state.setActiveBudget,
    }))
  );

  return {
    activeBudget,
    activeBudgetId,
    budgetSummary,
    budgets,
    recentExpenses,
    setActiveBudget,
  };
}

/**
 * Hook for budget management actions.
 */
export function useBudgetActions() {
  const {
    addBudget,
    addBudgetCategory,
    removeBudget,
    removeBudgetCategory,
    updateBudget,
    updateBudgetCategory,
  } = useBudgetStore(
    useShallow((state) => ({
      addBudget: state.addBudget,
      addBudgetCategory: state.addBudgetCategory,
      removeBudget: state.removeBudget,
      removeBudgetCategory: state.removeBudgetCategory,
      updateBudget: state.updateBudget,
      updateBudgetCategory: state.updateBudgetCategory,
    }))
  );

  return {
    addBudget,
    addBudgetCategory,
    removeBudget,
    removeBudgetCategory,
    updateBudget,
    updateBudgetCategory,
  };
}

/**
 * Hook for expense management.
 *
 * @param budgetId - Optional budget ID to filter expenses
 */
export function useExpenses(budgetId?: string) {
  const { addExpense, expenses, removeExpense, updateExpense } = useBudgetStore(
    useShallow((state) => ({
      addExpense: state.addExpense,
      expenses: state.expenses,
      removeExpense: state.removeExpense,
      updateExpense: state.updateExpense,
    }))
  );
  const budgetExpenses = budgetId ? expenses[budgetId] || [] : [];

  return {
    addExpense,
    expenses: budgetExpenses,
    removeExpense,
    updateExpense,
  };
}

/**
 * Hook for alerts management.
 *
 * @param budgetId - Optional budget ID to filter alerts
 */
export function useAlerts(budgetId?: string) {
  const { addAlert, alerts, clearAlerts, markAlertAsRead } = useBudgetStore(
    useShallow((state) => ({
      addAlert: state.addAlert,
      alerts: state.alerts,
      clearAlerts: state.clearAlerts,
      markAlertAsRead: state.markAlertAsRead,
    }))
  );
  const budgetAlerts = budgetId ? alerts[budgetId] || [] : [];

  return {
    addAlert,
    alerts: budgetAlerts,
    clearAlerts,
    markAlertAsRead,
  };
}

// API hooks for server interaction

/**
 * Hook for fetching all budgets for the current user.
 */
export function useFetchBudgets() {
  const setBudgets = useBudgetStore((state) => state.setBudgets);
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const userId = useCurrentUserId();

  const query = useQuery<{ budgets: Budget[] }, AppError>({
    enabled: !!userId,
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<{ budgets: Budget[] }>("/api/budgets");
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: userId ? keys.budget.list(userId) : keys.budget.all(),
    staleTime: staleTimes.categories,
    throwOnError: false,
  });

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
 * Hook for fetching a single budget.
 *
 * @param id - Budget ID to fetch
 */
export function useFetchBudget(id: string) {
  const addBudget = useBudgetStore((state) => state.addBudget);
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const userId = useCurrentUserId();

  const query = useQuery<Budget, AppError>({
    enabled: !!id && !!userId,
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<Budget>(`/api/budgets/${id}`);
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: userId ? keys.budget.detail(userId, id) : keys.budget.all(),
    staleTime: staleTimes.categories,
    throwOnError: false,
  });

  useEffect(() => {
    if (query.data) {
      addBudget(query.data);
    }
  }, [query.data, addBudget]);

  return query;
}

/**
 * Hook for creating a new budget.
 */
export function useCreateBudget() {
  const addBudget = useBudgetStore((state) => state.addBudget);
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();
  const userId = useCurrentUserId();

  const mutation = useMutation<Budget, AppError, CreateBudgetRequest>({
    mutationFn: async (variables) => {
      try {
        return await makeAuthenticatedRequest<Budget>("/api/budgets", {
          body: JSON.stringify(variables),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: () => {
      if (userId) {
        queryClient.invalidateQueries({ queryKey: keys.budget.list(userId) });
      } else {
        queryClient.invalidateQueries({ queryKey: keys.budget.all() });
      }
    },
    throwOnError: false,
  });

  useEffect(() => {
    if (mutation.data) {
      addBudget(mutation.data);
    }
  }, [mutation.data, addBudget]);

  return mutation;
}

/**
 * Hook for updating a budget.
 */
export function useUpdateBudget() {
  const updateBudget = useBudgetStore((state) => state.updateBudget);
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();
  const userId = useCurrentUserId();

  const mutation = useMutation<Budget, AppError, UpdateBudgetRequest>({
    mutationFn: async (variables) => {
      try {
        return await makeAuthenticatedRequest<Budget>("/api/budgets", {
          body: JSON.stringify(variables),
          headers: { "Content-Type": "application/json" },
          method: "PUT",
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: (data) => {
      if (userId) {
        queryClient.invalidateQueries({
          queryKey: keys.budget.detail(userId, data.id),
        });
        queryClient.invalidateQueries({ queryKey: keys.budget.list(userId) });
        return;
      }

      queryClient.invalidateQueries({ queryKey: keys.budget.all() });
    },
    throwOnError: false,
  });

  useEffect(() => {
    if (mutation.data) {
      updateBudget(mutation.data.id, mutation.data);
    }
  }, [mutation.data, updateBudget]);

  return mutation;
}

/**
 * Hook for deleting a budget.
 */
export function useDeleteBudget() {
  const removeBudget = useBudgetStore((state) => state.removeBudget);
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();
  const userId = useCurrentUserId();

  const mutation = useMutation<{ success: boolean; id: string }, AppError, string>({
    mutationFn: async (id) => {
      try {
        return await makeAuthenticatedRequest<{ success: boolean; id: string }>(
          `/api/budgets/${id}`,
          {
            method: "DELETE",
          }
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: (data) => {
      if (userId) {
        queryClient.invalidateQueries({
          queryKey: keys.budget.detail(userId, data.id),
        });
        queryClient.invalidateQueries({ queryKey: keys.budget.list(userId) });
        return;
      }

      queryClient.invalidateQueries({ queryKey: keys.budget.all() });
    },
    throwOnError: false,
  });

  useEffect(() => {
    if (mutation.data?.success) {
      removeBudget(mutation.data.id);
    }
  }, [mutation.data, removeBudget]);

  return mutation;
}

/**
 * Hook for fetching expenses for a budget.
 *
 * @param budgetId - Budget ID to fetch expenses for
 */
export function useFetchExpenses(budgetId: string) {
  const setExpenses = useBudgetStore((state) => state.setExpenses);
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const userId = useCurrentUserId();

  const query = useQuery<{ expenses: Expense[] }, AppError>({
    enabled: !!budgetId && !!userId,
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<{ expenses: Expense[] }>(
          `/api/budgets/${budgetId}/expenses`
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: userId ? keys.budget.expenses(userId, budgetId) : keys.budget.all(),
    staleTime: staleTimes.categories,
    throwOnError: false,
  });

  useEffect(() => {
    if (query.data) {
      setExpenses(budgetId, query.data.expenses);
    }
  }, [query.data, budgetId, setExpenses]);

  return query;
}

/**
 * Hook for adding an expense.
 */
export function useAddExpense() {
  const addExpense = useBudgetStore((state) => state.addExpense);
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();
  const userId = useCurrentUserId();

  const mutation = useMutation<Expense, AppError, AddExpenseRequest>({
    mutationFn: async (variables) => {
      try {
        return await makeAuthenticatedRequest<Expense>("/api/expenses", {
          body: JSON.stringify(variables),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: (data) => {
      if (userId) {
        queryClient.invalidateQueries({
          queryKey: keys.budget.expenses(userId, data.budgetId),
        });
      } else {
        queryClient.invalidateQueries({ queryKey: keys.budget.all() });
      }
    },
    throwOnError: false,
  });

  useEffect(() => {
    if (mutation.data) {
      addExpense(mutation.data);
    }
  }, [mutation.data, addExpense]);

  return mutation;
}

/**
 * Hook for updating an expense.
 */
export function useUpdateExpense() {
  const updateExpense = useBudgetStore((state) => state.updateExpense);
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();
  const userId = useCurrentUserId();

  const mutation = useMutation<Expense, AppError, UpdateExpenseRequest>({
    mutationFn: async (variables) => {
      try {
        return await makeAuthenticatedRequest<Expense>("/api/expenses", {
          body: JSON.stringify(variables),
          headers: { "Content-Type": "application/json" },
          method: "PUT",
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: (data) => {
      if (userId) {
        queryClient.invalidateQueries({
          queryKey: keys.budget.expenses(userId, data.budgetId),
        });
      } else {
        queryClient.invalidateQueries({ queryKey: keys.budget.all() });
      }
    },
    throwOnError: false,
  });

  useEffect(() => {
    if (mutation.data) {
      updateExpense(mutation.data.id, mutation.data.budgetId, mutation.data);
    }
  }, [mutation.data, updateExpense]);

  return mutation;
}

/**
 * Hook for deleting an expense.
 */
export function useDeleteExpense() {
  const removeExpense = useBudgetStore((state) => state.removeExpense);
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();
  const userId = useCurrentUserId();

  const mutation = useMutation<
    { success: boolean; id: string; budgetId: string },
    AppError,
    string
  >({
    mutationFn: async (id) => {
      try {
        return await makeAuthenticatedRequest<{
          success: boolean;
          id: string;
          budgetId: string;
        }>(`/api/expenses/${id}`, {
          method: "DELETE",
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: (data) => {
      if (userId) {
        queryClient.invalidateQueries({
          queryKey: keys.budget.expenses(userId, data.budgetId),
        });
      } else {
        queryClient.invalidateQueries({ queryKey: keys.budget.all() });
      }
    },
    throwOnError: false,
  });

  useEffect(() => {
    if (mutation.data?.success) {
      removeExpense(mutation.data.id, mutation.data.budgetId);
    }
  }, [mutation.data, removeExpense]);

  return mutation;
}

/**
 * Hook for fetching budget alerts.
 *
 * @param budgetId - Budget ID to fetch alerts for
 */
export function useFetchAlerts(budgetId: string) {
  const setAlerts = useBudgetStore((state) => state.setAlerts);
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const userId = useCurrentUserId();

  const query = useQuery<{ alerts: BudgetAlert[] }, AppError>({
    enabled: !!budgetId && !!userId,
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<{ alerts: BudgetAlert[] }>(
          `/api/budgets/${budgetId}/alerts`
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: userId ? keys.budget.alerts(userId, budgetId) : keys.budget.all(),
    staleTime: staleTimes.categories,
    throwOnError: false,
  });

  useEffect(() => {
    if (query.data) {
      setAlerts(budgetId, query.data.alerts);
    }
  }, [query.data, budgetId, setAlerts]);

  return query;
}

/**
 * Hook for creating a budget alert.
 */
export function useCreateAlert() {
  const addAlert = useBudgetStore((state) => state.addAlert);
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();
  const userId = useCurrentUserId();

  const mutation = useMutation<BudgetAlert, AppError, CreateBudgetAlertRequest>({
    mutationFn: async (variables) => {
      try {
        return await makeAuthenticatedRequest<BudgetAlert>("/api/alerts", {
          body: JSON.stringify(variables),
          headers: { "Content-Type": "application/json" },
          method: "POST",
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: (data) => {
      if (userId) {
        queryClient.invalidateQueries({
          queryKey: keys.budget.alerts(userId, data.budgetId),
        });
      } else {
        queryClient.invalidateQueries({ queryKey: keys.budget.all() });
      }
    },
    throwOnError: false,
  });

  useEffect(() => {
    if (mutation.data) {
      addAlert(mutation.data);
    }
  }, [mutation.data, addAlert]);

  return mutation;
}

/**
 * Hook for marking an alert as read.
 */
export function useMarkAlertAsRead() {
  const markAlertAsRead = useBudgetStore((state) => state.markAlertAsRead);
  const { makeAuthenticatedRequest } = useAuthenticatedApi();
  const queryClient = useQueryClient();
  const userId = useCurrentUserId();

  const mutation = useMutation<
    { id: string; budgetId: string; isRead: boolean },
    AppError,
    { id: string; budgetId: string }
  >({
    mutationFn: async (variables) => {
      try {
        return await makeAuthenticatedRequest<{
          id: string;
          budgetId: string;
          isRead: boolean;
        }>("/api/alerts/read", {
          body: JSON.stringify(variables),
          headers: { "Content-Type": "application/json" },
          method: "PUT",
        });
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: (data) => {
      if (userId) {
        queryClient.invalidateQueries({
          queryKey: keys.budget.alerts(userId, data.budgetId),
        });
      } else {
        queryClient.invalidateQueries({ queryKey: keys.budget.all() });
      }
    },
    throwOnError: false,
  });

  useEffect(() => {
    if (mutation.data) {
      markAlertAsRead(mutation.data.id, mutation.data.budgetId);
    }
  }, [mutation.data, markAlertAsRead]);

  return mutation;
}

/**
 * Hook for fetching currency exchange rates.
 */
export function useFetchCurrencyRates() {
  const setCurrencies = useBudgetStore((state) => state.setCurrencies);
  const { makeAuthenticatedRequest } = useAuthenticatedApi();

  const query = useQuery<{ rates: Record<string, number> }, AppError>({
    queryFn: async () => {
      try {
        return await makeAuthenticatedRequest<{ rates: Record<string, number> }>(
          "/api/currencies/rates"
        );
      } catch (error) {
        throw handleApiError(error);
      }
    },
    queryKey: keys.currency.rates(),
    refetchInterval: 60 * 60 * 1000, // Refresh currency rates every hour
    staleTime: staleTimes.currency,
    throwOnError: false,
  });

  useEffect(() => {
    if (query.data) {
      // Transform response to match our store format
      const formattedRates = Object.entries(query.data.rates).reduce(
        (acc, [code, rate]) => {
          acc[code] = {
            code,
            lastUpdated: new Date().toISOString(),
            rate,
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
