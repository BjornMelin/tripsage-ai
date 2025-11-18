import { describe, expect, it } from "vitest";
import {
  addExpenseRequestSchema,
  budgetAlertSchema,
  budgetCategorySchema,
  budgetFormSchema,
  budgetSchema,
  budgetStateSchema,
  budgetSummarySchema,
  createBudgetAlertRequestSchema,
  createBudgetRequestSchema,
  currencyRateSchema,
  expenseCategorySchema,
  expenseFormSchema,
  expenseSchema,
  shareDetailsSchema,
} from "../budget";

describe("budget schemas", () => {
  describe("expenseCategorySchema", () => {
    it.concurrent("should validate valid expense categories", () => {
      const categories = [
        "flights",
        "accommodations",
        "transportation",
        "food",
        "activities",
        "shopping",
        "other",
      ];
      for (const category of categories) {
        const result = expenseCategorySchema.safeParse(category);
        expect(result.success).toBe(true);
      }
    });

    it.concurrent("should reject invalid category", () => {
      const result = expenseCategorySchema.safeParse("invalid");
      expect(result.success).toBe(false);
    });
  });

  describe("budgetCategorySchema", () => {
    it.concurrent("should validate budget category", () => {
      const result = budgetCategorySchema.safeParse({
        amount: 1000,
        category: "food",
        id: "123e4567-e89b-12d3-a456-426614174000",
        percentage: 50,
        remaining: 500,
        spent: 500,
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject negative amount", () => {
      const result = budgetCategorySchema.safeParse({
        amount: -1000,
        category: "food",
        id: "123e4567-e89b-12d3-a456-426614174000",
        percentage: 50,
        remaining: -1000,
        spent: 0,
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject percentage over 100", () => {
      const result = budgetCategorySchema.safeParse({
        amount: 1000,
        category: "food",
        id: "123e4567-e89b-12d3-a456-426614174000",
        percentage: 150,
        remaining: 1000,
        spent: 0,
      });
      expect(result.success).toBe(false);
    });
  });

  describe("shareDetailsSchema", () => {
    it.concurrent("should validate share details", () => {
      const result = shareDetailsSchema.safeParse({
        amount: 50,
        isPaid: false,
        percentage: 25,
        userId: "123e4567-e89b-12d3-a456-426614174000",
        userName: "John Doe",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject negative amount", () => {
      const result = shareDetailsSchema.safeParse({
        amount: -50,
        isPaid: false,
        percentage: 25,
        userId: "123e4567-e89b-12d3-a456-426614174000",
        userName: "John Doe",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("budgetSchema", () => {
    it.concurrent("should validate budget", () => {
      const result = budgetSchema.safeParse({
        categories: [
          {
            amount: 2000,
            category: "flights",
            id: "123e4567-e89b-12d3-a456-426614174001",
            percentage: 40,
            remaining: 2000,
            spent: 0,
          },
          {
            amount: 2000,
            category: "accommodations",
            id: "123e4567-e89b-12d3-a456-426614174002",
            percentage: 40,
            remaining: 2000,
            spent: 0,
          },
          {
            amount: 1000,
            category: "food",
            id: "123e4567-e89b-12d3-a456-426614174003",
            percentage: 20,
            remaining: 1000,
            spent: 0,
          },
        ],
        createdAt: "2024-01-01T00:00:00Z",
        currency: "USD",
        endDate: "2024-06-07",
        id: "123e4567-e89b-12d3-a456-426614174000",
        isActive: true,
        name: "Summer Trip",
        startDate: "2024-06-01",
        totalAmount: 5000,
        updatedAt: "2024-01-01T00:00:00Z",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject end date before start date", () => {
      const result = budgetSchema.safeParse({
        categories: [],
        createdAt: "2024-01-01T00:00:00Z",
        currency: "USD",
        endDate: "2024-06-01",
        id: "123e4567-e89b-12d3-a456-426614174000",
        isActive: true,
        name: "Summer Trip",
        startDate: "2024-06-07",
        totalAmount: 5000,
        updatedAt: "2024-01-01T00:00:00Z",
      });
      expect(result.success).toBe(false);
    });

    it.concurrent("should reject category amounts exceeding total", () => {
      const result = budgetSchema.safeParse({
        categories: [
          {
            amount: 6000,
            category: "flights",
            id: "123e4567-e89b-12d3-a456-426614174001",
            percentage: 120,
            remaining: 6000,
            spent: 0,
          },
        ],
        createdAt: "2024-01-01T00:00:00Z",
        currency: "USD",
        id: "123e4567-e89b-12d3-a456-426614174000",
        isActive: true,
        name: "Summer Trip",
        totalAmount: 5000,
        updatedAt: "2024-01-01T00:00:00Z",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("expenseSchema", () => {
    it.concurrent("should validate expense", () => {
      const result = expenseSchema.safeParse({
        amount: 50,
        budgetId: "123e4567-e89b-12d3-a456-426614174001",
        category: "food",
        createdAt: "2024-01-01T00:00:00Z",
        currency: "USD",
        date: "2024-06-01",
        description: "Dinner",
        id: "123e4567-e89b-12d3-a456-426614174000",
        isShared: false,
        updatedAt: "2024-01-01T00:00:00Z",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject negative amount", () => {
      const result = expenseSchema.safeParse({
        amount: -50,
        budgetId: "123e4567-e89b-12d3-a456-426614174001",
        category: "food",
        createdAt: "2024-01-01T00:00:00Z",
        currency: "USD",
        date: "2024-06-01",
        description: "Dinner",
        id: "123e4567-e89b-12d3-a456-426614174000",
        isShared: false,
      });
      expect(result.success).toBe(false);
    });
  });

  describe("currencyRateSchema", () => {
    it.concurrent("should validate currency rate", () => {
      const result = currencyRateSchema.safeParse({
        code: "EUR",
        lastUpdated: "2024-01-01T00:00:00Z",
        rate: 1.2,
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject negative rate", () => {
      const result = currencyRateSchema.safeParse({
        code: "EUR",
        lastUpdated: "2024-01-01T00:00:00Z",
        rate: -1.2,
      });
      expect(result.success).toBe(false);
    });
  });

  describe("budgetSummarySchema", () => {
    it.concurrent("should validate budget summary", () => {
      const result = budgetSummarySchema.safeParse({
        dailyAverage: 357.14,
        dailyLimit: 714.29,
        isOverBudget: false,
        percentageSpent: 50,
        projectedTotal: 5000,
        spentByCategory: {
          accommodations: 1000,
          flights: 1000,
          food: 500,
        },
        totalBudget: 5000,
        totalRemaining: 2500,
        totalSpent: 2500,
      });
      expect(result.success).toBe(true);
    });
  });

  describe("budgetAlertSchema", () => {
    it.concurrent("should validate budget alert", () => {
      const result = budgetAlertSchema.safeParse({
        budgetId: "123e4567-e89b-12d3-a456-426614174001",
        createdAt: "2024-01-01T00:00:00Z",
        id: "123e4567-e89b-12d3-a456-426614174000",
        isRead: false,
        message: "Budget at 80%",
        threshold: 80,
        type: "threshold",
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should validate all alert types", () => {
      const types = ["threshold", "category", "daily"];
      for (const type of types) {
        const result = budgetAlertSchema.safeParse({
          budgetId: "123e4567-e89b-12d3-a456-426614174001",
          createdAt: "2024-01-01T00:00:00Z",
          id: "123e4567-e89b-12d3-a456-426614174000",
          isRead: false,
          message: "Budget alert",
          threshold: 80,
          type,
        });
        expect(result.success).toBe(true);
      }
    });
  });

  describe("createBudgetRequestSchema", () => {
    it.concurrent("should validate create budget request", () => {
      const result = createBudgetRequestSchema.safeParse({
        categories: [
          { amount: 2000, category: "flights" },
          { amount: 2000, category: "accommodations" },
          { amount: 1000, category: "food" },
        ],
        currency: "USD",
        endDate: "2024-06-07",
        name: "Summer Trip",
        startDate: "2024-06-01",
        totalAmount: 5000,
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should allow empty categories (optional)", () => {
      const result = createBudgetRequestSchema.safeParse({
        currency: "USD",
        name: "Summer Trip",
        totalAmount: 5000,
      });
      expect(result.success).toBe(true);
    });
  });

  describe("budgetFormSchema", () => {
    it.concurrent("should validate budget form", () => {
      const result = budgetFormSchema.safeParse({
        categories: [
          { amount: 2000, category: "flights" },
          { amount: 2000, category: "accommodations" },
          { amount: 1000, category: "food" },
        ],
        currency: "USD",
        endDate: "2024-06-07",
        name: "Summer Trip",
        startDate: "2024-06-01",
        totalAmount: 5000,
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject category totals exceeding budget", () => {
      const result = budgetFormSchema.safeParse({
        categories: [{ amount: 6000, category: "flights" }],
        currency: "USD",
        name: "Summer Trip",
        totalAmount: 5000,
      });
      expect(result.success).toBe(false);
    });
  });

  describe("expenseFormSchema", () => {
    it.concurrent("should validate expense form", () => {
      const result = expenseFormSchema.safeParse({
        amount: 50,
        budgetId: "123e4567-e89b-12d3-a456-426614174000",
        category: "food",
        currency: "USD",
        date: "2024-06-01",
        description: "Dinner",
        isShared: false,
      });
      expect(result.success).toBe(true);
    });

    it.concurrent("should reject negative amount", () => {
      const result = expenseFormSchema.safeParse({
        amount: -50,
        budgetId: "123e4567-e89b-12d3-a456-426614174000",
        category: "food",
        currency: "USD",
        date: "2024-06-01",
        description: "Dinner",
        isShared: false,
      });
      expect(result.success).toBe(false);
    });
  });

  describe("addExpenseRequestSchema", () => {
    it.concurrent("should validate add expense request", () => {
      const result = addExpenseRequestSchema.safeParse({
        amount: 50,
        budgetId: "123e4567-e89b-12d3-a456-426614174000",
        category: "food",
        currency: "USD",
        date: "2024-06-01",
        description: "Dinner",
        isShared: false,
      });
      expect(result.success).toBe(true);
    });
  });

  describe("createBudgetAlertRequestSchema", () => {
    it.concurrent("should validate create alert request", () => {
      const result = createBudgetAlertRequestSchema.safeParse({
        budgetId: "123e4567-e89b-12d3-a456-426614174000",
        threshold: 80,
        type: "threshold",
      });
      expect(result.success).toBe(true);
    });
  });

  describe("budgetStateSchema", () => {
    it.concurrent("should validate budget state", () => {
      const result = budgetStateSchema.safeParse({
        alerts: [],
        budgets: {},
        currencyRates: {},
        currentBudgetId: null,
        error: null,
        expenses: {},
        isLoading: false,
        lastUpdated: null,
        summary: null,
      });
      expect(result.success).toBe(true);
    });
  });
});
