/**
 * Enhanced Budget Form with comprehensive Zod validation
 * Demonstrates latest validation patterns and error handling
 */

"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useZodForm } from "@/lib/hooks/use-zod-form";
import {
  type BudgetFormData,
  type ExpenseCategory,
  budgetFormSchema,
} from "@/lib/schemas/budget";
import { cn } from "@/lib/utils";
import {
  AlertCircle,
  Calculator,
  DollarSign,
  Loader2,
  Plus,
  TrendingUp,
  X,
} from "lucide-react";
import React, { useCallback, useState } from "react";
import { z } from "zod";

// Enhanced form data with additional UI state
const enhancedBudgetFormSchema = budgetFormSchema.and(
  z.object({
    // UI-specific fields
    autoAllocate: z.boolean().optional(),
    enableAlerts: z.boolean().optional(),
    alertThreshold: z.number().min(50).max(95).optional(),
    notes: z.string().max(500).optional(),
  })
);

type EnhancedBudgetFormData = z.infer<typeof enhancedBudgetFormSchema>;

interface BudgetFormProps {
  onSubmit: (data: BudgetFormData) => Promise<void>;
  onCancel?: () => void;
  initialData?: Partial<EnhancedBudgetFormData>;
  currencies?: Array<{ code: string; name: string; symbol: string }>;
  tripId?: string;
  className?: string;
}

// Default currencies (would typically come from API)
const DEFAULT_CURRENCIES = [
  { code: "USD", name: "US Dollar", symbol: "$" },
  { code: "EUR", name: "Euro", symbol: "€" },
  { code: "GBP", name: "British Pound", symbol: "£" },
  { code: "JPY", name: "Japanese Yen", symbol: "¥" },
  { code: "CAD", name: "Canadian Dollar", symbol: "C$" },
  { code: "AUD", name: "Australian Dollar", symbol: "A$" },
];

// Expense category options with descriptions
const EXPENSE_CATEGORIES = [
  {
    value: "flights",
    label: "Flights",
    description: "Airfare and airline fees",
    icon: "✈️",
  },
  {
    value: "accommodations",
    label: "Hotels",
    description: "Lodging and accommodation",
    icon: "🏨",
  },
  {
    value: "transportation",
    label: "Transport",
    description: "Local transport and car rentals",
    icon: "🚗",
  },
  {
    value: "food",
    label: "Food & Dining",
    description: "Meals and beverages",
    icon: "🍽️",
  },
  {
    value: "activities",
    label: "Activities",
    description: "Tours, attractions, and entertainment",
    icon: "🎭",
  },
  {
    value: "shopping",
    label: "Shopping",
    description: "Souvenirs and personal purchases",
    icon: "🛍️",
  },
  { value: "other", label: "Other", description: "Miscellaneous expenses", icon: "📝" },
] as const;

export function EnhancedBudgetForm({
  onSubmit,
  onCancel,
  initialData,
  currencies = DEFAULT_CURRENCIES,
  tripId,
  className,
}: BudgetFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Enhanced form with custom validation and error handling
  const form = useZodForm({
    schema: enhancedBudgetFormSchema,
    defaultValues: {
      name: "",
      totalAmount: 0,
      currency: "USD",
      startDate: "",
      endDate: "",
      categories: [
        { category: "flights" as ExpenseCategory, amount: 0 },
        { category: "accommodations" as ExpenseCategory, amount: 0 },
        { category: "food" as ExpenseCategory, amount: 0 },
      ],
      autoAllocate: false,
      enableAlerts: true,
      alertThreshold: 80,
      notes: "",
      ...initialData,
    },
    validateMode: "onChange",
    reValidateMode: "onChange",
    transformSubmitData: (data) => {
      // Transform data before submission - remove UI-specific fields
      const { autoAllocate, enableAlerts, alertThreshold, notes, ...budgetData } = data;
      return budgetData;
    },
    onValidationError: (errors) => {
      console.warn("Budget form validation failed:", errors);
    },
    onSubmitError: (error) => {
      console.error("Budget form submission failed:", error);
    },
  });

  // Watch form values for dynamic calculations
  const totalAmount = form.watch("totalAmount");
  const categories = form.watch("categories");
  const autoAllocate = form.watch("autoAllocate");
  const currency = form.watch("currency");

  // Calculate allocations
  const totalAllocated = categories.reduce((sum, category) => sum + category.amount, 0);
  const remainingAmount = totalAmount - totalAllocated;
  const allocationPercentage =
    totalAmount > 0 ? (totalAllocated / totalAmount) * 100 : 0;

  // Get currency symbol
  const currencySymbol =
    currencies.find((c) => c.code === currency)?.symbol || currency;

  // Auto-allocate funds when enabled
  const handleAutoAllocate = useCallback(() => {
    if (!autoAllocate || totalAmount <= 0 || categories.length === 0) return;

    const equalAmount = Math.floor(totalAmount / categories.length);
    const remainder = totalAmount % categories.length;

    const newCategories = categories.map((category, index) => ({
      ...category,
      amount: equalAmount + (index < remainder ? 1 : 0),
    }));

    form.setValue("categories", newCategories);
  }, [autoAllocate, totalAmount, categories, form]);

  // Add category
  const addCategory = () => {
    const availableCategories = EXPENSE_CATEGORIES.filter(
      (cat) => !categories.some((existing) => existing.category === cat.value)
    );

    if (availableCategories.length > 0) {
      const newCategory = {
        category: availableCategories[0].value as ExpenseCategory,
        amount: 0,
      };
      form.setValue("categories", [...categories, newCategory]);
    }
  };

  // Remove category
  const removeCategory = (index: number) => {
    const newCategories = categories.filter((_, i) => i !== index);
    form.setValue("categories", newCategories);
  };

  // Handle form submission with enhanced error handling
  const handleSubmit = form.handleSubmitSafe(
    async (data) => {
      setIsSubmitting(true);
      try {
        await onSubmit(data);
      } finally {
        setIsSubmitting(false);
      }
    },
    (validationErrors) => {
      console.error("Form validation failed:", validationErrors);
    }
  );

  // React to auto-allocate changes
  React.useEffect(() => {
    if (autoAllocate) {
      handleAutoAllocate();
    }
  }, [autoAllocate, handleAutoAllocate]);

  return (
    <Card className={cn("w-full max-w-4xl mx-auto", className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Calculator className="h-5 w-5" />
          Create Budget
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <Form {...form}>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Information */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Budget Name</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g., Europe Trip 2024" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="currency"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Currency</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select currency" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {currencies.map((curr) => (
                          <SelectItem key={curr.code} value={curr.code}>
                            {curr.symbol} {curr.name} ({curr.code})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Budget Amount */}
            <FormField
              control={form.control}
              name="totalAmount"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="flex items-center gap-2">
                    <DollarSign className="h-4 w-4" />
                    Total Budget Amount
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground">
                        {currencySymbol}
                      </span>
                      <Input
                        type="number"
                        min="0"
                        step="0.01"
                        placeholder="0.00"
                        className="pl-8"
                        {...field}
                        onChange={(e) =>
                          field.onChange(Number.parseFloat(e.target.value) || 0)
                        }
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Date Range */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="startDate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Start Date</FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="endDate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>End Date</FormLabel>
                    <FormControl>
                      <Input type="date" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            {/* Budget Categories */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">Budget Categories</h3>
                <div className="flex items-center gap-4">
                  <FormField
                    control={form.control}
                    name="autoAllocate"
                    render={({ field }) => (
                      <FormItem className="flex items-center space-x-2 space-y-0">
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                        <FormLabel className="text-sm font-normal">
                          Auto-allocate
                        </FormLabel>
                      </FormItem>
                    )}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={addCategory}
                    disabled={categories.length >= EXPENSE_CATEGORIES.length}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add Category
                  </Button>
                </div>
              </div>

              <div className="space-y-3">
                {categories.map((category, index) => {
                  const categoryInfo = EXPENSE_CATEGORIES.find(
                    (c) => c.value === category.category
                  );
                  const percentage =
                    totalAmount > 0 ? (category.amount / totalAmount) * 100 : 0;

                  return (
                    <div
                      key={index}
                      className="flex items-center gap-4 p-4 border rounded-lg"
                    >
                      <div className="flex-shrink-0">
                        <span className="text-2xl">{categoryInfo?.icon}</span>
                      </div>

                      <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4">
                        <FormField
                          control={form.control}
                          name={`categories.${index}.category`}
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="sr-only">Category</FormLabel>
                              <Select
                                onValueChange={field.onChange}
                                value={field.value}
                              >
                                <FormControl>
                                  <SelectTrigger>
                                    <SelectValue />
                                  </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                  {EXPENSE_CATEGORIES.map((cat) => (
                                    <SelectItem
                                      key={cat.value}
                                      value={cat.value}
                                      disabled={categories.some(
                                        (existing, existingIndex) =>
                                          existing.category === cat.value &&
                                          existingIndex !== index
                                      )}
                                    >
                                      {cat.icon} {cat.label}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              <FormMessage />
                            </FormItem>
                          )}
                        />

                        <FormField
                          control={form.control}
                          name={`categories.${index}.amount`}
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="sr-only">Amount</FormLabel>
                              <FormControl>
                                <div className="relative">
                                  <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground">
                                    {currencySymbol}
                                  </span>
                                  <Input
                                    type="number"
                                    min="0"
                                    step="0.01"
                                    placeholder="0.00"
                                    className="pl-8"
                                    {...field}
                                    onChange={(e) =>
                                      field.onChange(
                                        Number.parseFloat(e.target.value) || 0
                                      )
                                    }
                                    disabled={autoAllocate}
                                  />
                                </div>
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />

                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="text-xs">
                            {percentage.toFixed(1)}%
                          </Badge>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => removeCategory(index)}
                            disabled={categories.length <= 1}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Budget Summary */}
              <div className="p-4 bg-muted/50 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">Budget Allocation</span>
                  <span className="text-sm text-muted-foreground">
                    {allocationPercentage.toFixed(1)}%
                  </span>
                </div>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Total Budget:</span>
                    <span className="font-medium">
                      {currencySymbol}
                      {totalAmount.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Allocated:</span>
                    <span className="font-medium">
                      {currencySymbol}
                      {totalAllocated.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Remaining:</span>
                    <span
                      className={cn(
                        "font-medium",
                        remainingAmount < 0
                          ? "text-destructive"
                          : "text-muted-foreground"
                      )}
                    >
                      {currencySymbol}
                      {remainingAmount.toFixed(2)}
                    </span>
                  </div>
                </div>

                {remainingAmount < 0 && (
                  <Alert className="mt-3">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription className="text-sm">
                      You've allocated more than your total budget. Please adjust your
                      category amounts.
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </div>

            {/* Budget Settings */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">Settings</h3>

              <FormField
                control={form.control}
                name="enableAlerts"
                render={({ field }) => (
                  <FormItem className="flex items-center justify-between space-y-0 rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base font-medium">
                        Budget Alerts
                      </FormLabel>
                      <div className="text-sm text-muted-foreground">
                        Get notified when you approach your budget limits
                      </div>
                    </div>
                    <FormControl>
                      <Switch checked={field.value} onCheckedChange={field.onChange} />
                    </FormControl>
                  </FormItem>
                )}
              />

              {form.watch("enableAlerts") && (
                <FormField
                  control={form.control}
                  name="alertThreshold"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Alert Threshold (%)</FormLabel>
                      <FormControl>
                        <div className="flex items-center gap-4">
                          <Input
                            type="number"
                            min="50"
                            max="95"
                            step="5"
                            {...field}
                            onChange={(e) =>
                              field.onChange(Number.parseInt(e.target.value) || 80)
                            }
                            className="w-20"
                          />
                          <span className="text-sm text-muted-foreground">
                            Alert when {field.value}% of budget is used
                          </span>
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}
            </div>

            {/* Notes */}
            <FormField
              control={form.control}
              name="notes"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Notes (Optional)</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Add any additional notes about this budget..."
                      className="resize-none"
                      rows={3}
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Form Validation Summary */}
            {!form.isFormComplete && (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Please complete all required fields before submitting.
                  {form.validationState.validationErrors.length > 0 && (
                    <ul className="mt-2 list-disc list-inside text-sm">
                      {form.validationState.validationErrors.map((error, index) => (
                        <li key={index}>{error}</li>
                      ))}
                    </ul>
                  )}
                </AlertDescription>
              </Alert>
            )}

            {/* Submit Actions */}
            <Separator />
            <div className="flex gap-4 justify-end">
              {onCancel && (
                <Button type="button" variant="outline" onClick={onCancel}>
                  Cancel
                </Button>
              )}
              <Button
                type="submit"
                disabled={
                  isSubmitting ||
                  form.validationState.isValidating ||
                  !form.isFormComplete
                }
                className="min-w-32"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <TrendingUp className="mr-2 h-4 w-4" />
                    Create Budget
                  </>
                )}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
