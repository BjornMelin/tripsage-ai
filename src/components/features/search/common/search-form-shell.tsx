/**
 * @fileoverview Reusable search form shell component.
 *
 * Provides a consistent wrapper for search forms with shared quick-select sections
 * (popular + recent), optimistic progress indication, and error handling.
 */

"use client";

import { AlertCircleIcon, Loader2Icon, SearchIcon } from "lucide-react";
import { useState, useTransition } from "react";
import type { FieldValues, Path, UseFormReturn } from "react-hook-form";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Form } from "@/components/ui/form";
import { Progress } from "@/components/ui/progress";
import { withClientTelemetrySpan } from "@/lib/telemetry/client";
import type { ErrorSpanMetadata } from "@/lib/telemetry/client-errors";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";
import { cn } from "@/lib/utils";

export interface SearchFormShellRenderState {
  isPending: boolean;
  isSubmitting: boolean;
  isSubmitDisabled: boolean;
}

/** Quick-select item for populating form fields. */
export interface QuickSelectItem<TParams extends FieldValues> {
  id: string;
  label: string;
  params: Partial<TParams>;
  description?: string;
  icon?: React.ReactNode;
  disabled?: boolean;
}

/** Props for the SearchFormShell component */
export interface SearchFormShellProps<TParams extends FieldValues> {
  /** React Hook Form instance (created via `useSearchForm` or `useForm`). */
  form: UseFormReturn<TParams>;
  /** Handler called on form submission */
  onSubmit: (params: TParams) => Promise<void>;
  /** Telemetry span name for tracking submissions */
  telemetrySpanName?: string;
  /** Telemetry span attributes */
  telemetryAttributes?: Record<string, string | number | boolean>;
  /** Telemetry metadata for errors recorded on the active span */
  telemetryErrorMetadata?: ErrorSpanMetadata;
  /** Error message to display */
  error?: string | null;
  /** Custom submit button text */
  submitLabel?: string;
  /** Custom loading button text */
  loadingLabel?: string;
  /** Whether the form is disabled */
  disabled?: boolean;
  /** Whether submit should be disabled when form is invalid */
  disableSubmitWhenInvalid?: boolean;
  /** Additional className for the form */
  className?: string;
  /** Render function for form fields */
  children: (
    form: UseFormReturn<TParams>,
    state: SearchFormShellRenderState
  ) => React.ReactNode;
  /** Optional content rendered after quick-select sections and before submit. */
  footer?: (
    form: UseFormReturn<TParams>,
    state: SearchFormShellRenderState
  ) => React.ReactNode;
  /** Popular items for quick selection */
  popularItems?: QuickSelectItem<TParams>[];
  /** Recent search items for quick selection */
  recentItems?: QuickSelectItem<TParams>[];
  /** Popular section label */
  popularLabel?: string;
  /** Recent section label */
  recentLabel?: string;
  /** Handler for popular item selection */
  onPopularItemSelect?: (
    item: QuickSelectItem<TParams>,
    form: UseFormReturn<TParams>
  ) => void;
  /** Handler for recent item selection */
  onRecentItemSelect?: (
    item: QuickSelectItem<TParams>,
    form: UseFormReturn<TParams>
  ) => void;
  /** Secondary action rendered next to the submit button */
  secondaryAction?: React.ReactNode;
  /** Whether to show the optimistic progress bar while pending */
  showProgress?: boolean;
}

/**
 * Shared search form shell with consistent validation, loading, and error states.
 *
 * @example
 * ```tsx
 * const form = useSearchForm(flightSearchSchema, defaultValues);
 *
 * <SearchFormShell form={form} onSubmit={handleSearch} telemetrySpanName="flight.search">
 *   {(form) => (
 *     <>
 *       <FormField name="origin" control={form.control} ... />
 *       <FormField name="destination" control={form.control} ... />
 *     </>
 *   )}
 * </SearchFormShell>
 * ```
 */
export function SearchFormShell<TParams extends FieldValues>({
  form,
  onSubmit,
  telemetrySpanName = "search.submit",
  telemetryAttributes,
  telemetryErrorMetadata,
  error,
  submitLabel = "Search",
  loadingLabel = "Searching...",
  disabled = false,
  disableSubmitWhenInvalid = false,
  className,
  children,
  footer,
  popularItems,
  recentItems,
  popularLabel = "Popular",
  recentLabel = "Recent searches",
  onPopularItemSelect,
  onRecentItemSelect,
  secondaryAction,
  showProgress = true,
}: SearchFormShellProps<TParams>) {
  const [isPending, startTransition] = useTransition();
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  const handleSubmit = form.handleSubmit((data) => {
    setSubmissionError(null);
    startTransition(async () => {
      try {
        await withClientTelemetrySpan(
          telemetrySpanName,
          telemetryAttributes ?? {},
          async () => {
            try {
              await onSubmit(data);
            } catch (err) {
              recordClientErrorOnActiveSpan(
                err instanceof Error ? err : new Error(String(err)),
                telemetryErrorMetadata
              );
              throw err;
            }
          }
        );
      } catch (err) {
        setSubmissionError(err instanceof Error ? err.message : String(err));
      }
    });
  });

  const isSubmitting = isPending || disabled;
  const isSubmitDisabled =
    isSubmitting || (disableSubmitWhenInvalid && !form.formState.isValid);

  const applyQuickSelectParams = (item: QuickSelectItem<TParams>) => {
    Object.entries(item.params).forEach(([key, value]) => {
      form.setValue(key as Path<TParams>, value, {
        shouldDirty: true,
        shouldTouch: true,
        shouldValidate: true,
      });
    });
  };

  const renderState: SearchFormShellRenderState = {
    isPending,
    isSubmitDisabled,
    isSubmitting,
  };

  const renderQuickSelectSection = (
    sectionLabel: string,
    items: QuickSelectItem<TParams>[],
    onSelect:
      | ((item: QuickSelectItem<TParams>, form: UseFormReturn<TParams>) => void)
      | undefined
  ) => {
    if (items.length === 0) return null;

    return (
      <div className="space-y-2">
        <div className="text-sm font-medium text-muted-foreground">{sectionLabel}</div>
        <div className="flex flex-wrap gap-2">
          {items.map((item) => (
            <Button
              key={item.id}
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                if (onSelect) {
                  onSelect(item, form);
                  return;
                }
                applyQuickSelectParams(item);
              }}
              disabled={isSubmitting || item.disabled}
              className={cn(
                "h-auto py-2 px-3 flex flex-col items-start",
                item.description ? "gap-0.5" : "gap-0"
              )}
            >
              <span className="inline-flex items-center gap-1.5">
                {item.icon}
                <span className="font-medium">{item.label}</span>
              </span>
              {item.description && (
                <span className="text-xs text-muted-foreground">
                  {item.description}
                </span>
              )}
            </Button>
          ))}
        </div>
      </div>
    );
  };

  return (
    <Form {...form}>
      <form onSubmit={handleSubmit} className={cn("space-y-4", className)}>
        {children(form, renderState)}

        {popularItems
          ? renderQuickSelectSection(popularLabel, popularItems, onPopularItemSelect)
          : null}

        {recentItems
          ? renderQuickSelectSection(recentLabel, recentItems, onRecentItemSelect)
          : null}

        {footer ? footer(form, renderState) : null}

        {(submissionError || error) && (
          <Alert variant="destructive">
            <AlertCircleIcon className="h-4 w-4" />
            <AlertDescription>{submissionError || error}</AlertDescription>
          </Alert>
        )}

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <Button
            type="submit"
            disabled={isSubmitDisabled}
            className="w-full sm:w-auto"
          >
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
          {secondaryAction ? (
            <div className="w-full sm:w-auto">{secondaryAction}</div>
          ) : null}
        </div>

        {showProgress && isPending ? <Progress value={66} className="h-2" /> : null}
      </form>
    </Form>
  );
}
