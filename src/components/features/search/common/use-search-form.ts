/**
 * @fileoverview Shared React Hook Form setup for search feature forms.
 */

"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import type {
  DefaultValues,
  FieldValues,
  UseFormProps,
  UseFormReturn,
} from "react-hook-form";
import { useForm } from "react-hook-form";
import type { z } from "zod";

type AnyFieldValuesSchema = z.core.$ZodType<FieldValues, FieldValues>;
type FormFieldValues<Schema extends AnyFieldValuesSchema> = z.input<Schema>;
type FormSubmitValues<Schema extends AnyFieldValuesSchema> = z.output<Schema>;

/**
 * Shared React Hook Form setup for search feature forms.
 *
 * @param schema - The Zod schema to use for validation.
 * @param defaultValues - The default values to use for the form.
 * @param options - The options to use for the form.
 * @returns A React Hook Form instance.
 */
export function useSearchForm<Schema extends AnyFieldValuesSchema>(
  schema: Schema,
  defaultValues: DefaultValues<FormFieldValues<Schema>>,
  options: Omit<
    UseFormProps<FormFieldValues<Schema>, unknown, FormSubmitValues<Schema>>,
    "resolver" | "defaultValues"
  > = {}
): UseFormReturn<FormFieldValues<Schema>, unknown, FormSubmitValues<Schema>> {
  return useForm<FormFieldValues<Schema>, unknown, FormSubmitValues<Schema>>({
    defaultValues,
    mode: "onChange",
    resolver: zodResolver(schema),
    ...options,
  });
}
