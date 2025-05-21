/**
 * Types for Budget management
 */

export type CurrencyCode = string; // ISO 4217 currency code (e.g., "USD", "EUR")
export type ExpenseCategory = 
  | "flights" 
  | "accommodations" 
  | "transportation" 
  | "food" 
  | "activities" 
  | "shopping" 
  | "other";

export interface Budget {
  id: string;
  tripId?: string; // Associated trip ID (if any)
  name: string;
  totalAmount: number;
  currency: CurrencyCode;
  startDate?: string; // ISO date string
  endDate?: string; // ISO date string
  categories: BudgetCategory[];
  isActive: boolean;
  createdAt: string; // ISO date-time string
  updatedAt: string; // ISO date-time string
}

export interface BudgetCategory {
  id: string;
  category: ExpenseCategory;
  amount: number; // Allocated amount
  spent: number; // Amount spent so far
  remaining: number; // amount - spent
  percentage: number; // (spent / amount) * 100
}

export interface Expense {
  id: string;
  budgetId: string;
  tripId?: string;
  category: ExpenseCategory;
  description: string;
  amount: number;
  currency: CurrencyCode;
  date: string; // ISO date string
  location?: string;
  paymentMethod?: string;
  attachmentUrl?: string; // URL to receipt or other attachment
  isShared: boolean; // Expense is shared with travel companions
  shareDetails?: ShareDetails[];
  createdAt: string; // ISO date-time string
  updatedAt: string; // ISO date-time string
}

export interface ShareDetails {
  userId: string;
  userName: string;
  percentage: number; // Share percentage (0-100)
  amount: number; // Calculated amount based on percentage
  isPaid: boolean;
}

export interface CurrencyRate {
  code: CurrencyCode;
  rate: number; // Exchange rate relative to base currency
  lastUpdated: string; // ISO date-time string
}

export interface BudgetSummary {
  totalBudget: number;
  totalSpent: number;
  totalRemaining: number;
  percentageSpent: number; // (totalSpent / totalBudget) * 100
  spentByCategory: Record<ExpenseCategory, number>;
  dailyAverage: number;
  dailyLimit: number;
  projectedTotal: number; // Based on current spending rate
  isOverBudget: boolean;
  daysRemaining?: number;
}

export interface BudgetAlert {
  id: string;
  budgetId: string;
  type: "threshold" | "category" | "daily";
  threshold: number; // Percentage threshold for alerts
  message: string;
  isRead: boolean;
  createdAt: string; // ISO date-time string
}

// API Request/Response types

export interface CreateBudgetRequest {
  name: string;
  totalAmount: number;
  currency: CurrencyCode;
  tripId?: string;
  startDate?: string;
  endDate?: string;
  categories?: Partial<BudgetCategory>[];
}

export interface UpdateBudgetRequest {
  id: string;
  name?: string;
  totalAmount?: number;
  currency?: CurrencyCode;
  startDate?: string;
  endDate?: string;
  categories?: Partial<BudgetCategory>[];
  isActive?: boolean;
}

export interface AddExpenseRequest {
  budgetId: string;
  tripId?: string;
  category: ExpenseCategory;
  description: string;
  amount: number;
  currency: CurrencyCode;
  date: string;
  location?: string;
  paymentMethod?: string;
  attachmentUrl?: string;
  isShared: boolean;
  shareDetails?: Partial<ShareDetails>[];
}

export interface UpdateExpenseRequest {
  id: string;
  budgetId?: string;
  category?: ExpenseCategory;
  description?: string;
  amount?: number;
  currency?: CurrencyCode;
  date?: string;
  location?: string;
  paymentMethod?: string;
  attachmentUrl?: string;
  isShared?: boolean;
  shareDetails?: Partial<ShareDetails>[];
}

export interface CreateBudgetAlertRequest {
  budgetId: string;
  type: "threshold" | "category" | "daily";
  threshold: number;
  message?: string;
}