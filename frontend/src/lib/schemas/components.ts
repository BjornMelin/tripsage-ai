/**
 * Zod schemas for component props validation
 * Runtime validation for all component props to ensure type safety
 */

import React from "react";
import { z } from "zod";

// Base component prop patterns
const classNameSchema = z.string().optional();
const childrenSchema = z.any(); // React.ReactNode
const callbackSchema = z.function().optional();
const refSchema = z.any().optional();

// Common UI component schemas
export const buttonPropsSchema = z.object({
  variant: z
    .enum(["default", "destructive", "outline", "secondary", "ghost", "link"])
    .optional(),
  size: z.enum(["default", "sm", "lg", "icon"]).optional(),
  asChild: z.boolean().optional(),
  disabled: z.boolean().optional(),
  loading: z.boolean().optional(),
  onClick: callbackSchema,
  children: childrenSchema.optional(),
  className: classNameSchema,
  type: z.enum(["button", "submit", "reset"]).optional(),
});

export const inputPropsSchema = z.object({
  type: z
    .enum([
      "text",
      "email",
      "password",
      "number",
      "tel",
      "url",
      "search",
      "date",
      "time",
      "datetime-local",
    ])
    .optional(),
  value: z.union([z.string(), z.number()]).optional(),
  defaultValue: z.union([z.string(), z.number()]).optional(),
  placeholder: z.string().optional(),
  disabled: z.boolean().optional(),
  required: z.boolean().optional(),
  readOnly: z.boolean().optional(),
  autoComplete: z.string().optional(),
  autoFocus: z.boolean().optional(),
  min: z.union([z.string(), z.number()]).optional(),
  max: z.union([z.string(), z.number()]).optional(),
  step: z.union([z.string(), z.number()]).optional(),
  pattern: z.string().optional(),
  minLength: z.number().optional(),
  maxLength: z.number().optional(),
  onChange: callbackSchema,
  onBlur: callbackSchema,
  onFocus: callbackSchema,
  className: classNameSchema,
  ref: refSchema,
});

export const selectPropsSchema = z.object({
  value: z.string().optional(),
  defaultValue: z.string().optional(),
  placeholder: z.string().optional(),
  disabled: z.boolean().optional(),
  required: z.boolean().optional(),
  multiple: z.boolean().optional(),
  onValueChange: z.function().optional(),
  children: childrenSchema,
  className: classNameSchema,
});

export const cardPropsSchema = z.object({
  variant: z.enum(["default", "elevated", "outlined"]).optional(),
  padding: z.enum(["none", "sm", "md", "lg"]).optional(),
  children: childrenSchema,
  className: classNameSchema,
  onClick: callbackSchema,
});

export const dialogPropsSchema = z.object({
  open: z.boolean().optional(),
  defaultOpen: z.boolean().optional(),
  onOpenChange: z.function().optional(),
  modal: z.boolean().optional(),
  children: childrenSchema,
});

export const toastPropsSchema = z.object({
  id: z.string(),
  title: z.string().optional(),
  description: z.string().optional(),
  variant: z.enum(["default", "destructive", "success", "warning"]).optional(),
  duration: z.number().positive().optional(),
  action: z
    .object({
      label: z.string(),
      onClick: z.function(),
    })
    .optional(),
  onDismiss: z.function().optional(),
});

// Form component schemas
export const formFieldPropsSchema = z.object({
  name: z.string(),
  label: z.string().optional(),
  description: z.string().optional(),
  required: z.boolean().optional(),
  disabled: z.boolean().optional(),
  error: z.string().optional(),
  children: childrenSchema,
  className: classNameSchema,
});

export const formPropsSchema = z.object({
  onSubmit: z.function(),
  onReset: z.function().optional(),
  loading: z.boolean().optional(),
  disabled: z.boolean().optional(),
  children: childrenSchema,
  className: classNameSchema,
});

// Search component schemas
export const searchFormPropsSchema = z.object({
  searchType: z.enum(["flight", "accommodation", "activity", "destination"]),
  initialParams: z.unknown().optional(),
  onSearch: z.function(),
  onParamsChange: z.function().optional(),
  loading: z.boolean().optional(),
  disabled: z.boolean().optional(),
  className: classNameSchema,
});

export const searchResultsPropsSchema = z.object({
  results: z.object({
    flights: z.array(z.unknown()).optional(),
    accommodations: z.array(z.unknown()).optional(),
    activities: z.array(z.unknown()).optional(),
    destinations: z.array(z.unknown()).optional(),
  }),
  loading: z.boolean().optional(),
  error: z.string().optional(),
  onItemClick: z.function().optional(),
  onLoadMore: z.function().optional(),
  hasMore: z.boolean().optional(),
  className: classNameSchema,
});

export const searchFiltersPropsSchema = z.object({
  searchType: z.enum(["flight", "accommodation", "activity", "destination"]),
  filters: z.record(z.unknown()),
  onFiltersChange: z.function(),
  onReset: z.function().optional(),
  disabled: z.boolean().optional(),
  className: classNameSchema,
});

// Trip component schemas
export const tripCardPropsSchema = z.object({
  trip: z.object({
    id: z.string(),
    title: z.string(),
    destination: z.string(),
    startDate: z.string(),
    endDate: z.string(),
    status: z.enum(["planning", "booked", "active", "completed", "cancelled"]),
    budget: z
      .object({
        total: z.number(),
        spent: z.number(),
        currency: z.string(),
      })
      .optional(),
    travelers: z.array(z.unknown()),
  }),
  variant: z.enum(["default", "compact", "detailed"]).optional(),
  onClick: z.function().optional(),
  onEdit: z.function().optional(),
  onDelete: z.function().optional(),
  className: classNameSchema,
});

export const budgetTrackerPropsSchema = z.object({
  budget: z.object({
    total: z.number().positive(),
    spent: z.number().nonnegative(),
    currency: z.string().length(3),
    breakdown: z.record(z.number()).optional(),
  }),
  showBreakdown: z.boolean().optional(),
  editable: z.boolean().optional(),
  onUpdate: z.function().optional(),
  className: classNameSchema,
});

export const itineraryBuilderPropsSchema = z.object({
  tripId: z.string(),
  itinerary: z.array(
    z.object({
      id: z.string(),
      day: z.number(),
      date: z.string(),
      activities: z.array(z.unknown()),
    })
  ),
  editable: z.boolean().optional(),
  onUpdate: z.function().optional(),
  onActivityAdd: z.function().optional(),
  onActivityRemove: z.function().optional(),
  onActivityReorder: z.function().optional(),
  className: classNameSchema,
});

// Chat component schemas
export const chatInterfacePropsSchema = z.object({
  conversationId: z.string().optional(),
  messages: z.array(
    z.object({
      id: z.string(),
      role: z.enum(["user", "assistant", "system"]),
      content: z.string(),
      timestamp: z.string(),
      metadata: z.unknown().optional(),
    })
  ),
  loading: z.boolean().optional(),
  disabled: z.boolean().optional(),
  onSendMessage: z.function(),
  onClearConversation: z.function().optional(),
  placeholder: z.string().optional(),
  maxLength: z.number().positive().optional(),
  allowAttachments: z.boolean().optional(),
  className: classNameSchema,
});

export const messageItemPropsSchema = z.object({
  message: z.object({
    id: z.string(),
    role: z.enum(["user", "assistant", "system"]),
    content: z.string(),
    timestamp: z.string(),
    metadata: z.unknown().optional(),
    attachments: z.array(z.unknown()).optional(),
  }),
  variant: z.enum(["default", "compact", "detailed"]).optional(),
  showTimestamp: z.boolean().optional(),
  showActions: z.boolean().optional(),
  onEdit: z.function().optional(),
  onDelete: z.function().optional(),
  onCopy: z.function().optional(),
  className: classNameSchema,
});

export const typingIndicatorPropsSchema = z.object({
  visible: z.boolean(),
  userName: z.string().optional(),
  duration: z.number().positive().optional(),
  className: classNameSchema,
});

// Dashboard component schemas
export const dashboardStatsPropsSchema = z.object({
  stats: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      value: z.union([z.string(), z.number()]),
      change: z.number().optional(),
      changeType: z.enum(["increase", "decrease", "neutral"]).optional(),
      format: z.enum(["number", "currency", "percentage", "text"]).optional(),
    })
  ),
  loading: z.boolean().optional(),
  error: z.string().optional(),
  refreshable: z.boolean().optional(),
  onRefresh: z.function().optional(),
  className: classNameSchema,
});

export const quickActionsPropsSchema = z.object({
  actions: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      description: z.string().optional(),
      icon: z.any().optional(),
      href: z.string().optional(),
      onClick: z.function().optional(),
      disabled: z.boolean().optional(),
      badge: z.string().optional(),
    })
  ),
  layout: z.enum(["grid", "list"]).optional(),
  columns: z.number().int().positive().max(6).optional(),
  loading: z.boolean().optional(),
  className: classNameSchema,
});

// Navigation component schemas
export const navbarPropsSchema = z.object({
  user: z
    .object({
      id: z.string(),
      name: z.string(),
      email: z.string(),
      avatar: z.string().optional(),
    })
    .optional(),
  currentPath: z.string(),
  onSignOut: z.function().optional(),
  showUserMenu: z.boolean().optional(),
  showNotifications: z.boolean().optional(),
  notificationCount: z.number().nonnegative().optional(),
  className: classNameSchema,
});

export const sidebarPropsSchema = z.object({
  navigation: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      href: z.string(),
      icon: z.any().optional(),
      badge: z.string().optional(),
      children: z.array(z.unknown()).optional(),
    })
  ),
  currentPath: z.string(),
  collapsed: z.boolean().optional(),
  onToggle: z.function().optional(),
  className: classNameSchema,
});

// Error component schemas
export const errorBoundaryPropsSchema = z.object({
  children: childrenSchema,
  fallback: z.function().optional(),
  onError: z.function().optional(),
  resetKeys: z.array(z.unknown()).optional(),
  resetOnPropsChange: z.boolean().optional(),
  className: classNameSchema,
});

export const errorFallbackPropsSchema = z.object({
  error: z.instanceof(Error),
  reset: z.function(),
  title: z.string().optional(),
  description: z.string().optional(),
  showDetails: z.boolean().optional(),
  actions: z
    .array(
      z.object({
        label: z.string(),
        onClick: z.function(),
        variant: z.enum(["default", "destructive", "outline", "secondary"]).optional(),
      })
    )
    .optional(),
  className: classNameSchema,
});

// Loading component schemas
export const loadingSpinnerPropsSchema = z.object({
  size: z.enum(["sm", "md", "lg"]).optional(),
  color: z.enum(["primary", "secondary", "muted"]).optional(),
  text: z.string().optional(),
  fullScreen: z.boolean().optional(),
  className: classNameSchema,
});

export const skeletonPropsSchema = z.object({
  variant: z.enum(["default", "circular", "rectangular", "text"]).optional(),
  width: z.union([z.string(), z.number()]).optional(),
  height: z.union([z.string(), z.number()]).optional(),
  count: z.number().int().positive().max(20).optional(),
  spacing: z.enum(["none", "sm", "md", "lg"]).optional(),
  className: classNameSchema,
});

// Utility functions for component validation
export const validateComponentProps = <T>(
  schema: z.ZodSchema<T>,
  props: unknown
): T => {
  try {
    return schema.parse(props);
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error("Component props validation failed:", error.issues);
      throw new Error(
        `Invalid component props: ${error.issues.map((i) => i.message).join(", ")}`
      );
    }
    throw error;
  }
};

export const safeValidateComponentProps = <T>(
  schema: z.ZodSchema<T>,
  props: unknown
) => {
  const result = schema.safeParse(props);
  if (!result.success) {
    console.warn("Component props validation failed:", result.error.issues);
  }
  return result;
};

// Higher-order component for runtime props validation
export const withPropsValidation = <T extends Record<string, any>>(
  schema: z.ZodSchema<T>,
  componentName?: string
) => {
  return (WrappedComponent: React.ComponentType<T>) => {
    const ValidatedComponent = (props: T) => {
      if (process.env.NODE_ENV === "development") {
        const result = safeValidateComponentProps(schema, props);
        if (!result.success) {
          console.error(
            `Props validation failed for ${componentName || WrappedComponent.name}:`,
            result.error.issues
          );
        }
      }
      return React.createElement(WrappedComponent, props);
    };

    ValidatedComponent.displayName = `withPropsValidation(${componentName || WrappedComponent.name})`;
    return ValidatedComponent;
  };
};

// Type exports
export type ButtonProps = z.infer<typeof buttonPropsSchema>;
export type InputProps = z.infer<typeof inputPropsSchema>;
export type SelectProps = z.infer<typeof selectPropsSchema>;
export type CardProps = z.infer<typeof cardPropsSchema>;
export type DialogProps = z.infer<typeof dialogPropsSchema>;
export type ToastProps = z.infer<typeof toastPropsSchema>;
export type FormFieldProps = z.infer<typeof formFieldPropsSchema>;
export type FormProps = z.infer<typeof formPropsSchema>;
export type SearchFormProps = z.infer<typeof searchFormPropsSchema>;
export type SearchResultsProps = z.infer<typeof searchResultsPropsSchema>;
export type SearchFiltersProps = z.infer<typeof searchFiltersPropsSchema>;
export type TripCardProps = z.infer<typeof tripCardPropsSchema>;
export type BudgetTrackerProps = z.infer<typeof budgetTrackerPropsSchema>;
export type ItineraryBuilderProps = z.infer<typeof itineraryBuilderPropsSchema>;
export type ChatInterfaceProps = z.infer<typeof chatInterfacePropsSchema>;
export type MessageItemProps = z.infer<typeof messageItemPropsSchema>;
export type TypingIndicatorProps = z.infer<typeof typingIndicatorPropsSchema>;
export type DashboardStatsProps = z.infer<typeof dashboardStatsPropsSchema>;
export type QuickActionsProps = z.infer<typeof quickActionsPropsSchema>;
export type NavbarProps = z.infer<typeof navbarPropsSchema>;
export type SidebarProps = z.infer<typeof sidebarPropsSchema>;
export type ErrorBoundaryProps = z.infer<typeof errorBoundaryPropsSchema>;
export type ErrorFallbackProps = z.infer<typeof errorFallbackPropsSchema>;
export type LoadingSpinnerProps = z.infer<typeof loadingSpinnerPropsSchema>;
export type SkeletonProps = z.infer<typeof skeletonPropsSchema>;
