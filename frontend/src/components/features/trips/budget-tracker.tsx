"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useBudgetStore } from "@/stores/budget-store";
import { useCurrencyStore } from "@/stores/currency-store";
import type { BudgetSummary } from "@/types/budget";
import { AlertTriangle, DollarSign, Plus, Target, TrendingUp } from "lucide-react";
import { useMemo } from "react";

interface BudgetTrackerProps {
  tripId?: string;
  budgetId?: string;
  className?: string;
  showActions?: boolean;
  onAddExpense?: () => void;
  onCreateBudget?: () => void;
}

export function BudgetTracker({
  tripId,
  budgetId,
  className,
  showActions = true,
  onAddExpense,
  onCreateBudget,
}: BudgetTrackerProps) {
  const { budgets, activeBudget, budgetSummary, budgetsByTrip, setActiveBudget } =
    useBudgetStore();

  const { baseCurrency } = useCurrencyStore();

  const targetBudget = useMemo(() => {
    if (budgetId) {
      return budgets[budgetId] || null;
    }
    if (tripId) {
      const tripBudgetIds = budgetsByTrip[tripId] || [];
      if (tripBudgetIds.length > 0) {
        return budgets[tripBudgetIds[0]] || null;
      }
    }
    return activeBudget;
  }, [budgetId, tripId, budgets, budgetsByTrip, activeBudget]);

  const summary = useMemo(() => {
    if (!targetBudget) return null;

    // If this is the active budget, use the computed summary
    if (targetBudget.id === activeBudget?.id) {
      return budgetSummary;
    }

    // Otherwise, manually compute for this specific budget
    // This is a simplified version - in production you'd want to
    // fetch expenses for this specific budget
    const totalBudget = targetBudget.totalAmount;
    const totalSpent = 0; // Would be calculated from expenses
    const totalRemaining = totalBudget - totalSpent;
    const percentageSpent = totalBudget > 0 ? (totalSpent / totalBudget) * 100 : 0;

    return {
      totalBudget,
      totalSpent,
      totalRemaining,
      percentageSpent,
      spentByCategory: {},
      dailyAverage: 0,
      dailyLimit: 0,
      projectedTotal: totalSpent,
      isOverBudget: totalRemaining < 0,
      daysRemaining: undefined,
    } as BudgetSummary;
  }, [targetBudget, activeBudget, budgetSummary]);

  if (!targetBudget || !summary) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Budget Tracker
          </CardTitle>
          <CardDescription>No budget found for this trip</CardDescription>
        </CardHeader>
        <CardContent>
          {showActions && onCreateBudget && (
            <Button onClick={onCreateBudget} className="w-full">
              <Plus className="h-4 w-4 mr-2" />
              Create Budget
            </Button>
          )}
        </CardContent>
      </Card>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: targetBudget.currency,
    }).format(amount);
  };

  const getStatusColor = (percentage: number) => {
    if (percentage >= 100) return "text-destructive";
    if (percentage >= 80) return "text-orange-600";
    if (percentage >= 60) return "text-yellow-600";
    return "text-green-600";
  };

  const _getProgressColor = (percentage: number) => {
    if (percentage >= 100) return "bg-destructive";
    if (percentage >= 80) return "bg-orange-500";
    if (percentage >= 60) return "bg-yellow-500";
    return "bg-primary";
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            {targetBudget.name}
          </CardTitle>
          {summary.isOverBudget && (
            <Badge variant="destructive" className="gap-1">
              <AlertTriangle className="h-3 w-3" />
              Over Budget
            </Badge>
          )}
        </div>
        <CardDescription>
          Budget for{" "}
          {targetBudget.startDate && targetBudget.endDate
            ? `${targetBudget.startDate} - ${targetBudget.endDate}`
            : "trip planning"}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Main Budget Overview */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span>Spent</span>
            <span className={getStatusColor(summary.percentageSpent)}>
              {formatCurrency(summary.totalSpent)} of{" "}
              {formatCurrency(summary.totalBudget)}
            </span>
          </div>
          <Progress value={Math.min(summary.percentageSpent, 100)} className="h-2" />
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{summary.percentageSpent.toFixed(1)}% used</span>
            <span>
              {summary.totalRemaining >= 0
                ? `${formatCurrency(summary.totalRemaining)} remaining`
                : `${formatCurrency(Math.abs(summary.totalRemaining))} over budget`}
            </span>
          </div>
        </div>

        {/* Daily Metrics */}
        {summary.dailyAverage > 0 && (
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                <TrendingUp className="h-3 w-3" />
                Daily Average
              </div>
              <div className="text-lg font-semibold">
                {formatCurrency(summary.dailyAverage)}
              </div>
            </div>

            {summary.dailyLimit > 0 && (
              <div className="space-y-1">
                <div className="flex items-center gap-1 text-sm text-muted-foreground">
                  <Target className="h-3 w-3" />
                  Daily Limit
                </div>
                <div className="text-lg font-semibold">
                  {formatCurrency(summary.dailyLimit)}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Projected Total */}
        {summary.projectedTotal > summary.totalSpent && (
          <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">Projected Total</span>
            </div>
            <span
              className={`font-semibold ${
                summary.projectedTotal > summary.totalBudget
                  ? "text-destructive"
                  : "text-foreground"
              }`}
            >
              {formatCurrency(summary.projectedTotal)}
            </span>
          </div>
        )}

        {/* Category Breakdown */}
        {Object.keys(summary.spentByCategory).length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Category Breakdown</h4>
            {Object.entries(summary.spentByCategory).map(([category, amount]) => {
              const percentage =
                summary.totalBudget > 0 ? (amount / summary.totalBudget) * 100 : 0;

              return (
                <div key={category} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="capitalize">{category}</span>
                    <span>{formatCurrency(amount)}</span>
                  </div>
                  <Progress value={percentage} className="h-1" />
                </div>
              );
            })}
          </div>
        )}

        {/* Actions */}
        {showActions && (
          <div className="flex gap-2">
            {onAddExpense && (
              <Button
                variant="outline"
                size="sm"
                onClick={onAddExpense}
                className="flex-1"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Expense
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setActiveBudget(targetBudget.id)}
              className="flex-1"
            >
              <DollarSign className="h-4 w-4 mr-2" />
              View Details
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
