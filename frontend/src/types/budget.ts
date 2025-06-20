/**
 * Budget management types - now using Zod schemas for runtime validation
 *
 * @deprecated Direct type imports - use Zod schemas from /lib/schemas/budget.ts instead
 * This file now re-exports types from the Zod schemas for backward compatibility
 */

// Re-export types from Zod schemas for backward compatibility
export type {
  ExpenseCategory,
  Budget,
  BudgetCategory,
  Expense,
  ShareDetails,
  CurrencyRate,
  BudgetSummary,
  BudgetAlert,
  CreateBudgetRequest,
  UpdateBudgetRequest,
  AddExpenseRequest,
  UpdateExpenseRequest,
  CreateBudgetAlertRequest,
  BudgetState,
  BudgetFormData,
  ExpenseFormData,
} from "../lib/schemas/budget";

// Re-export schemas for validation
export {
  expenseCategorySchema,
  budgetSchema,
  budgetCategorySchema,
  expenseSchema,
  shareDetailsSchema,
  currencyRateSchema,
  budgetSummarySchema,
  budgetAlertSchema,
  createBudgetRequestSchema,
  updateBudgetRequestSchema,
  addExpenseRequestSchema,
  updateExpenseRequestSchema,
  createBudgetAlertRequestSchema,
  budgetStateSchema,
  budgetFormSchema,
  expenseFormSchema,
  validateBudgetData,
  validateExpenseData,
  safeValidateBudget,
  safeValidateExpense,
  calculateBudgetSummary,
} from "../lib/schemas/budget";

// Legacy type alias for backward compatibility
export type CurrencyCode = string;
