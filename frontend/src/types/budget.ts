/**
 * Budget management types - now using Zod schemas for runtime validation
 *
 * @deprecated Direct type imports - use Zod schemas from /lib/schemas/budget.ts instead
 * This file now re-exports types from the Zod schemas for backward compatibility
 */

// Re-export types from Zod schemas for backward compatibility
export type {
  AddExpenseRequest,
  Budget,
  BudgetAlert,
  BudgetCategory,
  BudgetFormData,
  BudgetState,
  BudgetSummary,
  CreateBudgetAlertRequest,
  CreateBudgetRequest,
  CurrencyRate,
  Expense,
  ExpenseCategory,
  ExpenseFormData,
  ShareDetails,
  UpdateBudgetRequest,
  UpdateExpenseRequest,
} from "../lib/schemas/budget";

// Re-export schemas for validation
export {
  addExpenseRequestSchema,
  budgetAlertSchema,
  budgetCategorySchema,
  budgetFormSchema,
  budgetSchema,
  budgetStateSchema,
  budgetSummarySchema,
  calculateBudgetSummary,
  createBudgetAlertRequestSchema,
  createBudgetRequestSchema,
  currencyRateSchema,
  expenseCategorySchema,
  expenseFormSchema,
  expenseSchema,
  safeValidateBudget,
  safeValidateExpense,
  shareDetailsSchema,
  updateBudgetRequestSchema,
  updateExpenseRequestSchema,
  validateBudgetData,
  validateExpenseData,
} from "../lib/schemas/budget";

// Legacy type alias for backward compatibility
export type CurrencyCode = string;
