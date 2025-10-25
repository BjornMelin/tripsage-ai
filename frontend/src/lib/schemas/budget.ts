/**
 * @fileoverview Zod schemas for budget entities and validation.
 */

import { z } from "zod";

// Common validation patterns
const currencyCodeSchema = z
  .string()
  .length(3, "Currency code must be 3 characters")
  .regex(/^[A-Z]{3}$/, "Currency code must be uppercase letters");

const uuidSchema = z.string().uuid();
const dateStringSchema = z.string().datetime();
const positiveNumberSchema = z.number().positive();
const nonNegativeNumberSchema = z.number().nonnegative();
const percentageSchema = z.number().min(0).max(100);

// Expense category enum
export const expenseCategorySchema = z.enum([
  "flights",
  "accommodations",
  "transportation",
  "food",
  "activities",
  "shopping",
  "other",
]);

// Budget category schema
export const budgetCategorySchema = z.object({
  id: uuidSchema,
  category: expenseCategorySchema,
  amount: positiveNumberSchema,
  spent: nonNegativeNumberSchema,
  remaining: z.number(), // Can be negative if overspent
  percentage: percentageSchema,
});

// Share details schema
export const shareDetailsSchema = z.object({
  userId: uuidSchema,
  userName: z.string().min(1).max(100),
  percentage: percentageSchema,
  amount: nonNegativeNumberSchema,
  isPaid: z.boolean(),
});

// Budget schema
export const budgetSchema = z
  .object({
    id: uuidSchema,
    tripId: uuidSchema.optional(),
    name: z.string().min(1, "Budget name is required").max(100, "Name too long"),
    totalAmount: positiveNumberSchema,
    currency: currencyCodeSchema,
    startDate: z.string().date().optional(),
    endDate: z.string().date().optional(),
    categories: z.array(budgetCategorySchema),
    isActive: z.boolean(),
    createdAt: dateStringSchema,
    updatedAt: dateStringSchema,
  })
  .refine(
    (data) => {
      if (data.startDate && data.endDate) {
        return new Date(data.endDate) > new Date(data.startDate);
      }
      return true;
    },
    {
      message: "End date must be after start date",
      path: ["endDate"],
    }
  )
  .refine(
    (data) => {
      // Validate that category amounts don't exceed total budget
      const totalCategoryAmount = data.categories.reduce(
        (sum, category) => sum + category.amount,
        0
      );
      return totalCategoryAmount <= data.totalAmount;
    },
    {
      message: "Total category amounts cannot exceed budget total",
      path: ["categories"],
    }
  );

// Expense schema
export const expenseSchema = z.object({
  id: uuidSchema,
  budgetId: uuidSchema,
  tripId: uuidSchema.optional(),
  category: expenseCategorySchema,
  description: z
    .string()
    .min(1, "Description is required")
    .max(200, "Description too long"),
  amount: positiveNumberSchema,
  currency: currencyCodeSchema,
  date: z.string().date(),
  location: z.string().max(100).optional(),
  paymentMethod: z.string().max(50).optional(),
  attachmentUrl: z.string().url().optional(),
  isShared: z.boolean(),
  shareDetails: z.array(shareDetailsSchema).optional(),
  createdAt: dateStringSchema,
  updatedAt: dateStringSchema,
});

// Currency rate schema
export const currencyRateSchema = z.object({
  code: currencyCodeSchema,
  rate: positiveNumberSchema,
  lastUpdated: dateStringSchema,
});

// Budget summary schema
export const budgetSummarySchema = z.object({
  totalBudget: positiveNumberSchema,
  totalSpent: nonNegativeNumberSchema,
  totalRemaining: z.number(), // Can be negative
  percentageSpent: z.number().min(0), // Can be over 100%
  spentByCategory: z.record(expenseCategorySchema, nonNegativeNumberSchema),
  dailyAverage: nonNegativeNumberSchema,
  dailyLimit: positiveNumberSchema,
  projectedTotal: nonNegativeNumberSchema,
  isOverBudget: z.boolean(),
  daysRemaining: z.number().int().nonnegative().optional(),
});

// Budget alert schema
export const budgetAlertSchema = z.object({
  id: uuidSchema,
  budgetId: uuidSchema,
  type: z.enum(["threshold", "category", "daily"]),
  threshold: percentageSchema,
  message: z.string().max(500),
  isRead: z.boolean(),
  createdAt: dateStringSchema,
});

// API Request schemas
export const createBudgetRequestSchema = z
  .object({
    name: z.string().min(1, "Budget name is required").max(100, "Name too long"),
    totalAmount: positiveNumberSchema,
    currency: currencyCodeSchema,
    tripId: uuidSchema.optional(),
    startDate: z.string().date().optional(),
    endDate: z.string().date().optional(),
    categories: z
      .array(
        z.object({
          category: expenseCategorySchema,
          amount: positiveNumberSchema,
        })
      )
      .optional(),
  })
  .refine(
    (data) => {
      if (data.startDate && data.endDate) {
        return new Date(data.endDate) > new Date(data.startDate);
      }
      return true;
    },
    {
      message: "End date must be after start date",
      path: ["endDate"],
    }
  )
  .refine(
    (data) => {
      if (data.categories) {
        const totalCategoryAmount = data.categories.reduce(
          (sum, category) => sum + category.amount,
          0
        );
        return totalCategoryAmount <= data.totalAmount;
      }
      return true;
    },
    {
      message: "Total category amounts cannot exceed budget total",
      path: ["categories"],
    }
  );

export const updateBudgetRequestSchema = z
  .object({
    id: uuidSchema,
    name: z.string().min(1).max(100).optional(),
    totalAmount: positiveNumberSchema.optional(),
    currency: currencyCodeSchema.optional(),
    startDate: z.string().date().optional(),
    endDate: z.string().date().optional(),
    categories: z
      .array(
        z.object({
          category: expenseCategorySchema,
          amount: positiveNumberSchema,
        })
      )
      .optional(),
    isActive: z.boolean().optional(),
  })
  .refine(
    (data) => {
      if (data.startDate && data.endDate) {
        return new Date(data.endDate) > new Date(data.startDate);
      }
      return true;
    },
    {
      message: "End date must be after start date",
      path: ["endDate"],
    }
  );

export const addExpenseRequestSchema = z.object({
  budgetId: uuidSchema,
  tripId: uuidSchema.optional(),
  category: expenseCategorySchema,
  description: z
    .string()
    .min(1, "Description is required")
    .max(200, "Description too long"),
  amount: positiveNumberSchema,
  currency: currencyCodeSchema,
  date: z.string().date(),
  location: z.string().max(100).optional(),
  paymentMethod: z.string().max(50).optional(),
  attachmentUrl: z.string().url().optional(),
  isShared: z.boolean(),
  shareDetails: z
    .array(
      z.object({
        userId: uuidSchema,
        userName: z.string().min(1).max(100),
        percentage: percentageSchema,
      })
    )
    .optional(),
});

export const updateExpenseRequestSchema = z.object({
  id: uuidSchema,
  budgetId: uuidSchema.optional(),
  category: expenseCategorySchema.optional(),
  description: z.string().min(1).max(200).optional(),
  amount: positiveNumberSchema.optional(),
  currency: currencyCodeSchema.optional(),
  date: z.string().date().optional(),
  location: z.string().max(100).optional(),
  paymentMethod: z.string().max(50).optional(),
  attachmentUrl: z.string().url().optional(),
  isShared: z.boolean().optional(),
  shareDetails: z
    .array(
      z.object({
        userId: uuidSchema,
        userName: z.string().min(1).max(100),
        percentage: percentageSchema,
      })
    )
    .optional(),
});

export const createBudgetAlertRequestSchema = z.object({
  budgetId: uuidSchema,
  type: z.enum(["threshold", "category", "daily"]),
  threshold: percentageSchema,
  message: z.string().max(500).optional(),
});

// Budget state schema for Zustand stores
export const budgetStateSchema = z.object({
  budgets: z.record(uuidSchema, budgetSchema),
  currentBudgetId: uuidSchema.nullable(),
  expenses: z.record(uuidSchema, expenseSchema),
  alerts: z.array(budgetAlertSchema),
  summary: budgetSummarySchema.nullable(),
  currencyRates: z.record(currencyCodeSchema, currencyRateSchema),
  isLoading: z.boolean(),
  error: z.string().nullable(),
  lastUpdated: dateStringSchema.nullable(),
});

// Budget form schemas (for React Hook Form)
export const budgetFormSchema = z
  .object({
    name: z.string().min(1, "Budget name is required").max(100, "Name too long"),
    totalAmount: z.number().positive("Amount must be positive"),
    currency: currencyCodeSchema,
    startDate: z.string().date().optional(),
    endDate: z.string().date().optional(),
    categories: z
      .array(
        z.object({
          category: expenseCategorySchema,
          amount: z.number().positive("Amount must be positive"),
        })
      )
      .min(1, "At least one category is required"),
  })
  .refine(
    (data) => {
      if (data.startDate && data.endDate) {
        return new Date(data.endDate) > new Date(data.startDate);
      }
      return true;
    },
    {
      message: "End date must be after start date",
      path: ["endDate"],
    }
  )
  .refine(
    (data) => {
      const totalCategoryAmount = data.categories.reduce(
        (sum, category) => sum + category.amount,
        0
      );
      return totalCategoryAmount <= data.totalAmount;
    },
    {
      message: "Total category amounts cannot exceed budget total",
      path: ["categories"],
    }
  );

export const expenseFormSchema = z.object({
  budgetId: uuidSchema,
  category: expenseCategorySchema,
  description: z
    .string()
    .min(1, "Description is required")
    .max(200, "Description too long"),
  amount: z.number().positive("Amount must be positive"),
  currency: currencyCodeSchema,
  date: z.string().date(),
  location: z.string().max(100).optional(),
  paymentMethod: z.string().max(50).optional(),
  isShared: z.boolean(),
  shareDetails: z
    .array(
      z.object({
        userId: uuidSchema,
        userName: z.string().min(1).max(100),
        percentage: z.number().min(0.01).max(100),
      })
    )
    .optional(),
});

// Validation utilities
export const validateBudgetData = (data: unknown) => {
  return budgetSchema.parse(data);
};

export const validateExpenseData = (data: unknown) => {
  return expenseSchema.parse(data);
};

export const safeValidateBudget = (data: unknown) => {
  return budgetSchema.safeParse(data);
};

export const safeValidateExpense = (data: unknown) => {
  return expenseSchema.safeParse(data);
};

// Helper functions
export const calculateBudgetSummary = (
  budget: Budget,
  expenses: Expense[]
): BudgetSummary => {
  const budgetExpenses = expenses.filter((expense) => expense.budgetId === budget.id);
  const totalSpent = budgetExpenses.reduce((sum, expense) => sum + expense.amount, 0);
  const totalRemaining = budget.totalAmount - totalSpent;
  const percentageSpent = (totalSpent / budget.totalAmount) * 100;

  const spentByCategory = budget.categories.reduce(
    (acc, category) => {
      const categoryExpenses = budgetExpenses.filter(
        (expense) => expense.category === category.category
      );
      acc[category.category] = categoryExpenses.reduce(
        (sum, expense) => sum + expense.amount,
        0
      );
      return acc;
    },
    {} as Record<ExpenseCategory, number>
  );

  // Calculate daily averages if dates are available
  let dailyAverage = 0;
  let dailyLimit = budget.totalAmount;
  let daysRemaining: number | undefined;

  if (budget.startDate && budget.endDate) {
    const startDate = new Date(budget.startDate);
    const endDate = new Date(budget.endDate);
    const today = new Date();

    const totalDays = Math.ceil(
      (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)
    );
    const daysPassed = Math.ceil(
      (today.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)
    );
    daysRemaining = Math.max(0, totalDays - daysPassed);

    if (daysPassed > 0) {
      dailyAverage = totalSpent / daysPassed;
    }

    if (daysRemaining > 0) {
      dailyLimit = totalRemaining / daysRemaining;
    }
  }

  const projectedTotal =
    budget.startDate && budget.endDate
      ? totalSpent + dailyAverage * (daysRemaining || 0)
      : totalSpent;

  return {
    totalBudget: budget.totalAmount,
    totalSpent,
    totalRemaining,
    percentageSpent,
    spentByCategory,
    dailyAverage,
    dailyLimit: Math.max(0, dailyLimit),
    projectedTotal,
    isOverBudget: totalSpent > budget.totalAmount,
    daysRemaining,
  };
};

// Type exports
export type ExpenseCategory = z.infer<typeof expenseCategorySchema>;
export type Budget = z.infer<typeof budgetSchema>;
export type BudgetCategory = z.infer<typeof budgetCategorySchema>;
export type Expense = z.infer<typeof expenseSchema>;
export type ShareDetails = z.infer<typeof shareDetailsSchema>;
export type CurrencyRate = z.infer<typeof currencyRateSchema>;
export type BudgetSummary = z.infer<typeof budgetSummarySchema>;
export type BudgetAlert = z.infer<typeof budgetAlertSchema>;
export type CreateBudgetRequest = z.infer<typeof createBudgetRequestSchema>;
export type UpdateBudgetRequest = z.infer<typeof updateBudgetRequestSchema>;
export type AddExpenseRequest = z.infer<typeof addExpenseRequestSchema>;
export type UpdateExpenseRequest = z.infer<typeof updateExpenseRequestSchema>;
export type CreateBudgetAlertRequest = z.infer<typeof createBudgetAlertRequestSchema>;
export type BudgetState = z.infer<typeof budgetStateSchema>;
export type BudgetFormData = z.infer<typeof budgetFormSchema>;
export type ExpenseFormData = z.infer<typeof expenseFormSchema>;
