/**
 * Comprehensive test suite for the Trip Budget Form with Zod validation
 * Demonstrates testing patterns for complex forms with runtime validation
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  type BudgetFormData,
  type ExpenseCategory,
  budgetFormSchema,
  expenseCategorySchema,
} from "@/lib/schemas/budget";
import { BudgetForm } from "../budget-form";

// Mock the useZodForm hook
const mockUseZodForm = vi.fn();
vi.mock("@/lib/hooks/use-zod-form", () => ({
  useZodForm: mockUseZodForm,
}));

// Mock currency data
const mockCurrencies = [
  { code: "USD", name: "US Dollar", symbol: "$" },
  { code: "EUR", name: "Euro", symbol: "€" },
  { code: "GBP", name: "British Pound", symbol: "£" },
];

// Mock form instance for testing
const createMockForm = (overrides = {}) => ({
  control: {} as any,
  watch: vi.fn().mockImplementation((field: string) => {
    const defaults = {
      totalAmount: 1000,
      categories: [
        { category: "flights" as ExpenseCategory, amount: 400 },
        { category: "accommodations" as ExpenseCategory, amount: 300 },
        { category: "food" as ExpenseCategory, amount: 200 },
      ],
      autoAllocate: false,
      currency: "USD",
    };
    return (defaults as any)[field];
  }),
  setValue: vi.fn(),
  handleSubmitSafe: vi.fn().mockReturnValue(vi.fn()),
  isFormComplete: true,
  validationState: {
    isValidating: false,
    validationErrors: [],
  },
  ...overrides,
});

describe("BudgetForm", () => {
  let mockOnSubmit: ReturnType<typeof vi.fn>;
  let _mockOnCancel: ReturnType<typeof vi.fn>;
  let mockForm: ReturnType<typeof createMockForm>;

  beforeEach(() => {
    mockOnSubmit = vi.fn().mockResolvedValue(undefined);
    _mockOnCancel = vi.fn();
    mockForm = createMockForm();
    mockUseZodForm.mockReturnValue(mockForm);
    vi.clearAllMocks();
  });

  describe("Zod Schema Validation", () => {
    it("validates budget form data with complete schema", () => {
      const validBudgetData: BudgetFormData = {
        name: "Europe Trip 2024",
        totalAmount: 5000,
        currency: "USD",
        startDate: "2024-06-01",
        endDate: "2024-06-15",
        categories: [
          { category: "flights", amount: 2000 },
          { category: "accommodations", amount: 1500 },
          { category: "food", amount: 1000 },
          { category: "activities", amount: 500 },
        ],
      };

      // Should pass validation
      expect(() => budgetFormSchema.parse(validBudgetData)).not.toThrow();

      const validatedData = budgetFormSchema.parse(validBudgetData);
      expect(validatedData.name).toBe("Europe Trip 2024");
      expect(validatedData.totalAmount).toBe(5000);
      expect(validatedData.categories).toHaveLength(4);
    });

    it("rejects invalid budget form data", () => {
      const invalidBudgetData = {
        name: "", // Empty name should fail
        totalAmount: -100, // Negative amount should fail
        currency: "INVALID", // Invalid currency code
        startDate: "invalid-date",
        endDate: "2024-06-01", // End date before start date
        categories: [], // Empty categories should fail
      };

      expect(() => budgetFormSchema.parse(invalidBudgetData)).toThrow();
    });

    it("validates expense categories", () => {
      const validCategories: ExpenseCategory[] = [
        "flights",
        "accommodations",
        "transportation",
        "food",
        "activities",
        "shopping",
        "other",
      ];

      validCategories.forEach((category) => {
        expect(() => expenseCategorySchema.parse(category)).not.toThrow();
      });

      expect(() => expenseCategorySchema.parse("invalid_category")).toThrow();
    });

    it("validates cross-field dependencies", () => {
      const budgetWithInvalidDates = {
        name: "Test Budget",
        totalAmount: 1000,
        currency: "USD",
        startDate: "2024-06-15",
        endDate: "2024-06-01", // End date before start date
        categories: [{ category: "flights", amount: 500 }],
      };

      expect(() => budgetFormSchema.parse(budgetWithInvalidDates)).toThrow();
    });
  });

  describe("Component Rendering", () => {
    it("renders budget form with all required fields", () => {
      render(
        <BudgetForm onSubmit={mockOnSubmit} currencies={mockCurrencies} />
      );

      expect(screen.getByLabelText(/budget name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/currency/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/total budget amount/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
    });

    it("displays budget allocation summary", () => {
      render(
        <BudgetForm onSubmit={mockOnSubmit} currencies={mockCurrencies} />
      );

      expect(screen.getByText(/budget allocation/i)).toBeInTheDocument();
      expect(screen.getByText(/total budget/i)).toBeInTheDocument();
      expect(screen.getByText(/allocated/i)).toBeInTheDocument();
      expect(screen.getByText(/remaining/i)).toBeInTheDocument();
    });

    it("shows validation errors when form is incomplete", () => {
      const incompleteForm = createMockForm({
        isFormComplete: false,
        validationState: {
          isValidating: false,
          validationErrors: [
            "Budget name is required",
            "Total amount must be positive",
          ],
        },
      });
      mockUseZodForm.mockReturnValue(incompleteForm);

      render(
        <BudgetForm onSubmit={mockOnSubmit} currencies={mockCurrencies} />
      );

      expect(
        screen.getByText(/please complete all required fields/i)
      ).toBeInTheDocument();
      expect(screen.getByText("Budget name is required")).toBeInTheDocument();
      expect(screen.getByText("Total amount must be positive")).toBeInTheDocument();
    });
  });

  describe("Form Interactions", () => {
    it("handles auto-allocation toggle", async () => {
      const user = userEvent.setup();

      render(
        <BudgetForm onSubmit={mockOnSubmit} currencies={mockCurrencies} />
      );

      const autoAllocateSwitch = screen.getByRole("switch", { name: /auto-allocate/i });
      await user.click(autoAllocateSwitch);

      expect(mockForm.setValue).toHaveBeenCalled();
    });

    it("adds new expense category", async () => {
      const user = userEvent.setup();

      render(
        <BudgetForm onSubmit={mockOnSubmit} currencies={mockCurrencies} />
      );

      const addButton = screen.getByRole("button", { name: /add category/i });
      await user.click(addButton);

      expect(mockForm.setValue).toHaveBeenCalledWith(
        "categories",
        expect.arrayContaining([
          expect.objectContaining({ category: expect.any(String), amount: 0 }),
        ])
      );
    });

    it("validates budget allocation doesn't exceed total", () => {
      const overAllocatedForm = createMockForm({
        watch: vi.fn().mockImplementation((field: string) => {
          const data = {
            totalAmount: 1000,
            categories: [
              { category: "flights", amount: 600 },
              { category: "accommodations", amount: 500 }, // Total: 1100 > 1000
            ],
            currency: "USD",
          };
          return (data as any)[field];
        }),
      });
      mockUseZodForm.mockReturnValue(overAllocatedForm);

      render(
        <BudgetForm onSubmit={mockOnSubmit} currencies={mockCurrencies} />
      );

      expect(
        screen.getByText(/you've allocated more than your total budget/i)
      ).toBeInTheDocument();
    });
  });

  describe("Form Submission", () => {
    it("submits valid form data", async () => {
      const user = userEvent.setup();
      const handleSubmit = vi.fn();
      mockForm.handleSubmitSafe.mockReturnValue(handleSubmit);

      render(
        <BudgetForm onSubmit={mockOnSubmit} currencies={mockCurrencies} />
      );

      const submitButton = screen.getByRole("button", { name: /create budget/i });
      await user.click(submitButton);

      expect(handleSubmit).toHaveBeenCalled();
    });

    it("transforms form data before submission", async () => {
      const transformedData = { name: "Test", totalAmount: 1000, currency: "USD" };
      const formWithTransform = createMockForm({
        handleSubmitSafe: vi.fn().mockImplementation((onSubmit, _onError) => {
          return vi.fn().mockImplementation(() => {
            // Simulate data transformation
            onSubmit(transformedData);
          });
        }),
      });
      mockUseZodForm.mockReturnValue(formWithTransform);

      const user = userEvent.setup();
      render(
        <BudgetForm onSubmit={mockOnSubmit} currencies={mockCurrencies} />
      );

      const submitButton = screen.getByRole("button", { name: /create budget/i });
      await user.click(submitButton);

      await waitFor(() => {
        expect(mockOnSubmit).toHaveBeenCalledWith(transformedData);
      });
    });

    it("handles submission errors gracefully", async () => {
      const submissionError = new Error("API Error");
      mockOnSubmit.mockRejectedValue(submissionError);

      const errorHandlingForm = createMockForm({
        handleSubmitSafe: vi.fn().mockImplementation((onSubmit, onError) => {
          return vi.fn().mockImplementation(() => {
            onSubmit({}).catch(onError);
          });
        }),
      });
      mockUseZodForm.mockReturnValue(errorHandlingForm);

      const user = userEvent.setup();
      render(
        <BudgetForm onSubmit={mockOnSubmit} currencies={mockCurrencies} />
      );

      const submitButton = screen.getByRole("button", { name: /create budget/i });
      await user.click(submitButton);

      // Should handle error without crashing
      expect(mockOnSubmit).toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("provides proper form labels", () => {
      render(
        <BudgetForm onSubmit={mockOnSubmit} currencies={mockCurrencies} />
      );

      // Check that all form fields have accessible labels
      expect(screen.getByLabelText(/budget name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/currency/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/total budget amount/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/start date/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/end date/i)).toBeInTheDocument();
    });

    it("announces validation errors to screen readers", () => {
      const errorForm = createMockForm({
        isFormComplete: false,
        validationState: {
          isValidating: false,
          validationErrors: ["Required field missing"],
        },
      });
      mockUseZodForm.mockReturnValue(errorForm);

      render(
        <BudgetForm onSubmit={mockOnSubmit} currencies={mockCurrencies} />
      );

      // Error alert should be accessible
      const errorAlert = screen.getByRole("alert");
      expect(errorAlert).toBeInTheDocument();
      expect(errorAlert).toHaveTextContent("Required field missing");
    });
  });

  describe("Currency Handling", () => {
    it("displays correct currency symbols", () => {
      render(
        <BudgetForm onSubmit={mockOnSubmit} currencies={mockCurrencies} />
      );

      // Should display USD symbol by default
      expect(screen.getAllByText("$")).toHaveLength(2); // Total amount + categories
    });

    it("updates currency symbol when currency changes", () => {
      const eurForm = createMockForm({
        watch: vi.fn().mockImplementation((field: string) => {
          if (field === "currency") return "EUR";
          return mockForm.watch(field);
        }),
      });
      mockUseZodForm.mockReturnValue(eurForm);

      render(
        <BudgetForm onSubmit={mockOnSubmit} currencies={mockCurrencies} />
      );

      expect(screen.getAllByText("€")).toHaveLength(2);
    });
  });

  describe("Real-time Calculations", () => {
    it("calculates remaining budget correctly", () => {
      const calculationForm = createMockForm({
        watch: vi.fn().mockImplementation((field: string) => {
          const data = {
            totalAmount: 1000,
            categories: [
              { category: "flights", amount: 400 },
              { category: "accommodations", amount: 300 },
            ],
            currency: "USD",
          };
          return (data as any)[field];
        }),
      });
      mockUseZodForm.mockReturnValue(calculationForm);

      render(
        <BudgetForm onSubmit={mockOnSubmit} currencies={mockCurrencies} />
      );

      // Remaining should be 1000 - 400 - 300 = 300
      expect(screen.getByText("$300.00")).toBeInTheDocument();
    });

    it("shows allocation percentage", () => {
      render(
        <BudgetForm onSubmit={mockOnSubmit} currencies={mockCurrencies} />
      );

      // Should show percentage allocation
      expect(screen.getByText(/90\.0%/)).toBeInTheDocument(); // 900/1000 = 90%
    });
  });
});
