/**
 * @fileoverview Zod schemas for budget entities and validation.
 */

import { z } from "zod";

// Common validation patterns
const CURRENCY_CODE_SCHEMA = z
  .string()
  .length(3, "Currency code must be 3 characters")
  .regex(/^[A-Z]{3}$/, "Currency code must be uppercase letters");

const UUID_SCHEMA = z.uuid();
const DATE_STRING_SCHEMA = z.iso.datetime();
const POSITIVE_NUMBER_SCHEMA = z.number().positive();
const NON_NEGATIVE_NUMBER_SCHEMA = z.number().nonnegative();
const PERCENTAGE_SCHEMA = z.number().min(0).max(100);

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
  amount: POSITIVE_NUMBER_SCHEMA,
  category: expenseCategorySchema,
  id: UUID_SCHEMA,
  percentage: PERCENTAGE_SCHEMA,
  remaining: z.number(), // Can be negative if overspent
  spent: NON_NEGATIVE_NUMBER_SCHEMA,
});

// Share details schema
export const shareDetailsSchema = z.object({
  amount: NON_NEGATIVE_NUMBER_SCHEMA,
  isPaid: z.boolean(),
  percentage: PERCENTAGE_SCHEMA,
  userId: UUID_SCHEMA,
  userName: z.string().min(1).max(100),
});

// Budget schema
export const budgetSchema = z
  .object({
    categories: z.array(budgetCategorySchema),
    createdAt: DATE_STRING_SCHEMA,
    currency: CURRENCY_CODE_SCHEMA,
    endDate: z.string().date().optional(),
    id: UUID_SCHEMA,
    isActive: z.boolean(),
    name: z.string().min(1, "Budget name is required").max(100, "Name too long"),
    startDate: z.string().date().optional(),
    totalAmount: POSITIVE_NUMBER_SCHEMA,
    tripId: UUID_SCHEMA.optional(),
    updatedAt: DATE_STRING_SCHEMA,
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
  amount: POSITIVE_NUMBER_SCHEMA,
  attachmentUrl: z.url().optional(),
  budgetId: UUID_SCHEMA,
  category: expenseCategorySchema,
  createdAt: DATE_STRING_SCHEMA,
  currency: CURRENCY_CODE_SCHEMA,
  date: z.string().date(),
  description: z
    .string()
    .min(1, "Description is required")
    .max(200, "Description too long"),
  id: UUID_SCHEMA,
  isShared: z.boolean(),
  location: z.string().max(100).optional(),
  paymentMethod: z.string().max(50).optional(),
  shareDetails: z.array(shareDetailsSchema).optional(),
  tripId: UUID_SCHEMA.optional(),
  updatedAt: DATE_STRING_SCHEMA,
});

// Currency rate schema
export const currencyRateSchema = z.object({
  code: CURRENCY_CODE_SCHEMA,
  lastUpdated: DATE_STRING_SCHEMA,
  rate: POSITIVE_NUMBER_SCHEMA,
});

// Budget summary schema
export const budgetSummarySchema = z.object({
  dailyAverage: NON_NEGATIVE_NUMBER_SCHEMA,
  dailyLimit: POSITIVE_NUMBER_SCHEMA,
  daysRemaining: z.number().int().nonnegative().optional(),
  isOverBudget: z.boolean(),
  percentageSpent: z.number().min(0), // Can be over 100%
  projectedTotal: NON_NEGATIVE_NUMBER_SCHEMA,
  spentByCategory: z.record(expenseCategorySchema, NON_NEGATIVE_NUMBER_SCHEMA),
  totalBudget: POSITIVE_NUMBER_SCHEMA,
  totalRemaining: z.number(), // Can be negative
  totalSpent: NON_NEGATIVE_NUMBER_SCHEMA,
});

// Budget alert schema
export const budgetAlertSchema = z.object({
  budgetId: UUID_SCHEMA,
  createdAt: DATE_STRING_SCHEMA,
  id: UUID_SCHEMA,
  isRead: z.boolean(),
  message: z.string().max(500),
  threshold: PERCENTAGE_SCHEMA,
  type: z.enum(["threshold", "category", "daily"]),
});

// API Request schemas
export const createBudgetRequestSchema = z
  .object({
    categories: z
      .array(
        z.object({
          amount: POSITIVE_NUMBER_SCHEMA,
          category: expenseCategorySchema,
        })
      )
      .optional(),
    currency: CURRENCY_CODE_SCHEMA,
    endDate: z.string().date().optional(),
    name: z.string().min(1, "Budget name is required").max(100, "Name too long"),
    startDate: z.string().date().optional(),
    totalAmount: POSITIVE_NUMBER_SCHEMA,
    tripId: UUID_SCHEMA.optional(),
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
    categories: z
      .array(
        z.object({
          amount: POSITIVE_NUMBER_SCHEMA,
          category: expenseCategorySchema,
        })
      )
      .optional(),
    currency: CURRENCY_CODE_SCHEMA.optional(),
    endDate: z.string().date().optional(),
    id: UUID_SCHEMA,
    isActive: z.boolean().optional(),
    name: z.string().min(1).max(100).optional(),
    startDate: z.string().date().optional(),
    totalAmount: POSITIVE_NUMBER_SCHEMA.optional(),
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
  amount: POSITIVE_NUMBER_SCHEMA,
  attachmentUrl: z.url().optional(),
  budgetId: UUID_SCHEMA,
  category: expenseCategorySchema,
  currency: CURRENCY_CODE_SCHEMA,
  date: z.string().date(),
  description: z
    .string()
    .min(1, "Description is required")
    .max(200, "Description too long"),
  isShared: z.boolean(),
  location: z.string().max(100).optional(),
  paymentMethod: z.string().max(50).optional(),
  shareDetails: z
    .array(
      z.object({
        percentage: PERCENTAGE_SCHEMA,
        userId: UUID_SCHEMA,
        userName: z.string().min(1).max(100),
      })
    )
    .optional(),
  tripId: UUID_SCHEMA.optional(),
});

export const updateExpenseRequestSchema = z.object({
  amount: POSITIVE_NUMBER_SCHEMA.optional(),
  attachmentUrl: z.url().optional(),
  budgetId: UUID_SCHEMA.optional(),
  category: expenseCategorySchema.optional(),
  currency: CURRENCY_CODE_SCHEMA.optional(),
  date: z.string().date().optional(),
  description: z.string().min(1).max(200).optional(),
  id: UUID_SCHEMA,
  isShared: z.boolean().optional(),
  location: z.string().max(100).optional(),
  paymentMethod: z.string().max(50).optional(),
  shareDetails: z
    .array(
      z.object({
        percentage: PERCENTAGE_SCHEMA,
        userId: UUID_SCHEMA,
        userName: z.string().min(1).max(100),
      })
    )
    .optional(),
});

export const createBudgetAlertRequestSchema = z.object({
  budgetId: UUID_SCHEMA,
  message: z.string().max(500).optional(),
  threshold: PERCENTAGE_SCHEMA,
  type: z.enum(["threshold", "category", "daily"]),
});

// Budget state schema for Zustand stores
export const budgetStateSchema = z.object({
  alerts: z.array(budgetAlertSchema),
  budgets: z.record(UUID_SCHEMA, budgetSchema),
  currencyRates: z.record(CURRENCY_CODE_SCHEMA, currencyRateSchema),
  currentBudgetId: UUID_SCHEMA.nullable(),
  error: z.string().nullable(),
  expenses: z.record(UUID_SCHEMA, expenseSchema),
  isLoading: z.boolean(),
  lastUpdated: DATE_STRING_SCHEMA.nullable(),
  summary: budgetSummarySchema.nullable(),
});

// Budget form schemas (for React Hook Form)
export const budgetFormSchema = z
  .object({
    categories: z
      .array(
        z.object({
          amount: z.number().positive("Amount must be positive"),
          category: expenseCategorySchema,
        })
      )
      .min(1, "At least one category is required"),
    currency: CURRENCY_CODE_SCHEMA,
    endDate: z.string().date().optional(),
    name: z.string().min(1, "Budget name is required").max(100, "Name too long"),
    startDate: z.string().date().optional(),
    totalAmount: z.number().positive("Amount must be positive"),
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
  amount: z.number().positive("Amount must be positive"),
  budgetId: UUID_SCHEMA,
  category: expenseCategorySchema,
  currency: CURRENCY_CODE_SCHEMA,
  date: z.string().date(),
  description: z
    .string()
    .min(1, "Description is required")
    .max(200, "Description too long"),
  isShared: z.boolean(),
  location: z.string().max(100).optional(),
  paymentMethod: z.string().max(50).optional(),
  shareDetails: z
    .array(
      z.object({
        percentage: z.number().min(0.01).max(100),
        userId: UUID_SCHEMA,
        userName: z.string().min(1).max(100),
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
    dailyAverage,
    dailyLimit: Math.max(0, dailyLimit),
    daysRemaining,
    isOverBudget: totalSpent > budget.totalAmount,
    percentageSpent,
    projectedTotal,
    spentByCategory,
    totalBudget: budget.totalAmount,
    totalRemaining,
    totalSpent,
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
