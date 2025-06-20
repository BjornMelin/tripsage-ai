/**
 * Comprehensive test suite for useZodForm hook
 * Demonstrates advanced Zod validation patterns for forms
 */

import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";

import { useZodForm } from "../use-zod-form";

// Mock react-hook-form
const mockUseForm = vi.fn();
const mockRegister = vi.fn();
const mockHandleSubmit = vi.fn();
const mockWatch = vi.fn();
const mockSetValue = vi.fn();
const mockTrigger = vi.fn();
const mockClearErrors = vi.fn();
const mockSetError = vi.fn();
const mockGetValues = vi.fn();

vi.mock("react-hook-form", () => ({
  useForm: mockUseForm,
}));

vi.mock("@hookform/resolvers/zod", () => ({
  zodResolver: vi.fn((schema) => ({ schema })),
}));

// Test schemas for validation
const SimpleFormSchema = z.object({
  email: z.string().email("Invalid email format"),
  password: z.string().min(8, "Password must be at least 8 characters"),
  name: z.string().min(1, "Name is required"),
});

const ComplexFormSchema = z.object({
  personalInfo: z.object({
    firstName: z.string().min(1, "First name is required"),
    lastName: z.string().min(1, "Last name is required"),
    email: z.string().email("Invalid email format"),
    phone: z.string().regex(/^\+?[1-9]\d{1,14}$/, "Invalid phone number"),
  }),
  preferences: z.object({
    theme: z.enum(["light", "dark"], { required_error: "Theme is required" }),
    notifications: z.boolean(),
    language: z.string().default("en"),
  }),
  address: z.object({
    street: z.string().min(1, "Street is required"),
    city: z.string().min(1, "City is required"),
    country: z.string().min(2, "Country code required"),
    zipCode: z.string().regex(/^\d{5}(-\d{4})?$/, "Invalid ZIP code"),
  }),
});

const AsyncValidationSchema = z.object({
  username: z.string()
    .min(3, "Username must be at least 3 characters")
    .refine(
      async (username) => {
        // Simulate async validation (checking if username exists)
        await new Promise(resolve => setTimeout(resolve, 100));
        return username !== "taken_username";
      },
      { message: "Username is already taken" }
    ),
  email: z.string().email(),
});

type SimpleFormData = z.infer<typeof SimpleFormSchema>;
type ComplexFormData = z.infer<typeof ComplexFormSchema>;
type AsyncFormData = z.infer<typeof AsyncValidationSchema>;

describe("useZodForm Hook", () => {
  let mockFormInstance: any;

  beforeEach(() => {
    mockFormInstance = {
      register: mockRegister,
      handleSubmit: mockHandleSubmit,
      watch: mockWatch,
      setValue: mockSetValue,
      trigger: mockTrigger,
      clearErrors: mockClearErrors,
      setError: mockSetError,
      getValues: mockGetValues,
      formState: {
        errors: {},
        isSubmitting: false,
        isValidating: false,
        isValid: true,
        isDirty: false,
        isSubmitted: false,
        touchedFields: {},
        dirtyFields: {},
      },
      control: {},
      reset: vi.fn(),
    };

    mockUseForm.mockReturnValue(mockFormInstance);
    vi.clearAllMocks();
  });

  describe("Basic Form Functionality", () => {
    it("initializes form with Zod schema and default values", () => {
      const defaultValues: Partial<SimpleFormData> = {
        email: "test@example.com",
        name: "John Doe",
      };

      const { result } = renderHook(() =>
        useZodForm({
          schema: SimpleFormSchema,
          defaultValues,
        })
      );

      expect(mockUseForm).toHaveBeenCalledWith(
        expect.objectContaining({
          resolver: expect.objectContaining({ schema: SimpleFormSchema }),
          defaultValues,
          mode: "onChange",
        })
      );

      expect(result.current.register).toBe(mockRegister);
      expect(result.current.control).toBe(mockFormInstance.control);
    });

    it("provides enhanced form state with validation status", () => {
      mockFormInstance.formState = {
        ...mockFormInstance.formState,
        errors: {
          email: { message: "Invalid email" },
        },
        isValidating: true,
      };

      const { result } = renderHook(() =>
        useZodForm({
          schema: SimpleFormSchema,
        })
      );

      expect(result.current.validationState.isValidating).toBe(true);
      expect(result.current.validationState.validationErrors).toContain("Invalid email");
      expect(result.current.isFormComplete).toBe(false);
    });

    it("handles form submission with data transformation", async () => {
      const onSubmit = vi.fn().mockResolvedValue(undefined);
      const transformSubmitData = vi.fn((data) => ({ ...data, transformed: true }));

      mockHandleSubmit.mockImplementation((fn) => (e) => {
        fn({ email: "test@example.com", password: "password123", name: "John" });
      });

      const { result } = renderHook(() =>
        useZodForm({
          schema: SimpleFormSchema,
          transformSubmitData,
        })
      );

      const handleSubmit = result.current.handleSubmitSafe(onSubmit);
      
      await act(async () => {
        await handleSubmit({} as any);
      });

      expect(transformSubmitData).toHaveBeenCalledWith({
        email: "test@example.com",
        password: "password123",
        name: "John",
      });

      expect(onSubmit).toHaveBeenCalledWith({
        email: "test@example.com",
        password: "password123",
        name: "John",
        transformed: true,
      });
    });
  });

  describe("Validation Patterns", () => {
    it("validates simple form data with Zod schema", () => {
      const validData: SimpleFormData = {
        email: "test@example.com",
        password: "securepassword123",
        name: "John Doe",
      };

      expect(() => SimpleFormSchema.parse(validData)).not.toThrow();

      const invalidData = {
        email: "invalid-email",
        password: "short",
        name: "",
      };

      expect(() => SimpleFormSchema.parse(invalidData)).toThrow();
    });

    it("validates complex nested form data", () => {
      const validComplexData: ComplexFormData = {
        personalInfo: {
          firstName: "John",
          lastName: "Doe",
          email: "john@example.com",
          phone: "+1234567890",
        },
        preferences: {
          theme: "dark",
          notifications: true,
          language: "en",
        },
        address: {
          street: "123 Main St",
          city: "New York",
          country: "US",
          zipCode: "12345",
        },
      };

      expect(() => ComplexFormSchema.parse(validComplexData)).not.toThrow();

      const invalidComplexData = {
        personalInfo: {
          firstName: "",
          lastName: "",
          email: "invalid",
          phone: "invalid",
        },
        preferences: {
          theme: "invalid" as any,
          notifications: "yes" as any,
        },
        address: {
          street: "",
          city: "",
          country: "X",
          zipCode: "invalid",
        },
      };

      expect(() => ComplexFormSchema.parse(invalidComplexData)).toThrow();
    });

    it("provides detailed validation error messages", () => {
      const { result } = renderHook(() =>
        useZodForm({
          schema: SimpleFormSchema,
        })
      );

      // Mock validation errors
      mockFormInstance.formState = {
        ...mockFormInstance.formState,
        errors: {
          email: { message: "Invalid email format" },
          password: { message: "Password must be at least 8 characters" },
          name: { message: "Name is required" },
        },
      };

      const validationErrors = result.current.validationState.validationErrors;
      expect(validationErrors).toContain("Invalid email format");
      expect(validationErrors).toContain("Password must be at least 8 characters");
      expect(validationErrors).toContain("Name is required");
    });
  });

  describe("Async Validation", () => {
    it("handles async validation with loading states", async () => {
      mockFormInstance.formState = {
        ...mockFormInstance.formState,
        isValidating: true,
      };

      const { result } = renderHook(() =>
        useZodForm({
          schema: AsyncValidationSchema,
          validateMode: "onChange",
        })
      );

      expect(result.current.validationState.isValidating).toBe(true);

      // Simulate completion of async validation
      await act(async () => {
        mockFormInstance.formState.isValidating = false;
      });

      expect(result.current.validationState.isValidating).toBe(false);
    });

    it("validates async constraints", async () => {
      const validAsyncData = {
        username: "available_username",
        email: "test@example.com",
      };

      const invalidAsyncData = {
        username: "taken_username",
        email: "test@example.com",
      };

      // Valid data should pass
      await expect(AsyncValidationSchema.parseAsync(validAsyncData)).resolves.toEqual(validAsyncData);

      // Invalid data should fail
      await expect(AsyncValidationSchema.parseAsync(invalidAsyncData)).rejects.toThrow("Username is already taken");
    });
  });

  describe("Form Reset and State Management", () => {
    it("resets form to default values", () => {
      const defaultValues: Partial<SimpleFormData> = {
        email: "default@example.com",
        name: "Default Name",
      };

      const { result } = renderHook(() =>
        useZodForm({
          schema: SimpleFormSchema,
          defaultValues,
        })
      );

      act(() => {
        result.current.reset();
      });

      expect(mockFormInstance.reset).toHaveBeenCalledWith(defaultValues);
    });

    it("tracks form completion status", () => {
      // Form with no errors should be complete
      mockFormInstance.formState = {
        ...mockFormInstance.formState,
        errors: {},
        isValid: true,
      };

      const { result } = renderHook(() =>
        useZodForm({
          schema: SimpleFormSchema,
        })
      );

      expect(result.current.isFormComplete).toBe(true);

      // Form with errors should not be complete
      act(() => {
        mockFormInstance.formState = {
          ...mockFormInstance.formState,
          errors: { email: { message: "Invalid email" } },
          isValid: false,
        };
      });

      expect(result.current.isFormComplete).toBe(false);
    });
  });

  describe("Error Handling", () => {
    it("handles submission errors gracefully", async () => {
      const onSubmit = vi.fn().mockRejectedValue(new Error("Submission failed"));
      const onSubmitError = vi.fn();

      mockHandleSubmit.mockImplementation((fn) => (e) => {
        fn({ email: "test@example.com", password: "password123", name: "John" });
      });

      const { result } = renderHook(() =>
        useZodForm({
          schema: SimpleFormSchema,
          onSubmitError,
        })
      );

      const handleSubmit = result.current.handleSubmitSafe(onSubmit);
      
      await act(async () => {
        await handleSubmit({} as any);
      });

      expect(onSubmitError).toHaveBeenCalledWith(expect.any(Error));
    });

    it("handles validation errors during submission", async () => {
      const onSubmit = vi.fn();
      const onValidationError = vi.fn();

      // Mock validation failure
      mockHandleSubmit.mockImplementation((successFn, errorFn) => (e) => {
        errorFn({
          email: { message: "Invalid email" },
          password: { message: "Password too short" },
        });
      });

      const { result } = renderHook(() =>
        useZodForm({
          schema: SimpleFormSchema,
          onValidationError,
        })
      );

      const handleSubmit = result.current.handleSubmitSafe(onSubmit);
      
      await act(async () => {
        await handleSubmit({} as any);
      });

      expect(onValidationError).toHaveBeenCalledWith({
        email: { message: "Invalid email" },
        password: { message: "Password too short" },
      });
      expect(onSubmit).not.toHaveBeenCalled();
    });
  });

  describe("Form Wizard Functionality", () => {
    it("manages multi-step form state", () => {
      const steps = ["personal", "preferences", "address"];

      const { result } = renderHook(() =>
        useZodForm({
          schema: ComplexFormSchema,
          enableWizard: true,
          wizardSteps: steps,
        })
      );

      expect(result.current.wizardState.currentStep).toBe(0);
      expect(result.current.wizardState.totalSteps).toBe(3);
      expect(result.current.wizardState.isFirstStep).toBe(true);
      expect(result.current.wizardState.isLastStep).toBe(false);
    });

    it("navigates between wizard steps", () => {
      const steps = ["step1", "step2", "step3"];

      const { result } = renderHook(() =>
        useZodForm({
          schema: ComplexFormSchema,
          enableWizard: true,
          wizardSteps: steps,
        })
      );

      // Go to next step
      act(() => {
        result.current.wizardActions.goToNext();
      });

      expect(result.current.wizardState.currentStep).toBe(1);
      expect(result.current.wizardState.isFirstStep).toBe(false);
      expect(result.current.wizardState.isLastStep).toBe(false);

      // Go to previous step
      act(() => {
        result.current.wizardActions.goToPrevious();
      });

      expect(result.current.wizardState.currentStep).toBe(0);
    });

    it("validates current step before proceeding", async () => {
      const stepSchemas = [
        z.object({ step1Field: z.string().min(1) }),
        z.object({ step2Field: z.string().min(1) }),
        z.object({ step3Field: z.string().min(1) }),
      ];

      const { result } = renderHook(() =>
        useZodForm({
          schema: ComplexFormSchema,
          enableWizard: true,
          wizardSteps: ["step1", "step2", "step3"],
          stepValidationSchemas: stepSchemas,
        })
      );

      // Mock trigger validation to fail
      mockTrigger.mockResolvedValue(false);

      await act(async () => {
        const canProceed = await result.current.wizardActions.validateAndGoToNext();
        expect(canProceed).toBe(false);
      });

      expect(mockTrigger).toHaveBeenCalled();
      expect(result.current.wizardState.currentStep).toBe(0); // Should not advance
    });
  });

  describe("Performance Optimizations", () => {
    it("debounces validation for performance", async () => {
      const { result } = renderHook(() =>
        useZodForm({
          schema: SimpleFormSchema,
          validateMode: "onChange",
          debounceValidation: 300,
        })
      );

      // Trigger multiple rapid validations
      act(() => {
        result.current.trigger("email");
        result.current.trigger("email");
        result.current.trigger("email");
      });

      // Should only call trigger once after debounce
      await waitFor(() => {
        expect(mockTrigger).toHaveBeenCalledTimes(1);
      }, { timeout: 500 });
    });

    it("memoizes validation results", () => {
      const memoizedSchema = SimpleFormSchema;

      const { result, rerender } = renderHook(
        ({ schema }) => useZodForm({ schema }),
        { initialProps: { schema: memoizedSchema } }
      );

      const firstRender = result.current;

      // Rerender with same schema
      rerender({ schema: memoizedSchema });

      const secondRender = result.current;

      // Should maintain reference equality for performance
      expect(firstRender.validationState).toBe(secondRender.validationState);
    });
  });
});