/**
 * @fileoverview Shared React Hook Form setup for search feature forms.
 *
 * Provides a thin, typed wrapper around react-hook-form with Zod v4 resolver.
 * Keeps configuration consistent across search forms.
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

/**
 * Shared React Hook Form setup for search feature forms.
 *
 * @param schema - The Zod schema to use for validation.
 * @param defaultValues - The default values to use for the form.
 * @param options - The options to use for the form.
 * @returns A React Hook Form instance.
 */
// biome-ignore lint/style/useNamingConvention: Hook name follows existing app conventions.
export function useSearchForm<TSchema extends z.ZodType<FieldValues>>(
  schema: TSchema,
  defaultValues: DefaultValues<z.infer<TSchema>>,
  options: Omit<UseFormProps<z.infer<TSchema>>, "resolver" | "defaultValues"> = {}
): UseFormReturn<z.infer<TSchema>> {
  return useForm<z.infer<TSchema>>({
    defaultValues,
    mode: "onChange",
    // biome-ignore lint/suspicious/noExplicitAny: zodResolver requires flexible schema typing for Zod v4 compatibility
    resolver: zodResolver(schema as any),
    ...options,
  });
}
