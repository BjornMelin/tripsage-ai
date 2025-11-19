/**
 * @fileoverview Component props validation schemas.
 * Runtime validation for all component props to ensure type safety and prevent runtime errors.
 */

import React from "react";
import { z } from "zod";

// ===== CORE SCHEMAS =====
// Core component prop schemas for UI components

// Base component prop patterns
const CLASS_NAME_SCHEMA = z.string().optional();
const CHILDREN_SCHEMA = z.any(); // React.ReactNode
const FUNCTION_SCHEMA = z.custom<(...args: unknown[]) => unknown>(
  (value) => typeof value === "function"
);
const CALLBACK_SCHEMA = FUNCTION_SCHEMA.optional();
const REF_SCHEMA = z.any().optional();

/**
 * Zod schema for button component props.
 * Validates button configuration including variants, sizes, and event handlers.
 */
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

/** TypeScript type for button component props. */
export type ButtonProps = z.infer<typeof buttonPropsSchema>;

/**
 * Zod schema for input component props.
 * Validates input configuration including type, validation, and event handlers.
 */
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

/** TypeScript type for input component props. */
export type InputProps = z.infer<typeof inputPropsSchema>;

/**
 * Zod schema for select component props.
 * Validates select configuration including options, multiple selection, and handlers.
 */
export const selectPropsSchema = z.object({
  children: CHILDREN_SCHEMA,
  className: CLASS_NAME_SCHEMA,
  defaultValue: z.string().optional(),
  disabled: z.boolean().optional(),
  multiple: z.boolean().optional(),
  onValueChange: CALLBACK_SCHEMA,
  placeholder: z.string().optional(),
  required: z.boolean().optional(),
  value: z.string().optional(),
});

/** TypeScript type for select component props. */
export type SelectProps = z.infer<typeof selectPropsSchema>;

/**
 * Zod schema for card component props.
 * Validates card configuration including padding, variants, and click handlers.
 */
export const cardPropsSchema = z.object({
  children: CHILDREN_SCHEMA,
  className: CLASS_NAME_SCHEMA,
  onClick: CALLBACK_SCHEMA,
  padding: z.enum(["none", "sm", "md", "lg"]).optional(),
  variant: z.enum(["default", "elevated", "outlined"]).optional(),
});

/** TypeScript type for card component props. */
export type CardProps = z.infer<typeof cardPropsSchema>;

/**
 * Zod schema for dialog component props.
 * Validates dialog configuration including open state and modal behavior.
 */
export const dialogPropsSchema = z.object({
  children: CHILDREN_SCHEMA,
  defaultOpen: z.boolean().optional(),
  modal: z.boolean().optional(),
  onOpenChange: CALLBACK_SCHEMA,
  open: z.boolean().optional(),
});

/** TypeScript type for dialog component props. */
export type DialogProps = z.infer<typeof dialogPropsSchema>;

/**
 * Zod schema for toast notification component props.
 * Validates toast configuration including messages, actions, and duration.
 */
export const toastPropsSchema = z.object({
  action: z
    .object({
      label: z.string(),
      onClick: FUNCTION_SCHEMA,
    })
    .optional(),
  description: z.string().optional(),
  duration: z.number().positive().optional(),
  id: z.string(),
  onDismiss: CALLBACK_SCHEMA,
  title: z.string().optional(),
  variant: z.enum(["default", "destructive", "success", "warning"]).optional(),
});

/** TypeScript type for toast component props. */
export type ToastProps = z.infer<typeof toastPropsSchema>;

/**
 * Zod schema for form field component props.
 * Validates form field configuration including labels, errors, and validation state.
 */
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

/** TypeScript type for form field component props. */
export type FormFieldProps = z.infer<typeof formFieldPropsSchema>;

/**
 * Zod schema for form component props.
 * Validates form configuration including submission handlers and loading state.
 */
export const formPropsSchema = z.object({
  children: CHILDREN_SCHEMA,
  className: CLASS_NAME_SCHEMA,
  disabled: z.boolean().optional(),
  loading: z.boolean().optional(),
  onReset: CALLBACK_SCHEMA,
  onSubmit: FUNCTION_SCHEMA,
});

/** TypeScript type for form component props. */
export type FormProps = z.infer<typeof formPropsSchema>;

/**
 * Zod schema for search form component props.
 * Validates search form configuration including search type and parameter handlers.
 */
export const searchFormPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  disabled: z.boolean().optional(),
  initialParams: z.unknown().optional(),
  loading: z.boolean().optional(),
  onParamsChange: CALLBACK_SCHEMA,
  onSearch: FUNCTION_SCHEMA,
  searchType: z.enum(["flight", "accommodation", "activity", "destination"]),
});

/** TypeScript type for search form component props. */
export type SearchFormProps = z.infer<typeof searchFormPropsSchema>;

/**
 * Zod schema for search results component props.
 * Validates search results display configuration including results data and pagination.
 */
export const searchResultsPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  error: z.string().optional(),
  hasMore: z.boolean().optional(),
  loading: z.boolean().optional(),
  onItemClick: CALLBACK_SCHEMA,
  onLoadMore: CALLBACK_SCHEMA,
  results: z.object({
    accommodations: z.array(z.unknown()).optional(),
    activities: z.array(z.unknown()).optional(),
    destinations: z.array(z.unknown()).optional(),
    flights: z.array(z.unknown()).optional(),
  }),
});

/** TypeScript type for search results component props. */
export type SearchResultsProps = z.infer<typeof searchResultsPropsSchema>;

/**
 * Zod schema for search filters component props.
 * Validates filter configuration including filter state and change handlers.
 */
export const searchFiltersPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  disabled: z.boolean().optional(),
  filters: z.record(z.string(), z.unknown()),
  onFiltersChange: FUNCTION_SCHEMA,
  onReset: CALLBACK_SCHEMA,
  searchType: z.enum(["flight", "accommodation", "activity", "destination"]),
});

/** TypeScript type for search filters component props. */
export type SearchFiltersProps = z.infer<typeof searchFiltersPropsSchema>;

/**
 * Zod schema for trip card component props.
 * Validates trip card display configuration including trip data and action handlers.
 */
export const tripCardPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  onClick: CALLBACK_SCHEMA,
  onDelete: CALLBACK_SCHEMA,
  onEdit: CALLBACK_SCHEMA,
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

/** TypeScript type for trip card component props. */
export type TripCardProps = z.infer<typeof tripCardPropsSchema>;

/**
 * Zod schema for budget tracker component props.
 * Validates budget display configuration including budget data and update handlers.
 */
export const budgetTrackerPropsSchema = z.object({
  budget: z.object({
    breakdown: z.record(z.string(), z.number()).optional(),
    currency: z.string().length(3),
    spent: z.number().nonnegative(),
    total: z.number().positive(),
  }),
  className: CLASS_NAME_SCHEMA,
  editable: z.boolean().optional(),
  onUpdate: CALLBACK_SCHEMA,
  showBreakdown: z.boolean().optional(),
});

/** TypeScript type for budget tracker component props. */
export type BudgetTrackerProps = z.infer<typeof budgetTrackerPropsSchema>;

/**
 * Zod schema for itinerary builder component props.
 * Validates itinerary builder configuration including itinerary data and edit handlers.
 */
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
  onActivityAdd: CALLBACK_SCHEMA,
  onActivityRemove: CALLBACK_SCHEMA,
  onActivityReorder: CALLBACK_SCHEMA,
  onUpdate: CALLBACK_SCHEMA,
  tripId: z.string(),
});

/** TypeScript type for itinerary builder component props. */
export type ItineraryBuilderProps = z.infer<typeof itineraryBuilderPropsSchema>;

/**
 * Zod schema for chat interface component props.
 * Validates chat interface configuration including messages, handlers, and settings.
 */
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
  onClearConversation: CALLBACK_SCHEMA,
  onSendMessage: FUNCTION_SCHEMA,
  placeholder: z.string().optional(),
});

/** TypeScript type for chat interface component props. */
export type ChatInterfaceProps = z.infer<typeof chatInterfacePropsSchema>;

/**
 * Zod schema for message item component props.
 * Validates message display configuration including message data and action handlers.
 */
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
  onCopy: CALLBACK_SCHEMA,
  onDelete: CALLBACK_SCHEMA,
  onEdit: CALLBACK_SCHEMA,
  showActions: z.boolean().optional(),
  showTimestamp: z.boolean().optional(),
  variant: z.enum(["default", "compact", "detailed"]).optional(),
});

/** TypeScript type for message item component props. */
export type MessageItemProps = z.infer<typeof messageItemPropsSchema>;

/**
 * Zod schema for typing indicator component props.
 * Validates typing indicator configuration including visibility and duration.
 */
export const typingIndicatorPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  duration: z.number().positive().optional(),
  userName: z.string().optional(),
  visible: z.boolean(),
});

/** TypeScript type for typing indicator component props. */
export type TypingIndicatorProps = z.infer<typeof typingIndicatorPropsSchema>;

/**
 * Zod schema for dashboard stats component props.
 * Validates dashboard statistics display configuration including stats data and refresh handlers.
 */
export const dashboardStatsPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  error: z.string().optional(),
  loading: z.boolean().optional(),
  onRefresh: CALLBACK_SCHEMA,
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

/** TypeScript type for dashboard stats component props. */
export type DashboardStatsProps = z.infer<typeof dashboardStatsPropsSchema>;

/**
 * Zod schema for quick actions component props.
 * Validates quick actions configuration including action items and layout settings.
 */
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
      onClick: CALLBACK_SCHEMA,
    })
  ),
  className: CLASS_NAME_SCHEMA,
  columns: z.number().int().positive().max(6).optional(),
  layout: z.enum(["grid", "list"]).optional(),
  loading: z.boolean().optional(),
});

/** TypeScript type for quick actions component props. */
export type QuickActionsProps = z.infer<typeof quickActionsPropsSchema>;

/**
 * Zod schema for navbar component props.
 * Validates navbar configuration including navigation state and user information.
 */
export const navbarPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  currentPath: z.string(),
  notificationCount: z.number().nonnegative().optional(),
  onSignOut: CALLBACK_SCHEMA,
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

/** TypeScript type for navbar component props. */
export type NavbarProps = z.infer<typeof navbarPropsSchema>;

/**
 * Zod schema for sidebar component props.
 * Validates sidebar configuration including navigation items and collapse state.
 */
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
  onToggle: CALLBACK_SCHEMA,
});

/** TypeScript type for sidebar component props. */
export type SidebarProps = z.infer<typeof sidebarPropsSchema>;

/**
 * Zod schema for loading spinner component props.
 * Validates loading spinner configuration including size, color, and display options.
 */
export const loadingSpinnerPropsSchema = z.object({
  className: CLASS_NAME_SCHEMA,
  color: z.enum(["primary", "secondary", "muted"]).optional(),
  fullScreen: z.boolean().optional(),
  size: z.enum(["sm", "md", "lg"]).optional(),
  text: z.string().optional(),
});

/** TypeScript type for loading spinner component props. */
export type LoadingSpinnerProps = z.infer<typeof loadingSpinnerPropsSchema>;

// ===== UTILITY FUNCTIONS =====
// Validation helpers and higher-order components

/**
 * Validates component props against a schema.
 * Throws an error with detailed validation messages if validation fails.
 *
 * @param schema - Zod schema to validate against
 * @param props - Component props to validate
 * @returns Validated props
 * @throws {Error} When validation fails with detailed error information
 */
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

/**
 * Safely validates component props with error handling.
 * Returns a result object with success/error information instead of throwing.
 *
 * @param schema - Zod schema to validate against
 * @param props - Component props to validate
 * @returns Validation result with success/error information
 */
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

/**
 * Higher-order component for runtime props validation.
 * Wraps a component with development-time prop validation.
 *
 * @param schema - Zod schema to validate props against
 * @param componentName - Optional component name for error messages
 * @returns HOC that wraps the component with validation
 */
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
