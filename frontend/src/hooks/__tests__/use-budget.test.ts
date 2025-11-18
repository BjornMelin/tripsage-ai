/** @vitest-environment jsdom */

import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  useAddExpense,
  useAlerts,
  useBudget,
  useBudgetActions,
  useCreateAlert,
  useCreateBudget,
  useDeleteBudget,
  useDeleteExpense,
  useExpenses,
  useFetchAlerts,
  useFetchBudgets,
  useFetchCurrencyRates,
  useFetchExpenses,
  useMarkAlertAsRead,
  useUpdateBudget,
  useUpdateExpense,
} from "../use-budget";

// Mock TanStack Query
vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual("@tanstack/react-query");
  return {
    ...actual,
    useMutation: vi.fn().mockReturnValue({
      error: null,
      isPending: false,
      mutate: vi.fn(),
      mutateAsync: vi.fn(),
    }),
    useQuery: vi.fn().mockReturnValue({
      data: undefined,
      error: null,
      isLoading: false,
      refetch: vi.fn(),
    }),
    useQueryClient: vi.fn().mockReturnValue({
      invalidateQueries: vi.fn(),
    }),
  };
});

// Mock authenticated API hook
vi.mock("@/hooks/use-authenticated-api", () => ({
  useAuthenticatedApi: vi.fn().mockReturnValue({
    makeAuthenticatedRequest: vi.fn().mockResolvedValue({}),
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

  describe("API hooks", () => {
    it("useFetchBudgets returns a query hook", () => {
      const { result } = renderHook(() => useFetchBudgets());

      expect(result.current.data).toBeUndefined();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.refetch).toBeDefined();
    });

    it("useCreateBudget returns a mutation hook", () => {
      const { result } = renderHook(() => useCreateBudget());

      expect(result.current.mutate).toBeDefined();
      expect(result.current.isPending).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("useUpdateBudget returns a mutation hook", () => {
      const { result } = renderHook(() => useUpdateBudget());

      expect(result.current.mutate).toBeDefined();
      expect(result.current.isPending).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("useDeleteBudget returns a mutation hook", () => {
      const { result } = renderHook(() => useDeleteBudget());

      expect(result.current.mutate).toBeDefined();
      expect(result.current.isPending).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("useFetchExpenses returns a query hook", () => {
      const { result } = renderHook(() => useFetchExpenses("budget-1"));

      expect(result.current.data).toBeUndefined();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.refetch).toBeDefined();
    });

    it("useAddExpense returns a mutation hook", () => {
      const { result } = renderHook(() => useAddExpense());

      expect(result.current.mutate).toBeDefined();
      expect(result.current.isPending).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("useUpdateExpense returns a mutation hook", () => {
      const { result } = renderHook(() => useUpdateExpense());

      expect(result.current.mutate).toBeDefined();
      expect(result.current.isPending).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("useDeleteExpense returns a mutation hook", () => {
      const { result } = renderHook(() => useDeleteExpense());

      expect(result.current.mutate).toBeDefined();
      expect(result.current.isPending).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("useFetchAlerts returns a query hook", () => {
      const { result } = renderHook(() => useFetchAlerts("budget-1"));

      expect(result.current.data).toBeUndefined();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.refetch).toBeDefined();
    });

    it("useCreateAlert returns a mutation hook", () => {
      const { result } = renderHook(() => useCreateAlert());

      expect(result.current.mutate).toBeDefined();
      expect(result.current.isPending).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("useMarkAlertAsRead returns a mutation hook", () => {
      const { result } = renderHook(() => useMarkAlertAsRead());

      expect(result.current.mutate).toBeDefined();
      expect(result.current.isPending).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("useFetchCurrencyRates returns a query hook", () => {
      const { result } = renderHook(() => useFetchCurrencyRates());

      expect(result.current.data).toBeUndefined();
      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
      expect(result.current.refetch).toBeDefined();
    });
  });
});
