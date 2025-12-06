/**
 * @fileoverview Reusable number input field component for forms.
 * Integrates with React Hook Form and provides proper number parsing.
 */

"use client";

import type { Control, FieldValues, Path, PathValue } from "react-hook-form";
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";

/**
 * Props for the NumberInputField component.
 *
 * @template T The form data type extending FieldValues.
 */
interface NumberInputFieldProps<T extends FieldValues> {
  /** React Hook Form control instance. */
  control: Control<T>;
  /** Field name path in the form data. */
  name: Path<T>;
  /** Label text displayed above the input. */
  label: string;
  /** Minimum allowed value (optional). */
  min?: number;
  /** Maximum allowed value (optional). */
  max?: number;
  /** Step increment for the input (optional). */
  step?: number | string;
  /** Default value for the input (optional). */
  defaultValue?: PathValue<T, Path<T>>;
  /** Placeholder text (optional). */
  placeholder?: string;
  /** Whether the field is required (optional). */
  required?: boolean;
  /** Whether the input should be disabled (optional). */
  disabled?: boolean;
}

/**
 * Reusable number input field component for React Hook Form.
 *
 * Handles proper number parsing, converting string input to number values
 * for the form state. Integrates with shadcn/ui form components.
 *
 * Note: HTML `min`/`max` attributes only provide browser-level guarding; callers
 * should mirror these constraints in their validation schema (e.g., Zod or
 * React Hook Form rules) to ensure consistent client/server enforcement.
 *
 * @template T The form data type extending FieldValues.
 * @param props Component props.
 * @returns A form field with number input.
 *
 * @example
 * ```tsx
 * <NumberInputField
 *   control={form.control}
 *   name="passengers"
 *   label="Number of Passengers"
 *   min={1}
 *   max={9}
 *   defaultValue={1}
 *   placeholder="Enter number of passengers"
 * />
 * ```
 */
export function NumberInputField<T extends FieldValues>({
  control,
  name,
  label,
  min,
  max,
  step,
  defaultValue,
  placeholder,
  required,
  disabled,
}: NumberInputFieldProps<T>) {
  return (
    <FormField
      control={control}
      name={name}
      defaultValue={defaultValue}
      render={({ field }) => (
        <FormItem>
          <FormLabel>{label}</FormLabel>
          <FormControl>
            <Input
              type="number"
              placeholder={placeholder}
              min={min}
              max={max}
              step={step}
              required={required}
              disabled={disabled}
              {...field}
              value={field.value ?? ""}
              onChange={(e) => {
                const value = e.target.value;
                if (value === "") {
                  field.onChange(undefined);
                  return;
                }

                const parsedNumber = Number(value);
                // Only commit finite numbers to form state; otherwise clear value
                if (Number.isFinite(parsedNumber)) {
                  field.onChange(parsedNumber);
                } else {
                  field.onChange(undefined);
                }
              }}
            />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
