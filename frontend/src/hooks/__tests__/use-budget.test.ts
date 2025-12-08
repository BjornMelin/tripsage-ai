/** @vitest-environment jsdom */

/**
 * Budget hooks test suite.
 *
 * Tests store-based hooks (useBudget, useBudgetActions, useExpenses, useAlerts)
 * with mocked Zustand store. API hooks (useFetchBudgets, useCreateBudget, etc.)
 * use real React Query with mocked API layer.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  useAddExpense,
  useAlerts,
  useBudget,
  useBudgetActions,
  useCreateBudget,
  useDeleteBudget,
  useExpenses,
  useFetchAlerts,
  useFetchBudgets,
  useFetchCurrencyRates,
  useFetchExpenses,
} from "../use-budget";

// Hoisted mock for API layer
const mockMakeAuthenticatedRequest = vi.hoisted(() => vi.fn());

// Mock only the API layer - let React Query work normally
vi.mock("@/hooks/use-authenticated-api", () => ({
  useAuthenticatedApi: () => ({
    makeAuthenticatedRequest: mockMakeAuthenticatedRequest,
  }),
}));

// Mock the budget store
vi.mock("@/stores/budget-store", () => ({
  useBudgetStore: vi.fn().mockImplementation(() => ({
    activeBudget: {
      categories: [],
      createdAt: "2025-05-20T12:00:00Z",
      currency: "USD",
      id: "budget-1",
      isActive: true,
      name: "Summer Vacation",
      totalAmount: 5000,
      updatedAt: "2025-05-20T12:00:00Z",
    },
    activeBudgetId: "budget-1",
    addAlert: vi.fn(),
    addBudget: vi.fn(),
    addBudgetCategory: vi.fn(),
    addExpense: vi.fn(),
    alerts: {
      "budget-1": [
        {
          budgetId: "budget-1",
          createdAt: "2025-05-20T12:00:00Z",
          id: "alert-1",
          isRead: false,
          message: "Almost at budget limit",
          threshold: 80,
          type: "threshold",
        },
      ],
    },
    baseCurrency: "USD",
    budgetSummary: {
      dailyAverage: 100,
      dailyLimit: 300,
      isOverBudget: false,
      percentageSpent: 10,
      projectedTotal: 1500,
      spentByCategory: { flights: 500 },
      totalBudget: 5000,
      totalRemaining: 4500,
      totalSpent: 500,
    },
    budgets: {
      "budget-1": {
        categories: [],
        createdAt: "2025-05-20T12:00:00Z",
        currency: "USD",
        id: "budget-1",
        isActive: true,
        name: "Summer Vacation",
        totalAmount: 5000,
        updatedAt: "2025-05-20T12:00:00Z",
      },
    },
    budgetsByTrip: {
      "trip-1": ["budget-1"],
    },
    clearAlerts: vi.fn(),
    currencies: {
      EUR: {
        code: "EUR",
        lastUpdated: "2025-05-20T12:00:00Z",
        rate: 0.85,
      },
    },
    expenses: {
      "budget-1": [
        {
          amount: 500,
          budgetId: "budget-1",
          category: "flights",
          createdAt: "2025-05-20T12:00:00Z",
          currency: "USD",
          date: "2025-06-01",
          description: "Flight to NYC",
          id: "expense-1",
          isShared: false,
          updatedAt: "2025-05-20T12:00:00Z",
        },
      ],
    },
    markAlertAsRead: vi.fn(),
    recentExpenses: [
      {
        amount: 500,
        budgetId: "budget-1",
        category: "flights",
        createdAt: "2025-05-20T12:00:00Z",
        currency: "USD",
        date: "2025-06-01",
        description: "Flight to NYC",
        id: "expense-1",
        isShared: false,
        updatedAt: "2025-05-20T12:00:00Z",
      },
    ],
    removeBudget: vi.fn(),
    removeBudgetCategory: vi.fn(),
    removeExpense: vi.fn(),
    setActiveBudget: vi.fn(),
    setAlerts: vi.fn(),
    setBaseCurrency: vi.fn(),
    setBudgets: vi.fn(),
    setCurrencies: vi.fn(),
    setExpenses: vi.fn(),
    updateBudget: vi.fn(),
    updateBudgetCategory: vi.fn(),
    updateCurrencyRate: vi.fn(),
    updateExpense: vi.fn(),
  })),
}));

describe("Budget Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("useBudget", () => {
    it("returns budget data and actions", () => {
      const { result } = renderHook(() => useBudget());

      expect(result.current.budgets).toBeDefined();
      expect(result.current.activeBudgetId).toBe("budget-1");
      expect(result.current.activeBudget).toBeDefined();
      expect(result.current.budgetSummary).toBeDefined();
      expect(result.current.recentExpenses).toBeDefined();
      expect(result.current.setActiveBudget).toBeDefined();

      // Verify the data matches mock
      expect(result.current.activeBudget?.name).toBe("Summer Vacation");
      expect(result.current.budgetSummary?.totalBudget).toBe(5000);
      expect(result.current.budgetSummary?.totalSpent).toBe(500);
    });
  });

  describe("useBudgetActions", () => {
    it("returns budget actions", () => {
      const { result } = renderHook(() => useBudgetActions());

      expect(result.current.addBudget).toBeDefined();
      expect(result.current.updateBudget).toBeDefined();
      expect(result.current.removeBudget).toBeDefined();
      expect(result.current.addBudgetCategory).toBeDefined();
      expect(result.current.updateBudgetCategory).toBeDefined();
      expect(result.current.removeBudgetCategory).toBeDefined();
    });
  });

  describe("useExpenses", () => {
    it("returns expenses and expense actions for a specific budget", () => {
      const { result } = renderHook(() => useExpenses("budget-1"));

      expect(result.current.expenses).toHaveLength(1);
      expect(result.current.expenses[0].id).toBe("expense-1");
      expect(result.current.addExpense).toBeDefined();
      expect(result.current.updateExpense).toBeDefined();
      expect(result.current.removeExpense).toBeDefined();

      // Verify the expense data
      expect(result.current.expenses[0].description).toBe("Flight to NYC");
      expect(result.current.expenses[0].amount).toBe(500);
    });

    it("returns empty array when no budget is specified", () => {
      const { result } = renderHook(() => useExpenses());

      expect(result.current.expenses).toEqual([]);
    });
  });

  describe("useAlerts", () => {
    it("returns alerts and alert actions for a specific budget", () => {
      const { result } = renderHook(() => useAlerts("budget-1"));

      expect(result.current.alerts).toHaveLength(1);
      expect(result.current.alerts[0].id).toBe("alert-1");
      expect(result.current.addAlert).toBeDefined();
      expect(result.current.markAlertAsRead).toBeDefined();
      expect(result.current.clearAlerts).toBeDefined();

      // Verify the alert data
      expect(result.current.alerts[0].message).toBe("Almost at budget limit");
      expect(result.current.alerts[0].threshold).toBe(80);
    });

    it("returns empty array when no budget is specified", () => {
      const { result } = renderHook(() => useAlerts());

      expect(result.current.alerts).toEqual([]);
    });
  });

  // API hooks using real React Query with mocked API layer
  describe("API hooks with QueryClient", () => {
    const createTestQueryClient = () =>
      new QueryClient({
        defaultOptions: {
          mutations: { retry: false },
          queries: { retry: false },
        },
      });

    const createWrapper = (queryClient: QueryClient) => {
      return function Wrapper({ children }: { children: ReactNode }) {
        return createElement(QueryClientProvider, { client: queryClient }, children);
      };
    };

    beforeEach(() => {
      mockMakeAuthenticatedRequest.mockReset();
    });

    it("useFetchBudgets fetches and returns budgets", async () => {
      const mockBudgets = {
        budgets: [
          { currency: "USD", id: "b1", name: "Trip Budget", totalAmount: 1000 },
        ],
      };
      mockMakeAuthenticatedRequest.mockResolvedValue(mockBudgets);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useFetchBudgets(), {
        wrapper: createWrapper(queryClient),
      });

      // Initially loading
      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith("/api/budgets");
      expect(result.current.data).toEqual(mockBudgets);
    });

    it("useCreateBudget creates budget via mutation", async () => {
      const newBudget = {
        currency: "USD",
        id: "new-1",
        name: "New Budget",
        totalAmount: 500,
      };
      mockMakeAuthenticatedRequest.mockResolvedValue(newBudget);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useCreateBudget(), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.isPending).toBe(false);

      result.current.mutate({ currency: "USD", name: "New Budget", totalAmount: 500 });

      await waitFor(() => {
        expect(result.current.isPending).toBe(false);
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
        "/api/budgets",
        expect.objectContaining({ method: "POST" })
      );
    });

    it("useDeleteBudget deletes budget via mutation", async () => {
      mockMakeAuthenticatedRequest.mockResolvedValue({
        id: "budget-to-delete",
        success: true,
      });

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useDeleteBudget(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate("budget-to-delete");

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
        "/api/budgets/budget-to-delete",
        expect.objectContaining({ method: "DELETE" })
      );
    });

    it("useFetchExpenses fetches expenses for a budget", async () => {
      const mockExpenses = {
        expenses: [{ amount: 100, description: "Test expense", id: "e1" }],
      };
      mockMakeAuthenticatedRequest.mockResolvedValue(mockExpenses);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useFetchExpenses("budget-1"), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
        "/api/budgets/budget-1/expenses"
      );
      expect(result.current.data).toEqual(mockExpenses);
    });

    it("useAddExpense adds expense via mutation", async () => {
      const newExpense = {
        amount: 50,
        budgetId: "budget-1",
        description: "New expense",
        id: "e-new",
      };
      mockMakeAuthenticatedRequest.mockResolvedValue(newExpense);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useAddExpense(), {
        wrapper: createWrapper(queryClient),
      });

      result.current.mutate({
        amount: 50,
        budgetId: "budget-1",
        category: "food",
        currency: "USD",
        date: "2025-01-01",
        description: "New expense",
        isShared: false,
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
        "/api/expenses",
        expect.objectContaining({ method: "POST" })
      );
    });

    it("useFetchAlerts fetches alerts for a budget", async () => {
      const mockAlerts = {
        alerts: [{ id: "a1", message: "Over budget", threshold: 100 }],
      };
      mockMakeAuthenticatedRequest.mockResolvedValue(mockAlerts);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useFetchAlerts("budget-1"), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
        "/api/budgets/budget-1/alerts"
      );
    });

    it("useFetchCurrencyRates fetches currency rates", async () => {
      const mockRates = { rates: { EUR: 0.85, GBP: 0.73 } };
      mockMakeAuthenticatedRequest.mockResolvedValue(mockRates);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useFetchCurrencyRates(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockMakeAuthenticatedRequest).toHaveBeenCalledWith(
        "/api/currencies/rates"
      );
    });
  });
});
