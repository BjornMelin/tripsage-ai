/**
 * @fileoverview Form helpers that integrate Zod validation with React Hook Form.
 */

import { zodResolver } from "@hookform/resolvers/zod";
import type { ValidationResult } from "@schemas/validation";
import { useCallback, useMemo, useState } from "react";
import {
  type DefaultValues,
  type FieldPath,
  type FieldValues,
  type UseFormProps,
  type UseFormReturn,
  useForm,
} from "react-hook-form";
import { ZodError, type z } from "zod";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";

// Form options - using a data type parameter to avoid complex generic constraints
interface UseZodFormOptions<Data extends FieldValues>
  extends Omit<UseFormProps<Data>, "resolver"> {
  schema: z.ZodType<Data>;
  validateMode?: "onSubmit" | "onBlur" | "onChange" | "onTouched" | "all";
  reValidateMode?: "onSubmit" | "onBlur" | "onChange";
  enableAsyncValidation?: boolean;
  debounceValidation?: number;
  transformSubmitData?: (data: Data) => Data | Promise<Data>;
  onValidationError?: (errors: ValidationResult<Data>) => void;
  onSubmitSuccess?: (data: Data) => void | Promise<void>;
  onSubmitError?: (error: Error) => void;

  // Wizard options
  enableWizard?: boolean;
  wizardSteps?: string[];
  stepValidationSchemas?: z.ZodType<unknown>[];
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
export function useZodForm<Data extends FieldValues>(
  options: UseZodFormOptions<Data>
): UseZodFormReturn<Data> {
  const {
    schema,
    transformSubmitData,
    onValidationError,
    onSubmitSuccess,
    onSubmitError,
    enableAsyncValidation: _enableAsyncValidation = false,
    ...formOptions
  } = options;

  // Initialize React Hook Form with Zod resolver
  const form = useForm<Data>({
    mode: options.validateMode || "onChange",
    // biome-ignore lint/suspicious/noExplicitAny: zodResolver requires flexible schema typing
    resolver: zodResolver(schema as any),
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
    (
      fieldName: FieldPath<Data>,
      value: unknown
    ): Promise<ValidationResult<unknown>> => {
      try {
        // In Zod v4, we can't access .shape directly. Instead, validate the whole object
        // and extract field-specific errors if validation fails
        const testData = { [fieldName]: value } as Partial<Data>;

        // Create a partial schema for validation - handle both object and other schema types
        let partialSchema: z.ZodType<unknown>;
        if ("partial" in schema && typeof schema.partial === "function") {
          partialSchema = (schema as z.ZodObject<z.ZodRawShape>).partial();
        } else {
          // For non-object schemas, use the schema as-is for field validation
          partialSchema = schema;
        }

        const result = partialSchema.safeParse(testData);

        if (result.success) {
          return Promise.resolve({ data: value, success: true });
        }

        // Find field-specific errors
        const fieldErrors = result.error.issues
          .filter((issue) => issue.path.join(".") === fieldName)
          .map((issue) => ({
            code: issue.code,
            context: "form" as const,
            field: fieldName as string,
            message: issue.message,
            path: issue.path.map(String),
            timestamp: new Date(),
            value: issue.input,
          }));

        if (fieldErrors.length === 0) {
          return Promise.resolve({ data: value, success: true });
        }

        return Promise.resolve({
          errors: fieldErrors,
          success: false,
        });
      } catch (error) {
        return Promise.resolve({
          errors: [
            {
              code: "FIELD_VALIDATION_ERROR",
              context: "form" as const,
              field: fieldName as string,
              message: error instanceof Error ? error.message : "Validation failed",
              timestamp: new Date(),
            },
          ],
          success: false,
        });
      }
    },
    [schema]
  );

  // Validate all fields
  const validateAllFields = useCallback((): Promise<ValidationResult<Data>> => {
    setValidationState((prev) => ({ ...prev, isValidating: true }));

    try {
      const formData = form.getValues();
      const zodResult = (schema as z.ZodType<Data>).safeParse(formData);
      const result: ValidationResult<Data> = zodResult.success
        ? { data: zodResult.data, success: true }
        : {
            errors: zodResult.error.issues.map((issue) => ({
              code: issue.code,
              context: "form" as const,
              field: issue.path.join(".") || undefined,
              message: issue.message,
              path: issue.path.map(String),
              timestamp: new Date(),
              value: issue.input,
            })),
            success: false,
          };

      setValidationState((prev) => ({
        ...prev,
        isValidating: false,
        lastValidation: new Date(),
        validationErrors: result.success
          ? []
          : result.errors?.map((e) => e.message) || [],
      }));

      if (!result.success && onValidationError) {
        onValidationError(result as ValidationResult<Data>);
      }

      return Promise.resolve(result as ValidationResult<Data>);
    } catch (error) {
      const validationResult = {
        errors: [
          {
            code: "FORM_VALIDATION_ERROR",
            context: "form" as const,
            message: error instanceof Error ? error.message : "Validation failed",
            timestamp: new Date(),
          },
        ],
        success: false as const,
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

      return Promise.resolve(validationResult);
    }
  }, [form, schema, onValidationError]);

  // Safe submit handler with enhanced error handling
  const handleSubmitSafe = useCallback(
    (
      onValid: (data: Data) => void | Promise<void>,
      onInvalid?: (errors: ValidationResult<Data>) => void
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
          let submitData: Data;
          if (!validationResult.data) {
            return;
          }
          submitData = validationResult.data;
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
            recordClientErrorOnActiveSpan(submitError);
          }

          // Set form errors if it's a Zod validation error
          if (error instanceof ZodError) {
            error.issues.forEach((issue) => {
              const field = issue.path.join(".") as FieldPath<Data>;
              form.setError(field, { message: issue.message, type: "manual" });
            });
          }
        }
      },
    [validateAllFields, transformSubmitData, onSubmitSuccess, onSubmitError, form]
  );

  // Helper methods
  const isFieldValid = useCallback(
    (fieldName: FieldPath<Data>): boolean => {
      const fieldState = form.getFieldState(fieldName);
      return !fieldState.error;
    },
    [form]
  );

  const getFieldError = useCallback(
    (fieldName: FieldPath<Data>): string | undefined => {
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

  const getCleanData = useCallback((): Data => {
    const data = form.getValues();
    const result = (schema as z.ZodType<Data>).parse(data);
    return result;
  }, [form, schema]);

  const resetToDefaults = useCallback(() => {
    // React Hook Form v7+ expects DefaultValues<Data> or undefined
    if (options.defaultValues) {
      form.reset(options.defaultValues as DefaultValues<Data>);
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
      isFirstStep: currentStep === 0,
      isLastStep: currentStep === wizardSteps.length - 1,
      totalSteps: wizardSteps.length,
    };
  }, [enableWizard, currentStep, wizardSteps.length]);

  return {
    ...form,
    getCleanData,
    getFieldError,
    handleSubmitSafe,
    hasAnyErrors,
    isFieldValid,
    isFormComplete,
    resetToDefaults,
    validateAllFields,
    validateField,
    validationState,
    wizardActions,
    wizardState,
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
    errors: {},
    isValidating: false,
    lastValidated: null,
  });

  const validate = useCallback(
    debounce((data: T) => {
      setValidationState((prev) => ({ ...prev, isValidating: true }));

      try {
        const result = schema.safeParse(data);

        if (result.success) {
          setValidationState({
            errors: {},
            isValidating: false,
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
            errors,
            isValidating: false,
            lastValidated: new Date(),
          });
        }
      } catch (_error) {
        setValidationState({
          errors: { _global: "Validation error occurred" },
          isValidating: false,
          lastValidated: new Date(),
        });
      }
    }, debounceMs),
    []
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
    defaultValues: stepData as DefaultValues<T>,
    schema: currentStepConfig.schema as z.ZodSchema<T>,
  });

  const goToStep = useCallback(
    (stepIndex: number) => {
      if (stepIndex >= 0 && stepIndex < steps.length) {
        setCurrentStep(stepIndex);
        form.reset(stepData as DefaultValues<T>);
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

  const submitWizard = useCallback((): T => {
    const currentData = form.getValues();
    const finalData = { ...stepData, ...currentData } as T;

    const result = finalSchema.safeParse(finalData);
    if (result.success) {
      return result.data;
    }
    const error = new Error(
      `Form validation failed: ${result.error.issues.map((i) => i.message).join(", ")}`
    );
    (error as Error & { issues: z.ZodIssue[] }).issues = result.error.issues;
    throw error;
  }, [form, stepData, finalSchema]);

  const resetWizard = useCallback(() => {
    setCurrentStep(0);
    setCompletedSteps([]);
    setStepData({});
    form.reset({} as DefaultValues<T>);
  }, [form]);

  return {
    // Step data
    completedSteps,
    // Current step info
    currentStep,
    currentStepConfig,

    // Form
    form,

    // Navigation
    goToStep,
    isFirstStep,
    isLastStep,
    isStepCompleted: (stepIndex: number) => completedSteps.includes(stepIndex),
    nextStep,
    previousStep,

    // Progress
    progress: ((currentStep + 1) / steps.length) * 100,
    resetWizard,
    stepData,

    // Wizard actions
    submitWizard,
  };
}

// Utility function for debouncing
function debounce<T extends unknown[]>(
  func: (...args: T) => unknown,
  wait: number
): (...args: T) => void {
  let timeout: NodeJS.Timeout;
  return (...args: T) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

// Export types for external use
export type { UseZodFormOptions, UseZodFormReturn };
