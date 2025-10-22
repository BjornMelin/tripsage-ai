/**
 * React Hook Form integration with Zod validation
 * Provides type-safe form handling with error management
 */

import { zodResolver } from "@hookform/resolvers/zod";
import { useCallback, useMemo, useState } from "react";
import {
  type DefaultValues,
  type FieldPath,
  type FieldValues,
  type UseFormProps,
  type UseFormReturn,
  useForm,
} from "react-hook-form";
import type { z } from "zod";
import {
  TripSageValidationError,
  ValidationContext,
  type ValidationResult,
  validate,
} from "../validation";

// Form options
interface UseZodFormOptions<T extends FieldValues> extends UseFormProps<T> {
  schema: z.ZodSchema<T>;
  validateMode?: "onSubmit" | "onBlur" | "onChange" | "onTouched" | "all";
  reValidateMode?: "onSubmit" | "onBlur" | "onChange";
  enableAsyncValidation?: boolean;
  debounceValidation?: number;
  transformSubmitData?: (data: T) => T | Promise<T>;
  onValidationError?: (errors: ValidationResult<T>) => void;
  onSubmitSuccess?: (data: T) => void | Promise<void>;
  onSubmitError?: (error: Error) => void;

  // Wizard options
  enableWizard?: boolean;
  wizardSteps?: string[];
  stepValidationSchemas?: z.ZodType<any>[];
}

// form return type
interface UseZodFormReturn<T extends FieldValues> extends UseFormReturn<T> {
  // validation methods
  validateField: (
    fieldName: FieldPath<T>,
    value: unknown
  ) => Promise<ValidationResult<unknown>>;
  validateAllFields: () => Promise<ValidationResult<T>>;

  // Safe submit with validation
  handleSubmitSafe: (
    onValid: (data: T) => void | Promise<void>,
    onInvalid?: (errors: ValidationResult<T>) => void
  ) => (e?: React.BaseSyntheticEvent) => Promise<void>;

  // Form state helpers
  isFieldValid: (fieldName: FieldPath<T>) => boolean;
  getFieldError: (fieldName: FieldPath<T>) => string | undefined;
  hasAnyErrors: boolean;
  isFormComplete: boolean;

  // Data transformation helpers
  getCleanData: () => T;
  resetToDefaults: () => void;

  // Validation state
  validationState: {
    isValidating: boolean;
    lastValidation: Date | null;
    validationErrors: string[];
  };

  // Wizard state (for multi-step forms)
  wizardState?: {
    currentStep: number;
    totalSteps: number;
    isFirstStep: boolean;
    isLastStep: boolean;
  };

  // Wizard actions
  wizardActions?: {
    goToNext: () => void;
    goToPrevious: () => void;
    goToStep: (step: number) => void;
    validateAndGoToNext: () => Promise<boolean>;
  };
}

// Custom hook for enhanced Zod form handling
export function useZodForm<T extends FieldValues>(
  options: UseZodFormOptions<T>
): UseZodFormReturn<T> {
  const {
    schema,
    transformSubmitData,
    onValidationError,
    onSubmitSuccess,
    onSubmitError,
    enableAsyncValidation = false,
    ...formOptions
  } = options;

  // Initialize React Hook Form with Zod resolver
  const form = useForm<T>({
    resolver: zodResolver(schema),
    mode: options.validateMode || "onChange",
    reValidateMode: options.reValidateMode || "onChange",
    ...formOptions,
  });

  // Validation state management
  const [validationState, setValidationState] = useState({
    isValidating: false,
    lastValidation: null as Date | null,
    validationErrors: [] as string[],
  });

  // Wizard state management
  const [currentStep, setCurrentStep] = useState(0);
  const wizardSteps = options.wizardSteps || [];
  const enableWizard = options.enableWizard || false;

  // Validate individual field
  const validateField = useCallback(
    async (
      fieldName: FieldPath<T>,
      value: unknown
    ): Promise<ValidationResult<unknown>> => {
      try {
        // In Zod v4, we can't access .shape directly. Instead, validate the whole object
        // and extract field-specific errors if validation fails
        const testData = { [fieldName]: value } as Partial<T>;

        // Create a partial schema for validation - handle both object and other schema types
        let partialSchema: z.ZodType<any>;
        if ("partial" in schema && typeof schema.partial === "function") {
          partialSchema = (schema as any).partial();
        } else {
          // For non-object schemas, use the schema as-is for field validation
          partialSchema = schema;
        }

        const result = validate(partialSchema, testData, ValidationContext.FORM);

        if (result.success) {
          return { success: true, data: value };
        }

        // Find field-specific errors
        const fieldErrors =
          result.errors?.filter((err) => err.field === fieldName) || [];
        if (fieldErrors.length === 0) {
          return { success: true, data: value };
        }

        return {
          success: false,
          errors: fieldErrors,
        };
      } catch (error) {
        return {
          success: false,
          errors: [
            {
              context: ValidationContext.FORM,
              field: fieldName as string,
              message: error instanceof Error ? error.message : "Validation failed",
              code: "FIELD_VALIDATION_ERROR",
              timestamp: new Date(),
            },
          ],
        };
      }
    },
    [schema]
  );

  // Validate all fields
  const validateAllFields = useCallback(async (): Promise<ValidationResult<T>> => {
    setValidationState((prev) => ({ ...prev, isValidating: true }));

    try {
      const formData = form.getValues();
      const result = validate(schema, formData, ValidationContext.FORM);

      setValidationState((prev) => ({
        ...prev,
        isValidating: false,
        lastValidation: new Date(),
        validationErrors: result.success
          ? []
          : result.errors?.map((e) => e.message) || [],
      }));

      if (!result.success && onValidationError) {
        onValidationError(result);
      }

      return result;
    } catch (error) {
      const validationResult = {
        success: false as const,
        errors: [
          {
            context: ValidationContext.FORM,
            message: error instanceof Error ? error.message : "Validation failed",
            code: "FORM_VALIDATION_ERROR",
            timestamp: new Date(),
          },
        ],
      };

      setValidationState((prev) => ({
        ...prev,
        isValidating: false,
        lastValidation: new Date(),
        validationErrors: [validationResult.errors[0].message],
      }));

      if (onValidationError) {
        onValidationError(validationResult);
      }

      return validationResult;
    }
  }, [form, schema, onValidationError]);

  // Safe submit handler with enhanced error handling
  const handleSubmitSafe = useCallback(
    (
      onValid: (data: T) => void | Promise<void>,
      onInvalid?: (errors: ValidationResult<T>) => void
    ) =>
      async (e?: React.BaseSyntheticEvent) => {
        e?.preventDefault();

        try {
          // First, validate the entire form
          const validationResult = await validateAllFields();

          if (!validationResult.success) {
            if (onInvalid) {
              onInvalid(validationResult);
            }
            return;
          }

          // Transform data if transformer provided
          let submitData = validationResult.data!;
          if (transformSubmitData) {
            submitData = await transformSubmitData(submitData);
          }

          // Call the success handler
          await onValid(submitData);

          if (onSubmitSuccess) {
            await onSubmitSuccess(submitData);
          }
        } catch (error) {
          const submitError =
            error instanceof Error ? error : new Error("Submit failed");

          if (onSubmitError) {
            onSubmitError(submitError);
          } else {
            console.error("Form submission error:", submitError);
          }

          // Set form errors if it's a validation error
          if (error instanceof TripSageValidationError) {
            const formErrors = error.getFieldErrors();
            Object.entries(formErrors).forEach(([field, message]) => {
              form.setError(field as FieldPath<T>, { type: "manual", message });
            });
          }
        }
      },
    [validateAllFields, transformSubmitData, onSubmitSuccess, onSubmitError, form]
  );

  // Helper methods
  const isFieldValid = useCallback(
    (fieldName: FieldPath<T>): boolean => {
      const fieldState = form.getFieldState(fieldName);
      return !fieldState.error;
    },
    [form]
  );

  const getFieldError = useCallback(
    (fieldName: FieldPath<T>): string | undefined => {
      const fieldState = form.getFieldState(fieldName);
      return fieldState.error?.message;
    },
    [form]
  );

  const hasAnyErrors = useMemo(() => {
    return Object.keys(form.formState.errors).length > 0;
  }, [form.formState.errors]);

  const isFormComplete = useMemo(() => {
    const values = form.getValues();
    const result = schema.safeParse(values);
    return result.success;
  }, [form, schema]);

  const getCleanData = useCallback((): T => {
    const data = form.getValues();
    const result = schema.parse(data);
    return result;
  }, [form, schema]);

  const resetToDefaults = useCallback(() => {
    // React Hook Form v7+ expects DefaultValues<T> or undefined
    if (options.defaultValues) {
      form.reset(options.defaultValues as DefaultValues<T>);
    } else {
      form.reset();
    }
    setValidationState({
      isValidating: false,
      lastValidation: null,
      validationErrors: [],
    });
  }, [form, options.defaultValues]);

  // Wizard actions
  const wizardActions = useMemo(() => {
    if (!enableWizard) return undefined;

    return {
      goToNext: () => {
        if (currentStep < wizardSteps.length - 1) {
          setCurrentStep(currentStep + 1);
        }
      },
      goToPrevious: () => {
        if (currentStep > 0) {
          setCurrentStep(currentStep - 1);
        }
      },
      goToStep: (step: number) => {
        if (step >= 0 && step < wizardSteps.length) {
          setCurrentStep(step);
        }
      },
      validateAndGoToNext: async () => {
        const isValid = await form.trigger();
        if (isValid && currentStep < wizardSteps.length - 1) {
          setCurrentStep(currentStep + 1);
          return true;
        }
        return isValid;
      },
    };
  }, [enableWizard, currentStep, wizardSteps.length, form]);

  // Wizard state
  const wizardState = useMemo(() => {
    if (!enableWizard) return undefined;

    return {
      currentStep,
      totalSteps: wizardSteps.length,
      isFirstStep: currentStep === 0,
      isLastStep: currentStep === wizardSteps.length - 1,
    };
  }, [enableWizard, currentStep, wizardSteps.length]);

  return {
    ...form,
    validateField,
    validateAllFields,
    handleSubmitSafe,
    isFieldValid,
    getFieldError,
    hasAnyErrors,
    isFormComplete,
    getCleanData,
    resetToDefaults,
    validationState,
    wizardState,
    wizardActions,
  };
}

// Hook for async validation
export function useAsyncZodValidation<T extends FieldValues>(
  schema: z.ZodSchema<T>,
  debounceMs = 300
) {
  const [validationState, setValidationState] = useState<{
    isValidating: boolean;
    errors: Record<string, string>;
    lastValidated: Date | null;
  }>({
    isValidating: false,
    errors: {},
    lastValidated: null,
  });

  const validate = useCallback(
    debounce(async (data: T) => {
      setValidationState((prev) => ({ ...prev, isValidating: true }));

      try {
        const result = schema.safeParse(data);

        if (result.success) {
          setValidationState({
            isValidating: false,
            errors: {},
            lastValidated: new Date(),
          });
        } else {
          const errors = result.error.issues.reduce(
            (acc, issue) => {
              const path = issue.path.join(".");
              acc[path] = issue.message;
              return acc;
            },
            {} as Record<string, string>
          );

          setValidationState({
            isValidating: false,
            errors,
            lastValidated: new Date(),
          });
        }
      } catch (_error) {
        setValidationState({
          isValidating: false,
          errors: { _global: "Validation error occurred" },
          lastValidated: new Date(),
        });
      }
    }, debounceMs),
    [schema, debounceMs]
  );

  return {
    validate,
    ...validationState,
  };
}

// Form wizard hook for multi-step forms
export function useZodFormWizard<T extends FieldValues>(
  steps: Array<{
    name: string;
    schema: z.ZodSchema<Partial<T>>;
    title: string;
    description?: string;
  }>,
  finalSchema: z.ZodSchema<T>
) {
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [stepData, setStepData] = useState<Partial<T>>({});

  const currentStepConfig = steps[currentStep];
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === steps.length - 1;

  const form = useZodForm({
    schema: currentStepConfig.schema,
    defaultValues: stepData as any,
  });

  const goToStep = useCallback(
    (stepIndex: number) => {
      if (stepIndex >= 0 && stepIndex < steps.length) {
        setCurrentStep(stepIndex);
        form.reset(stepData as any);
      }
    },
    [steps.length, form, stepData]
  );

  const nextStep = useCallback(async () => {
    const isValid = await form.trigger();
    if (isValid && !isLastStep) {
      const currentData = form.getValues();
      setStepData((prev) => ({ ...prev, ...currentData }));
      setCompletedSteps((prev) => [...new Set([...prev, currentStep])]);
      setCurrentStep((prev) => prev + 1);
    }
    return isValid;
  }, [form, isLastStep, currentStep]);

  const previousStep = useCallback(() => {
    if (!isFirstStep) {
      const currentData = form.getValues();
      setStepData((prev) => ({ ...prev, ...currentData }));
      setCurrentStep((prev) => prev - 1);
    }
  }, [form, isFirstStep]);

  const submitWizard = useCallback(async () => {
    const currentData = form.getValues();
    const finalData = { ...stepData, ...currentData } as T;

    const result = finalSchema.safeParse(finalData);
    if (result.success) {
      return result.data;
    }
    throw new TripSageValidationError(
      ValidationContext.FORM,
      result.error.issues.map((issue) => ({
        context: ValidationContext.FORM,
        field: issue.path.join("."),
        message: issue.message,
        code: issue.code,
        timestamp: new Date(),
      }))
    );
  }, [form, stepData, finalSchema]);

  const resetWizard = useCallback(() => {
    setCurrentStep(0);
    setCompletedSteps([]);
    setStepData({});
    form.reset({});
  }, [form]);

  return {
    // Current step info
    currentStep,
    currentStepConfig,
    isFirstStep,
    isLastStep,

    // Step data
    completedSteps,
    stepData,

    // Navigation
    goToStep,
    nextStep,
    previousStep,

    // Form
    form,

    // Wizard actions
    submitWizard,
    resetWizard,

    // Progress
    progress: ((currentStep + 1) / steps.length) * 100,
    isStepCompleted: (stepIndex: number) => completedSteps.includes(stepIndex),
  };
}

// Utility function for debouncing
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout;
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

// Export types for external use
export type { UseZodFormOptions, UseZodFormReturn };
