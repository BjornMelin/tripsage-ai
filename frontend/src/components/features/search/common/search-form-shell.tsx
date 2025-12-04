/**
 * @fileoverview Reusable search form shell component.
 *
 * Provides a consistent wrapper for search forms with form state management,
 * validation, loading states, and error handling.
 */

"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircleIcon, Loader2Icon, SearchIcon } from "lucide-react";
import { useState, useTransition } from "react";
import type { DefaultValues, FieldValues, Path, UseFormReturn } from "react-hook-form";
import { useForm } from "react-hook-form";
import type { z } from "zod";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Form } from "@/components/ui/form";
import { withClientTelemetrySpan } from "@/lib/telemetry/client";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";
import { cn } from "@/lib/utils";

/** Popular item for quick selection */
export interface PopularItem<TParams> {
  id: string;
  label: string;
  params: Partial<TParams>;
  icon?: React.ReactNode;
}

/** Props for the SearchFormShell component */
export interface SearchFormShellProps<TSchema extends z.ZodType<FieldValues>> {
  /** Zod schema for form validation */
  schema: TSchema;
  /** Default form values */
  defaultValues: DefaultValues<z.infer<TSchema>>;
  /** Handler called on form submission */
  onSubmit: (params: z.infer<TSchema>) => Promise<void>;
  /** Telemetry span name for tracking submissions */
  telemetrySpanName?: string;
  /** Error message to display */
  error?: string | null;
  /** Custom submit button text */
  submitLabel?: string;
  /** Custom loading button text */
  loadingLabel?: string;
  /** Whether the form is disabled */
  disabled?: boolean;
  /** Additional className for the form */
  className?: string;
  /** Render function for form fields */
  children: (form: UseFormReturn<z.infer<TSchema>>) => React.ReactNode;
  /** Popular items for quick selection */
  popularItems?: PopularItem<z.infer<TSchema>>[];
  /** Handler for popular item selection */
  onPopularItemSelect?: (
    item: PopularItem<z.infer<TSchema>>,
    form: UseFormReturn<z.infer<TSchema>>
  ) => void;
}

/**
 * Shared search form shell with consistent validation, loading, and error states.
 *
 * @example
 * ```tsx
 * <SearchFormShell
 *   schema={flightSearchSchema}
 *   defaultValues={{ origin: "", destination: "" }}
 *   onSubmit={handleSearch}
 *   telemetrySpanName="flight.search"
 * >
 *   {(form) => (
 *     <>
 *       <FormField name="origin" control={form.control} ... />
 *       <FormField name="destination" control={form.control} ... />
 *     </>
 *   )}
 * </SearchFormShell>
 * ```
 */
export function SearchFormShell<TSchema extends z.ZodType<FieldValues>>({
  schema,
  defaultValues,
  onSubmit,
  telemetrySpanName = "search.submit",
  error,
  submitLabel = "Search",
  loadingLabel = "Searching...",
  disabled = false,
  className,
  children,
  popularItems,
  onPopularItemSelect,
}: SearchFormShellProps<TSchema>) {
  const [isPending, startTransition] = useTransition();
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  const form = useForm<z.infer<TSchema>>({
    defaultValues,
    mode: "onChange",
    // biome-ignore lint/suspicious/noExplicitAny: zodResolver requires flexible schema typing for Zod v4 compatibility
    resolver: zodResolver(schema as any),
  });

  const handleSubmit = form.handleSubmit((data) => {
    setSubmissionError(null);
    startTransition(async () => {
      try {
        await withClientTelemetrySpan(telemetrySpanName, {}, async () => {
          try {
            await onSubmit(data);
          } catch (err) {
            recordClientErrorOnActiveSpan(
              err instanceof Error ? err : new Error(String(err))
            );
            throw err;
          }
        });
      } catch (err) {
        setSubmissionError(err instanceof Error ? err.message : String(err));
      }
    });
  });

  const handlePopularItemClick = (item: PopularItem<z.infer<TSchema>>) => {
    if (onPopularItemSelect) {
      onPopularItemSelect(item, form);
    } else {
      // Default behavior: update provided fields while preserving metadata
      Object.entries(item.params).forEach(([key, value]) => {
        form.setValue(key as Path<z.infer<TSchema>>, value, {
          shouldDirty: true,
          shouldTouch: true,
          shouldValidate: true,
        });
      });
    }
  };

  const isSubmitting = isPending || disabled;

  return (
    <Form {...form}>
      <form onSubmit={handleSubmit} className={cn("space-y-4", className)}>
        {children(form)}

        {popularItems && popularItems.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <span className="text-muted-foreground text-sm">Popular:</span>
            {popularItems.map((item) => (
              <Button
                key={item.id}
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handlePopularItemClick(item)}
                disabled={isSubmitting}
                className="h-7 text-xs"
              >
                {item.icon}
                {item.label}
              </Button>
            ))}
          </div>
        )}

        {(submissionError || error) && (
          <Alert variant="destructive">
            <AlertCircleIcon className="h-4 w-4" />
            <AlertDescription>{submissionError || error}</AlertDescription>
          </Alert>
        )}

        <Button type="submit" disabled={isSubmitting} className="w-full sm:w-auto">
          {isPending ? (
            <>
              <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
              {loadingLabel}
            </>
          ) : (
            <>
              <SearchIcon className="mr-2 h-4 w-4" />
              {submitLabel}
            </>
          )}
        </Button>
      </form>
    </Form>
  );
}
