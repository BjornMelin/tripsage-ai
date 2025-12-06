/**
 * @fileoverview Budget and expense management schemas with validation.
 * Includes budget allocation, expense tracking, currency conversion, and financial reporting.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";

// ===== CORE SCHEMAS =====
// Core business logic schemas for budget and expense management

/** Zod schema for expense categories with predefined budget allocation types. */
export const expenseCategorySchema = z.enum([
  "flights",
  "accommodations",
  "transportation",
  "food",
  "activities",
  "shopping",
  "other",
]);

/** TypeScript type for expense categories. */
export type ExpenseCategory = z.infer<typeof expenseCategorySchema>;

/** Zod schema for budget category allocations with spending tracking. */
export const budgetCategorySchema = z.object({
  amount: primitiveSchemas.positiveNumber,
  category: expenseCategorySchema,
  id: primitiveSchemas.uuid,
  percentage: primitiveSchemas.percentage,
  remaining: z.number(), // Can be negative if overspent
  spent: primitiveSchemas.nonNegativeNumber,
});

/** TypeScript type for budget categories. */
export type BudgetCategory = z.infer<typeof budgetCategorySchema>;

/** Zod schema for expense sharing details between participants. */
export const shareDetailsSchema = z.object({
  amount: primitiveSchemas.nonNegativeNumber,
  isPaid: z.boolean(),
  percentage: primitiveSchemas.percentage,
  userId: primitiveSchemas.uuid,
  userName: z.string().min(1).max(100),
});

/** TypeScript type for share details. */
export type ShareDetails = z.infer<typeof shareDetailsSchema>;

/**
 * Zod schema for budget data with category allocations and validation.
 * Ensures date ranges are valid and category allocations don't exceed total budget.
 * Used for budget creation, updates, and financial planning.
 */
export const budgetSchema = z
  .object({
    categories: z.array(budgetCategorySchema),
    createdAt: primitiveSchemas.isoDateTime,
    currency: primitiveSchemas.isoCurrency,
    endDate: z.iso.date().optional(),
    id: primitiveSchemas.uuid,
    isActive: z.boolean(),
    name: z
      .string()
      .min(1, { error: "Budget name is required" })
      .max(100, { error: "Name too long" }),
    startDate: z.iso.date().optional(),
    totalAmount: primitiveSchemas.positiveNumber,
    tripId: primitiveSchemas.uuid.optional(),
    updatedAt: primitiveSchemas.isoDateTime,
  })
  .refine(
    (data) => {
      if (data.startDate && data.endDate) {
        return new Date(data.endDate) > new Date(data.startDate);
      }
      return true;
    },
    {
      error: "End date must be after start date",
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
      error: "Total category amounts cannot exceed budget total",
      path: ["categories"],
    }
  );

/** TypeScript type for budget data. */
export type Budget = z.infer<typeof budgetSchema>;

/**
 * Zod schema for expense records with attachment support and sharing.
 * Validates expense details, amounts, and participant sharing arrangements.
 */
export const expenseSchema = z.object({
  amount: primitiveSchemas.positiveNumber,
  attachmentUrl: primitiveSchemas.url.optional(),
  budgetId: primitiveSchemas.uuid,
  category: expenseCategorySchema,
  createdAt: primitiveSchemas.isoDateTime,
  currency: primitiveSchemas.isoCurrency,
  date: z.iso.date(),
  description: z
    .string()
    .min(1, "Description is required")
    .max(200, "Description too long"),
  id: primitiveSchemas.uuid,
  isShared: z.boolean(),
  location: z.string().max(100).optional(),
  paymentMethod: z.string().max(50).optional(),
  shareDetails: z.array(shareDetailsSchema).optional(),
  tripId: primitiveSchemas.uuid.optional(),
  updatedAt: primitiveSchemas.isoDateTime,
});

/** TypeScript type for expense data. */
export type Expense = z.infer<typeof expenseSchema>;

/** Zod schema for currency exchange rates with update tracking. */
export const currencyRateSchema = z.object({
  code: primitiveSchemas.isoCurrency,
  lastUpdated: primitiveSchemas.isoDateTime,
  rate: primitiveSchemas.positiveNumber,
});

/** TypeScript type for currency rates. */
export type CurrencyRate = z.infer<typeof currencyRateSchema>;

// ===== REPORTING SCHEMAS =====
// Schemas for budget analysis and financial reporting

/** Zod schema for budget summary with spending analysis and projections. */
export const budgetSummarySchema = z.object({
  dailyAverage: primitiveSchemas.nonNegativeNumber,
  dailyLimit: primitiveSchemas.positiveNumber,
  daysRemaining: z.number().int().nonnegative().optional(),
  isOverBudget: z.boolean(),
  percentageSpent: z.number().min(0), // Can be over 100%
  projectedTotal: primitiveSchemas.nonNegativeNumber,
  spentByCategory: z.partialRecord(
    expenseCategorySchema,
    primitiveSchemas.nonNegativeNumber
  ),
  totalBudget: primitiveSchemas.positiveNumber,
  totalRemaining: z.number(), // Can be negative
  totalSpent: primitiveSchemas.nonNegativeNumber,
});

/** TypeScript type for budget summaries. */
export type BudgetSummary = z.infer<typeof budgetSummarySchema>;

/** Zod schema for budget alerts with notification thresholds. */
export const budgetAlertSchema = z.object({
  budgetId: primitiveSchemas.uuid,
  createdAt: primitiveSchemas.isoDateTime,
  id: primitiveSchemas.uuid,
  isRead: z.boolean(),
  message: z.string().max(500),
  threshold: primitiveSchemas.percentage,
  type: z.enum(["threshold", "category", "daily"]),
});

/** TypeScript type for budget alerts. */
export type BudgetAlert = z.infer<typeof budgetAlertSchema>;

// ===== API SCHEMAS =====
// Request/response schemas for budget API endpoints

/**
 * API request schema for creating budgets with category allocations.
 * Validates budget parameters and ensures category amounts don't exceed total.
 */
export const createBudgetRequestSchema = z
  .object({
    categories: z
      .array(
        z.object({
          amount: primitiveSchemas.positiveNumber,
          category: expenseCategorySchema,
        })
      )
      .optional(),
    currency: primitiveSchemas.isoCurrency,
    endDate: z.iso.date().optional(),
    name: z.string().min(1, "Budget name is required").max(100, "Name too long"),
    startDate: z.iso.date().optional(),
    totalAmount: primitiveSchemas.positiveNumber,
    tripId: primitiveSchemas.uuid.optional(),
  })
  .refine(
    (data) => {
      if (data.startDate && data.endDate) {
        return new Date(data.endDate) > new Date(data.startDate);
      }
      return true;
    },
    {
      error: "End date must be after start date",
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
      error: "Total category amounts cannot exceed budget total",
      path: ["categories"],
    }
  );

/** TypeScript type for budget creation requests. */
export type CreateBudgetRequest = z.infer<typeof createBudgetRequestSchema>;

/**
 * API request schema for updating existing budgets.
 * Allows partial updates while maintaining validation constraints.
 */
export const updateBudgetRequestSchema = z
  .object({
    categories: z
      .array(
        z.object({
          amount: primitiveSchemas.positiveNumber,
          category: expenseCategorySchema,
        })
      )
      .optional(),
    currency: primitiveSchemas.isoCurrency.optional(),
    endDate: z.iso.date().optional(),
    id: primitiveSchemas.uuid,
    isActive: z.boolean().optional(),
    name: z.string().min(1).max(100).optional(),
    startDate: z.iso.date().optional(),
    totalAmount: primitiveSchemas.positiveNumber.optional(),
  })
  .refine(
    (data) => {
      if (data.startDate && data.endDate) {
        return new Date(data.endDate) > new Date(data.startDate);
      }
      return true;
    },
    {
      error: "End date must be after start date",
      path: ["endDate"],
    }
  );

/** TypeScript type for budget update requests. */
export type UpdateBudgetRequest = z.infer<typeof updateBudgetRequestSchema>;

/**
 * API request schema for adding expenses with sharing support.
 * Validates expense details and participant sharing arrangements.
 */
export const addExpenseRequestSchema = z.object({
  amount: primitiveSchemas.positiveNumber,
  attachmentUrl: primitiveSchemas.url.optional(),
  budgetId: primitiveSchemas.uuid,
  category: expenseCategorySchema,
  currency: primitiveSchemas.isoCurrency,
  date: z.iso.date(),
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
        percentage: primitiveSchemas.percentage,
        userId: primitiveSchemas.uuid,
        userName: z.string().min(1).max(100),
      })
    )
    .optional(),
  tripId: primitiveSchemas.uuid.optional(),
});

/** TypeScript type for expense creation requests. */
export type AddExpenseRequest = z.infer<typeof addExpenseRequestSchema>;

/**
 * API request schema for updating existing expenses.
 * Allows partial updates of expense properties.
 */
export const updateExpenseRequestSchema = z.object({
  amount: primitiveSchemas.positiveNumber.optional(),
  attachmentUrl: primitiveSchemas.url.optional(),
  budgetId: primitiveSchemas.uuid.optional(),
  category: expenseCategorySchema.optional(),
  currency: primitiveSchemas.isoCurrency.optional(),
  date: z.iso.date().optional(),
  description: z.string().min(1).max(200).optional(),
  id: primitiveSchemas.uuid,
  isShared: z.boolean().optional(),
  location: z.string().max(100).optional(),
  paymentMethod: z.string().max(50).optional(),
  shareDetails: z
    .array(
      z.object({
        percentage: primitiveSchemas.percentage,
        userId: primitiveSchemas.uuid,
        userName: z.string().min(1).max(100),
      })
    )
    .optional(),
});

/** TypeScript type for expense update requests. */
export type UpdateExpenseRequest = z.infer<typeof updateExpenseRequestSchema>;

/** API request schema for creating budget alerts with notification settings. */
export const createBudgetAlertRequestSchema = z.object({
  budgetId: primitiveSchemas.uuid,
  message: z.string().max(500).optional(),
  threshold: primitiveSchemas.percentage,
  type: z.enum(["threshold", "category", "daily"]),
});

/** TypeScript type for budget alert creation requests. */
export type CreateBudgetAlertRequest = z.infer<typeof createBudgetAlertRequestSchema>;

// ===== FORM SCHEMAS =====
// UI form validation schemas with user-friendly error messages

/**
 * Form schema for creating and editing budgets.
 * Includes user-friendly validation messages and category allocation checks.
 */
export const budgetFormSchema = z
  .object({
    categories: z
      .array(
        z.object({
          amount: z.number().positive({ error: "Amount must be positive" }),
          category: expenseCategorySchema,
        })
      )
      .min(1, { error: "At least one category is required" }),
    currency: primitiveSchemas.isoCurrency,
    endDate: z.iso.date().optional(),
    name: z
      .string()
      .min(1, { error: "Budget name is required" })
      .max(100, { error: "Name too long" }),
    startDate: z.iso.date().optional(),
    totalAmount: z.number().positive({ error: "Amount must be positive" }),
  })
  .refine(
    (data) => {
      if (data.startDate && data.endDate) {
        return new Date(data.endDate) > new Date(data.startDate);
      }
      return true;
    },
    {
      error: "End date must be after start date",
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
      error: "Total category amounts cannot exceed budget total",
      path: ["categories"],
    }
  );

/** TypeScript type for budget form data. */
export type BudgetFormData = z.infer<typeof budgetFormSchema>;

/**
 * Form schema for creating and editing expenses.
 * Includes attachment validation, sharing details, and user-friendly error messages.
 */
export const expenseFormSchema = z.object({
  amount: z.number().positive({ error: "Amount must be positive" }),
  budgetId: primitiveSchemas.uuid,
  category: expenseCategorySchema,
  currency: primitiveSchemas.isoCurrency,
  date: z.iso.date(),
  description: z
    .string()
    .min(1, { error: "Description is required" })
    .max(200, { error: "Description too long" }),
  isShared: z.boolean(),
  location: z.string().max(100).optional(),
  paymentMethod: z.string().max(50).optional(),
  receipt: primitiveSchemas.url.optional(),
  shareDetails: z
    .array(
      z.object({
        percentage: z.number().min(0.01).max(100),
        userId: primitiveSchemas.uuid,
        userName: z.string().min(1).max(100),
      })
    )
    .optional(),
  tags: z.array(z.string().max(50)).max(5).optional(),
});

/** TypeScript type for expense form data. */
export type ExpenseFormData = z.infer<typeof expenseFormSchema>;

// ===== STATE SCHEMAS =====
// Schemas for client-side state management

/** Zod schema for budget state management in Zustand stores. */
export const budgetStateSchema = z.object({
  alerts: z.array(budgetAlertSchema),
  budgets: z.record(primitiveSchemas.uuid, budgetSchema),
  currencyRates: z.record(primitiveSchemas.isoCurrency, currencyRateSchema),
  currentBudgetId: primitiveSchemas.uuid.nullable(),
  error: z.string().nullable(),
  expenses: z.record(primitiveSchemas.uuid, expenseSchema),
  isLoading: z.boolean(),
  lastUpdated: primitiveSchemas.isoDateTime.nullable(),
  summary: budgetSummarySchema.nullable(),
});

/** TypeScript type for budget state. */
export type BudgetState = z.infer<typeof budgetStateSchema>;

// ===== UTILITY FUNCTIONS =====
// Validation helpers and business logic functions

/**
 * Validates budget data from external sources.
 * Performs comprehensive validation including category allocation checks.
 *
 * @param data - Raw budget data to validate
 * @returns Parsed and validated budget data
 * @throws {ZodError} When validation fails with detailed error information
 *
 * @example
 * ```typescript
 * const rawData = { name: "Trip Budget", totalAmount: 1000 };
 * const budget = validateBudgetData(rawData);
 * ```
 */
export const validateBudgetData = (data: unknown): Budget => {
  return budgetSchema.parse(data);
};

/**
 * Validates expense data from external sources.
 * Ensures expense details meet business requirements.
 *
 * @param data - Raw expense data to validate
 * @returns Parsed and validated expense data
 * @throws {ZodError} When validation fails with detailed error information
 */
export const validateExpenseData = (data: unknown): Expense => {
  return expenseSchema.parse(data);
};

/**
 * Safely validates budget data with error handling.
 *
 * @param data - Raw budget data to validate
 * @returns Validation result with success/error information
 */
export const safeValidateBudget = (data: unknown) => {
  return budgetSchema.safeParse(data);
};

/**
 * Safely validates expense data with error handling.
 *
 * @param data - Raw expense data to validate
 * @returns Validation result with success/error information
 */
export const safeValidateExpense = (data: unknown) => {
  return expenseSchema.safeParse(data);
};

/**
 * Calculates comprehensive budget summary including spending analysis and projections.
 * Analyzes spending patterns, calculates daily averages, and provides financial insights.
 *
 * @param budget - Budget to analyze
 * @param expenses - Associated expenses for calculation
 * @returns Comprehensive budget summary with percentages and projections
 *
 * @example
 * ```typescript
 * const summary = calculateBudgetSummary(budget, expenses);
 * if (summary.isOverBudget) {
 *   alert(`Budget exceeded by ${summary.totalRemaining}`);
 * }
 * ```
 */
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

/**
 * Form schema for budget category configuration.
 * Includes visual customization options and allocation validation.
 */
export const budgetCategoryFormSchema = z.object({
  allocated: z.number().min(0, { error: "Allocated amount cannot be negative" }),
  color: z
    .string()
    .regex(/^#[0-9A-F]{6}$/i, { error: "Invalid color format" })
    .optional(),
  currency: primitiveSchemas.isoCurrency,
  icon: z.string().optional(),
  name: z
    .string()
    .min(1, { error: "Category name is required" })
    .max(50, { error: "Name too long" }),
});

/** TypeScript type for budget category form data. */
export type BudgetCategoryFormData = z.infer<typeof budgetCategoryFormSchema>;
