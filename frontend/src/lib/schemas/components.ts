/**
 * Zod schemas for component props validation
 * Runtime validation for all component props to ensure type safety
 */

import React from "react";
import { z } from "zod";

// Base component prop patterns
const CLASS_NAME_SCHEMA = z.string().optional();
const CHILDREN_SCHEMA = z.any(); // React.ReactNode
const CALLBACK_SCHEMA = z.function().optional();
const REF_SCHEMA = z.any().optional();

// Common UI component schemas
export const buttonPropsSchema = z.object({
  asChild: z.boolean().optional(),
  children: CHILDREN_SCHEMA.optional(),
  className: CLASS_NAME_SCHEMA,
  disabled: z.boolean().optional(),
  loading: z.boolean().optional(),
  onClick: CALLBACK_SCHEMA,
  size: z.enum(["default", "sm", "lg", "icon"]).optional(),
  type: z.enum(["button", "submit", "reset"]).optional(),
  variant: z
    .enum(["default", "destructive", "outline", "secondary", "ghost", "link"])
    .optional(),
});

export const inputPropsSchema = z.object({
  autoComplete: z.string().optional(),
  autoFocus: z.boolean().optional(),
  className: CLASS_NAME_SCHEMA,
  defaultValue: z.union([z.string(), z.number()]).optional(),
  disabled: z.boolean().optional(),
  max: z.union([z.string(), z.number()]).optional(),
  maxLength: z.number().optional(),
  min: z.union([z.string(), z.number()]).optional(),
  minLength: z.number().optional(),
  onBlur: CALLBACK_SCHEMA,
  onChange: CALLBACK_SCHEMA,
  onFocus: CALLBACK_SCHEMA,
  pattern: z.string().optional(),
  placeholder: z.string().optional(),
  readOnly: z.boolean().optional(),
  ref: REF_SCHEMA,
  required: z.boolean().optional(),
  step: z.union([z.string(), z.number()]).optional(),
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
});

export const selectPropsSchema = z.object({
  children: CHILDREN_SCHEMA,
  className: CLASS_NAME_SCHEMA,
  defaultValue: z.string().optional(),
  disabled: z.boolean().optional(),
  multiple: z.boolean().optional(),
  onValueChange: z.function().optional(),
  placeholder: z.string().optional(),
  required: z.boolean().optional(),
  value: z.string().optional(),
});

export const cardPropsSchema = z.object({
  children: CHILDREN_SCHEMA,
  className: CLASS_NAME_SCHEMA,
  onClick: CALLBACK_SCHEMA,
  padding: z.enum(["none", "sm", "md", "lg"]).optional(),
  variant: z.enum(["default", "elevated", "outlined"]).optional(),
});

export const dialogPropsSchema = z.object({
  children: CHILDREN_SCHEMA,
  defaultOpen: z.boolean().optional(),
  modal: z.boolean().optional(),
  onOpenChange: z.function().optional(),
  open: z.boolean().optional(),
});

export const toastPropsSchema = z.object({
  action: z
    .object({
      label: z.string(),
      onClick: z.function(),
    })
    .optional(),
  description: z.string().optional(),
  duration: z.number().positive().optional(),
  id: z.string(),
  onDismiss: z.function().optional(),
  title: z.string().optional(),
  variant: z.enum(["default", "destructive", "success", "warning"]).optional(),
});

// Form component schemas
export const formFieldPropsSchema = z.object({
  children: CHILDREN_SCHEMA,
  className: CLASS_NAME_SCHEMA,
  description: z.string().optional(),
  disabled: z.boolean().optional(),
  error: z.string().optional(),
  label: z.string().optional(),
  name: z.string(),
  required: z.boolean().optional(),
});

export const formPropsSchema = z.object({
  children: CHILDREN_SCHEMA,
  className: CLASS_NAME_SCHEMA,
  disabled: z.boolean().optional(),
  loading: z.boolean().optional(),
  onReset: z.function().optional(),
  onSubmit: z.function(),
});

// Search component schemas
export const searchFormPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  disabled: z.boolean().optional(),
  initialParams: z.unknown().optional(),
  loading: z.boolean().optional(),
  onParamsChange: z.function().optional(),
  onSearch: z.function(),
  searchType: z.enum(["flight", "accommodation", "activity", "destination"]),
});

export const searchResultsPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  error: z.string().optional(),
  hasMore: z.boolean().optional(),
  loading: z.boolean().optional(),
  onItemClick: z.function().optional(),
  onLoadMore: z.function().optional(),
  results: z.object({
    accommodations: z.array(z.unknown()).optional(),
    activities: z.array(z.unknown()).optional(),
    destinations: z.array(z.unknown()).optional(),
    flights: z.array(z.unknown()).optional(),
  }),
});

export const searchFiltersPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  disabled: z.boolean().optional(),
  filters: z.record(z.string(), z.unknown()),
  onFiltersChange: z.function(),
  onReset: z.function().optional(),
  searchType: z.enum(["flight", "accommodation", "activity", "destination"]),
});

// Trip component schemas
export const tripCardPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  onClick: z.function().optional(),
  onDelete: z.function().optional(),
  onEdit: z.function().optional(),
  trip: z.object({
    budget: z
      .object({
        currency: z.string(),
        spent: z.number(),
        total: z.number(),
      })
      .optional(),
    destination: z.string(),
    endDate: z.string(),
    id: z.string(),
    startDate: z.string(),
    status: z.enum(["planning", "booked", "active", "completed", "cancelled"]),
    title: z.string(),
    travelers: z.array(z.unknown()),
  }),
  variant: z.enum(["default", "compact", "detailed"]).optional(),
});

export const budgetTrackerPropsSchema = z.object({
  budget: z.object({
    breakdown: z.record(z.string(), z.number()).optional(),
    currency: z.string().length(3),
    spent: z.number().nonnegative(),
    total: z.number().positive(),
  }),
  className: CLASS_NAME_SCHEMA,
  editable: z.boolean().optional(),
  onUpdate: z.function().optional(),
  showBreakdown: z.boolean().optional(),
});

export const itineraryBuilderPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  editable: z.boolean().optional(),
  itinerary: z.array(
    z.object({
      activities: z.array(z.unknown()),
      date: z.string(),
      day: z.number(),
      id: z.string(),
    })
  ),
  onActivityAdd: z.function().optional(),
  onActivityRemove: z.function().optional(),
  onActivityReorder: z.function().optional(),
  onUpdate: z.function().optional(),
  tripId: z.string(),
});

// Chat component schemas
export const chatInterfacePropsSchema = z.object({
  allowAttachments: z.boolean().optional(),
  className: CLASS_NAME_SCHEMA,
  conversationId: z.string().optional(),
  disabled: z.boolean().optional(),
  loading: z.boolean().optional(),
  maxLength: z.number().positive().optional(),
  messages: z.array(
    z.object({
      content: z.string(),
      id: z.string(),
      metadata: z.unknown().optional(),
      role: z.enum(["user", "assistant", "system"]),
      timestamp: z.string(),
    })
  ),
  onClearConversation: z.function().optional(),
  onSendMessage: z.function(),
  placeholder: z.string().optional(),
});

export const messageItemPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  message: z.object({
    attachments: z.array(z.unknown()).optional(),
    content: z.string(),
    id: z.string(),
    metadata: z.unknown().optional(),
    role: z.enum(["user", "assistant", "system"]),
    timestamp: z.string(),
  }),
  onCopy: z.function().optional(),
  onDelete: z.function().optional(),
  onEdit: z.function().optional(),
  showActions: z.boolean().optional(),
  showTimestamp: z.boolean().optional(),
  variant: z.enum(["default", "compact", "detailed"]).optional(),
});

export const typingIndicatorPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  duration: z.number().positive().optional(),
  userName: z.string().optional(),
  visible: z.boolean(),
});

// Dashboard component schemas
export const dashboardStatsPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  error: z.string().optional(),
  loading: z.boolean().optional(),
  onRefresh: z.function().optional(),
  refreshable: z.boolean().optional(),
  stats: z.array(
    z.object({
      change: z.number().optional(),
      changeType: z.enum(["increase", "decrease", "neutral"]).optional(),
      format: z.enum(["number", "currency", "percentage", "text"]).optional(),
      id: z.string(),
      label: z.string(),
      value: z.union([z.string(), z.number()]),
    })
  ),
});

export const quickActionsPropsSchema = z.object({
  actions: z.array(
    z.object({
      badge: z.string().optional(),
      description: z.string().optional(),
      disabled: z.boolean().optional(),
      href: z.string().optional(),
      icon: z.any().optional(),
      id: z.string(),
      label: z.string(),
      onClick: z.function().optional(),
    })
  ),
  className: CLASS_NAME_SCHEMA,
  columns: z.number().int().positive().max(6).optional(),
  layout: z.enum(["grid", "list"]).optional(),
  loading: z.boolean().optional(),
});

// Navigation component schemas
export const navbarPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  currentPath: z.string(),
  notificationCount: z.number().nonnegative().optional(),
  onSignOut: z.function().optional(),
  showNotifications: z.boolean().optional(),
  showUserMenu: z.boolean().optional(),
  user: z
    .object({
      avatar: z.string().optional(),
      email: z.string(),
      id: z.string(),
      name: z.string(),
    })
    .optional(),
});

export const sidebarPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  collapsed: z.boolean().optional(),
  currentPath: z.string(),
  navigation: z.array(
    z.object({
      badge: z.string().optional(),
      children: z.array(z.unknown()).optional(),
      href: z.string(),
      icon: z.any().optional(),
      id: z.string(),
      label: z.string(),
    })
  ),
  onToggle: z.function().optional(),
});

// Error component schemas
export const errorBoundaryPropsSchema = z.object({
  children: CHILDREN_SCHEMA,
  className: CLASS_NAME_SCHEMA,
  fallback: z.function().optional(),
  onError: z.function().optional(),
  resetKeys: z.array(z.unknown()).optional(),
  resetOnPropsChange: z.boolean().optional(),
});

export const errorFallbackPropsSchema = z.object({
  actions: z
    .array(
      z.object({
        label: z.string(),
        onClick: z.function(),
        variant: z.enum(["default", "destructive", "outline", "secondary"]).optional(),
      })
    )
    .optional(),
  className: CLASS_NAME_SCHEMA,
  description: z.string().optional(),
  error: z.instanceof(Error),
  reset: z.function(),
  showDetails: z.boolean().optional(),
  title: z.string().optional(),
});

// Loading component schemas
export const loadingSpinnerPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  color: z.enum(["primary", "secondary", "muted"]).optional(),
  fullScreen: z.boolean().optional(),
  size: z.enum(["sm", "md", "lg"]).optional(),
  text: z.string().optional(),
});

export const skeletonPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  count: z.number().int().positive().max(20).optional(),
  height: z.union([z.string(), z.number()]).optional(),
  spacing: z.enum(["none", "sm", "md", "lg"]).optional(),
  variant: z.enum(["default", "circular", "rectangular", "text"]).optional(),
  width: z.union([z.string(), z.number()]).optional(),
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
export const withPropsValidation = <T extends Record<string, unknown>>(
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
