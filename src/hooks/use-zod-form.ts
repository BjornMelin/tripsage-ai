/**
 * @fileoverview Form helpers that integrate Zod validation with React Hook Form.
 */

import { zodResolver } from "@hookform/resolvers/zod";
import type { ValidationResult } from "@schemas/validation";
import { useCallback, useState } from "react";
import {
  type FieldErrors,
  type FieldValues,
  type UseFormProps,
  type UseFormReturn,
  useForm,
} from "react-hook-form";
import type { z } from "zod";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";

// Form options - using a data type parameter to avoid complex generic constraints
interface UseZodFormOptions<Data extends FieldValues>
  extends Omit<UseFormProps<Data>, "resolver"> {
  schema: z.ZodType<Data>;
  validateMode?: "onSubmit" | "onBlur" | "onChange" | "onTouched" | "all";
  transformSubmitData?: (data: Data) => Data | Promise<Data>;
  onValidationError?: (errors: ValidationResult<Data>) => void;
  onSubmitSuccess?: (data: Data) => void | Promise<void>;
  onSubmitError?: (error: Error) => void;
}

// form return type
interface UseZodFormReturn<T extends FieldValues> extends UseFormReturn<T> {
  // Safe submit with validation
  handleSubmitSafe: (
    onValid: (data: T) => void | Promise<void>,
    onInvalid?: (errors: ValidationResult<T>) => void
  ) => (e?: React.BaseSyntheticEvent) => Promise<void>;

  isFormComplete: boolean;

  // Validation state
  validationState: {
    isValidating: boolean;
    lastValidation: Date | null;
    validationErrors: string[];
  };
}

type FieldErrorLike = {
  message?: unknown;
  type?: unknown;
  types?: unknown;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isFieldErrorLike(value: unknown): value is FieldErrorLike {
  if (!isRecord(value)) return false;
  return "message" in value || "type" in value || "types" in value;
}

const MAX_ERROR_DEPTH = 20;

function collectRhfErrors(
  errors: unknown,
  path: string[],
  out: Array<{ path: string | undefined; message: string; code: string }>,
  depth = 0
) {
  if (!errors) return;

  // Depth guard to prevent stack overflow on deeply-nested objects
  if (depth >= MAX_ERROR_DEPTH) {
    out.push({
      code: "MAX_DEPTH_EXCEEDED",
      message: "Error structure exceeded maximum depth",
      path: path.length > 0 ? path.join(".") : undefined,
    });
    return;
  }

  if (Array.isArray(errors)) {
    errors.forEach((entry, index) => {
      collectRhfErrors(entry, [...path, String(index)], out, depth + 1);
    });

    for (const [key, value] of Object.entries(errors)) {
      if (/^\d+$/.test(key)) continue;
      collectRhfErrors(
        value,
        key === "root" ? [...path] : [...path, key],
        out,
        depth + 1
      );
    }
    return;
  }

  if (!isRecord(errors)) return;

  if (isFieldErrorLike(errors)) {
    const code =
      typeof errors.type === "string" && errors.type.trim().length > 0
        ? errors.type
        : "FIELD_VALIDATION_ERROR";
    const message =
      typeof errors.message === "string" && errors.message.trim().length > 0
        ? errors.message
        : "Invalid value";

    out.push({
      code,
      message,
      path: path.length > 0 ? path.join(".") : undefined,
    });

    if (isRecord(errors.types)) {
      for (const [type, value] of Object.entries(errors.types)) {
        if (typeof value !== "string" || value.trim().length === 0) continue;
        if (value === message) continue;
        out.push({
          code: type,
          message: value,
          path: path.length > 0 ? path.join(".") : undefined,
        });
      }
    }
  }

  for (const [key, value] of Object.entries(errors)) {
    if (key === "message" || key === "type" || key === "types" || key === "ref")
      continue;
    collectRhfErrors(
      value,
      key === "root" ? [...path] : [...path, key],
      out,
      depth + 1
    );
  }
}

function validationResultFromFieldErrors<Data extends FieldValues>(
  fieldErrors: FieldErrors<Data>
): ValidationResult<Data> {
  const flattened: Array<{ path: string | undefined; message: string; code: string }> =
    [];
  collectRhfErrors(fieldErrors, [], flattened);

  if (flattened.length === 0) {
    return {
      errors: [
        {
          code: "FORM_VALIDATION_ERROR",
          context: "form",
          message: "Validation failed",
          timestamp: new Date(),
        },
      ],
      success: false,
    };
  }

  return {
    errors: flattened.map((error) => ({
      code: error.code,
      context: "form" as const,
      field: error.path,
      message: error.message,
      path: error.path ? error.path.split(".") : undefined,
      timestamp: new Date(),
    })),
    success: false,
  };
}

// Custom hook for enhanced Zod form handling
export function useZodForm<Data extends FieldValues>(
  options: UseZodFormOptions<Data>
): UseZodFormReturn<Data> {
  const {
    schema,
    validateMode,
    transformSubmitData,
    onValidationError,
    onSubmitSuccess,
    onSubmitError,
    mode,
    ...formOptions
  } = options;

  // Initialize React Hook Form with Zod resolver
  const resolvedMode = mode ?? validateMode ?? "onChange";
  const form = useForm<Data>({
    ...formOptions,
    mode: resolvedMode,
    // biome-ignore lint/suspicious/noExplicitAny: zodResolver requires flexible schema typing
    resolver: zodResolver(schema as any),
    reValidateMode: options.reValidateMode ?? "onChange",
  });

  // Validation state management
  const [validationState, setValidationState] = useState({
    isValidating: false,
    lastValidation: null as Date | null,
    validationErrors: [] as string[],
  });

  // Safe submit handler with enhanced error handling
  const handleSubmitSafe = useCallback(
    (
      onValid: (data: Data) => void | Promise<void>,
      onInvalid?: (errors: ValidationResult<Data>) => void
    ) =>
      async (e?: React.BaseSyntheticEvent) => {
        const submit = form.handleSubmit(
          async (data) => {
            setValidationState({
              isValidating: false,
              lastValidation: new Date(),
              validationErrors: [],
            });

            try {
              let submitData = data;
              if (transformSubmitData) {
                submitData = await transformSubmitData(data);
              }

              await onValid(submitData);
              await onSubmitSuccess?.(submitData);
            } catch (error) {
              const submitError =
                error instanceof Error ? error : new Error("Submit failed");

              if (onSubmitError) {
                onSubmitError(submitError);
              } else {
                recordClientErrorOnActiveSpan(submitError);
              }

              setValidationState((prev) => ({
                ...prev,
                isValidating: false,
                lastValidation: prev.lastValidation ?? new Date(),
              }));
            }
          },
          (fieldErrors) => {
            const validationResult = validationResultFromFieldErrors<Data>(fieldErrors);

            setValidationState({
              isValidating: false,
              lastValidation: new Date(),
              validationErrors: validationResult.errors?.map((e) => e.message) ?? [],
            });

            onValidationError?.(validationResult);
            onInvalid?.(validationResult);
          }
        );

        setValidationState((prev) => ({ ...prev, isValidating: true }));
        try {
          await submit(e);
        } finally {
          setValidationState((prev) =>
            prev.isValidating ? { ...prev, isValidating: false } : prev
          );
        }
      },
    [form, onSubmitError, onSubmitSuccess, onValidationError, transformSubmitData]
  );

  // Subscribe to form validity via RHF's formState Proxy.
  const { isValid, isValidating } = form.formState;
  const isFormComplete = isValid;

  return {
    ...form,
    handleSubmitSafe,
    isFormComplete,
    validationState: {
      ...validationState,
      isValidating: validationState.isValidating || isValidating,
    },
  };
}

// Export types for external use
export type { UseZodFormOptions, UseZodFormReturn };
