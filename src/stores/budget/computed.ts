/**
 * @fileoverview Computed state and pure helpers for the budget store.
 */

import type { Budget, BudgetSummary, Expense, ExpenseCategory } from "@schemas/budget";
import type { BudgetState } from "./types";

const SELECT_RECENT_EXPENSES_LIMIT = 10;

type TimestampedExpense = { expense: Expense; timestamp: number };

const compareByTimestampDesc = (a: TimestampedExpense, b: TimestampedExpense): number =>
  b.timestamp - a.timestamp;

export function selectRecentExpensesFromExpenses(
  expensesByBudget: Record<string, Expense[]>
): Expense[] {
  const candidates: TimestampedExpense[] = [];

  for (const expenses of Object.values(expensesByBudget)) {
    for (const expense of expenses) {
      const parsedTimestamp = Date.parse(expense.date);
      candidates.push({
        expense,
        timestamp: Number.isFinite(parsedTimestamp) ? parsedTimestamp : 0,
      });
    }
  }

  return candidates
    .sort(compareByTimestampDesc)
    .slice(0, SELECT_RECENT_EXPENSES_LIMIT)
    .map((entry) => entry.expense);
}

export function calculateBudgetSummary(
  budget: Budget,
  expenses: Expense[]
): BudgetSummary {
  const totalBudget = budget.totalAmount;
  const totalSpent = expenses.reduce((sum, expense) => sum + expense.amount, 0);
  const totalRemaining = totalBudget - totalSpent;
  const percentageSpent = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0;

  // Calculate spent by category
  const spentByCategory = expenses.reduce(
    (acc, expense) => {
      const category = expense.category;
      acc[category] = (acc[category] || 0) + expense.amount;
      return acc;
    },
    {} as Record<ExpenseCategory, number>
  );

  // Calculate days remaining if dates are provided
  let daysRemaining: number | undefined;
  if (budget.startDate && budget.endDate) {
    const endDate = new Date(budget.endDate);
    const today = new Date();
    const diffTime = endDate.getTime() - today.getTime();
    daysRemaining = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    daysRemaining = daysRemaining < 0 ? 0 : daysRemaining;
  }

  // Calculate daily metrics
  const startDate = budget.startDate ? new Date(budget.startDate) : undefined;
  const endDate = budget.endDate ? new Date(budget.endDate) : undefined;

  let dailyAverage = 0;
  let dailyLimit = 0;
  let projectedTotal = totalSpent;

  if (startDate && endDate) {
    const totalDays = Math.max(
      1,
      Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24))
    );
    const elapsedDays = Math.max(
      1,
      Math.ceil((Date.now() - startDate.getTime()) / (1000 * 60 * 60 * 24))
    );

    dailyAverage = elapsedDays > 0 ? totalSpent / elapsedDays : 0;
    dailyLimit =
      daysRemaining && daysRemaining > 0 ? totalRemaining / daysRemaining : 0;
    projectedTotal = dailyAverage * totalDays;
  }

  return {
    dailyAverage,
    dailyLimit,
    daysRemaining,
    isOverBudget: totalRemaining < 0,
    percentageSpent,
    projectedTotal,
    spentByCategory,
    totalBudget,
    totalRemaining,
    totalSpent,
  };
}

export function getBudgetsByTrip(
  budgets: Record<string, Budget>
): Record<string, string[]> {
  return Object.values(budgets).reduce<Record<string, string[]>>((acc, budget) => {
    if (budget.tripId) {
      if (!acc[budget.tripId]) acc[budget.tripId] = [];
      acc[budget.tripId].push(budget.id);
    }
    return acc;
  }, {});
}

/** Compute derived budget properties. */
export function computeBudgetState(state: BudgetState): Partial<BudgetState> {
  // Compute activeBudget
  const activeBudget = state.activeBudgetId
    ? (state.budgets[state.activeBudgetId] ?? null)
    : null;

  // Compute budgetSummary
  const budgetSummary = activeBudget
    ? calculateBudgetSummary(activeBudget, state.expenses[activeBudget.id] ?? [])
    : null;

  // Compute budgetsByTrip and recentExpenses
  const budgetsByTrip = getBudgetsByTrip(state.budgets);
  const recentExpenses = selectRecentExpensesFromExpenses(state.expenses);

  return { activeBudget, budgetSummary, budgetsByTrip, recentExpenses };
}
