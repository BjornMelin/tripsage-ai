/**
 * Central schema registry and exports
 * All Zod schemas for comprehensive runtime type safety
 */

// Re-export all schemas
export * from "./api";
export * from "./forms";
export * from "./memory";
export * from "./search";
export * from "./stores";
export * from "./budget";
export * from "./agent-status";
export * from "./env";

// Selective exports to avoid conflicts
export {
  buttonPropsSchema,
  cardPropsSchema,
  inputPropsSchema,
  validateComponentProps,
} from "./components";

export type { LoadingState } from "./error-boundary";
export { loadingStateSchema } from "./error-boundary";

export type { SkeletonProps } from "./loading";
export { skeletonPropsSchema } from "./loading";

// Re-export validation utilities (selective)
export type { ValidationResult } from "../validation";
export {
  ValidationContext,
  validate,
  validateFormData,
  validateStrict,
} from "../validation";

// Schema categories for easy access
import * as apiSchemas from "./api";
import * as componentSchemas from "./components";
import * as errorBoundarySchemas from "./error-boundary";
import * as formSchemas from "./forms";
import * as loadingSchemas from "./loading";
import * as memorySchemas from "./memory";
import * as searchSchemas from "./search";
import * as storeSchemas from "./stores";
import * as budgetSchemas from "./budget";
import * as agentStatusSchemas from "./agent-status";
import * as envSchemas from "./env";

// Central schema registry
export const schemas = {
  api: apiSchemas,
  components: componentSchemas,
  errorBoundary: errorBoundarySchemas,
  forms: formSchemas,
  loading: loadingSchemas,
  memory: memorySchemas,
  search: searchSchemas,
  stores: storeSchemas,
  budget: budgetSchemas,
  agentStatus: agentStatusSchemas,
  env: envSchemas,
} as const;

// Commonly used validation patterns
export const commonPatterns = {
  email: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
  phone: "^\\+?[1-9]\\d{1,14}$",
  uuid: "^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
  password: "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]",
  currency: "^[A-Z]{3}$",
  date: "^\\d{4}-\\d{2}-\\d{2}$",
  time: "^\\d{2}:\\d{2}(:\\d{2})?$",
  datetime: "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d{3})?Z?$",
  url: "^https?:\\/\\/(www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b([-a-zA-Z0-9()@:%_\\+.~#?&//=]*)$",
  slug: "^[a-z0-9]+(?:-[a-z0-9]+)*$",
  hexColor: "^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$",
  base64: "^[A-Za-z0-9+/]*={0,2}$",
  ipv4: "^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",
  creditCard:
    "^(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3[0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})$",
} as const;

// Validation error codes
export const validationCodes = {
  REQUIRED: "required",
  INVALID_TYPE: "invalid_type",
  INVALID_FORMAT: "invalid_format",
  MIN_LENGTH: "min_length",
  MAX_LENGTH: "max_length",
  MIN_VALUE: "min_value",
  MAX_VALUE: "max_value",
  INVALID_EMAIL: "invalid_email",
  INVALID_URL: "invalid_url",
  INVALID_DATE: "invalid_date",
  PASSWORDS_DONT_MATCH: "passwords_dont_match",
  CUSTOM_VALIDATION: "custom_validation",
  NETWORK_ERROR: "network_error",
  SERVER_ERROR: "server_error",
  UNAUTHORIZED: "unauthorized",
  FORBIDDEN: "forbidden",
  NOT_FOUND: "not_found",
  RATE_LIMITED: "rate_limited",
  SERVICE_UNAVAILABLE: "service_unavailable",
} as const;

// Common error messages
export const errorMessages = {
  [validationCodes.REQUIRED]: "This field is required",
  [validationCodes.INVALID_TYPE]: "Invalid data type",
  [validationCodes.INVALID_FORMAT]: "Invalid format",
  [validationCodes.MIN_LENGTH]: "Too short",
  [validationCodes.MAX_LENGTH]: "Too long",
  [validationCodes.MIN_VALUE]: "Value too small",
  [validationCodes.MAX_VALUE]: "Value too large",
  [validationCodes.INVALID_EMAIL]: "Please enter a valid email address",
  [validationCodes.INVALID_URL]: "Please enter a valid URL",
  [validationCodes.INVALID_DATE]: "Please enter a valid date",
  [validationCodes.PASSWORDS_DONT_MATCH]: "Passwords don't match",
  [validationCodes.CUSTOM_VALIDATION]: "Validation failed",
  [validationCodes.NETWORK_ERROR]: "Network error occurred",
  [validationCodes.SERVER_ERROR]: "Server error occurred",
  [validationCodes.UNAUTHORIZED]: "Unauthorized access",
  [validationCodes.FORBIDDEN]: "Access forbidden",
  [validationCodes.NOT_FOUND]: "Resource not found",
  [validationCodes.RATE_LIMITED]: "Too many requests",
  [validationCodes.SERVICE_UNAVAILABLE]: "Service temporarily unavailable",
} as const;

// Schema validation utilities
import { z } from "zod";
import { ValidationContext, type ValidationResult, validate } from "../validation";

// Quick validation helpers
export const quickValidate = {
  email: (value: unknown): ValidationResult<string> =>
    validate(z.string().email(), value, ValidationContext.FORM),

  uuid: (value: unknown): ValidationResult<string> =>
    validate(z.string().uuid(), value, ValidationContext.FORM),

  date: (value: unknown): ValidationResult<string> =>
    validate(z.string().date(), value, ValidationContext.FORM),

  url: (value: unknown): ValidationResult<string> =>
    validate(z.string().url(), value, ValidationContext.FORM),

  positiveNumber: (value: unknown): ValidationResult<number> =>
    validate(z.number().positive(), value, ValidationContext.FORM),

  nonEmptyString: (value: unknown): ValidationResult<string> =>
    validate(z.string().min(1), value, ValidationContext.FORM),

  password: (value: unknown): ValidationResult<string> =>
    validate(
      z
        .string()
        .min(8, "Password must be at least 8 characters")
        .regex(/^(?=.*[a-z])/, "Must contain lowercase letter")
        .regex(/^(?=.*[A-Z])/, "Must contain uppercase letter")
        .regex(/^(?=.*\d)/, "Must contain number")
        .regex(/^(?=.*[@$!%*?&])/, "Must contain special character"),
      value,
      ValidationContext.FORM
    ),
};

// Schema metadata for documentation
export const schemaMetadata = {
  api: {
    description: "API request and response validation schemas",
    schemas: Object.keys(apiSchemas).length,
    categories: ["auth", "user", "chat", "trip", "api-keys", "errors", "websocket"],
  },
  components: {
    description: "React component props validation schemas",
    schemas: Object.keys(componentSchemas).length,
    categories: [
      "ui",
      "forms",
      "search",
      "trip",
      "chat",
      "dashboard",
      "navigation",
      "loading",
    ],
  },
  forms: {
    description: "Form data validation schemas with comprehensive rules",
    schemas: Object.keys(formSchemas).length,
    categories: ["auth", "profile", "search", "trip", "budget", "chat", "contact"],
  },
  search: {
    description: "Search functionality validation schemas",
    schemas: Object.keys(searchSchemas).length,
    categories: ["params", "results", "filters", "responses"],
  },
  stores: {
    description: "Zustand store state validation schemas",
    schemas: Object.keys(storeSchemas).length,
    categories: ["auth", "user", "search", "trip", "chat", "ui", "budget", "api-keys"],
  },
  memory: {
    description: "Memory and context management schemas",
    schemas: Object.keys(memorySchemas).length,
    categories: ["memory", "preferences", "insights", "conversations"],
  },
  errorBoundary: {
    description: "Error boundary and loading state schemas",
    schemas: Object.keys(errorBoundarySchemas).length,
    categories: ["errors", "loading", "skeleton"],
  },
  loading: {
    description: "Loading state and skeleton component schemas",
    schemas: Object.keys(loadingSchemas).length,
    categories: ["loading", "skeleton"],
  },
  budget: {
    description: "Budget and expense management validation schemas",
    schemas: Object.keys(budgetSchemas).length,
    categories: ["budget", "expenses", "categories", "alerts", "currency"],
  },
  agentStatus: {
    description: "Agent status and workflow management schemas",
    schemas: Object.keys(agentStatusSchemas).length,
    categories: ["agents", "tasks", "workflows", "sessions", "metrics"],
  },
  env: {
    description: "Environment variable validation schemas",
    schemas: Object.keys(envSchemas).length,
    categories: ["server", "client", "features", "security", "integrations"],
  },
} as const;

// Development helpers
export const dev = {
  // List all available schemas
  listSchemas: () => {
    return Object.entries(schemaMetadata).map(([category, meta]) => ({
      category,
      ...meta,
    }));
  },

  // Validate schema coverage
  validateCoverage: () => {
    const totalSchemas = Object.values(schemaMetadata).reduce(
      (total, meta) => total + meta.schemas,
      0
    );

    console.log(`Total schemas: ${totalSchemas}`);
    console.log("Schema distribution:", schemaMetadata);

    return totalSchemas;
  },

  // Test schema validation performance
  benchmarkValidation: (iterations = 1000) => {
    const testData = {
      email: "test@example.com",
      uuid: "123e4567-e89b-12d3-a456-426614174000",
      password: "TestPass123!",
      number: 42,
      string: "test string",
    };

    const results: Record<string, number> = {};

    Object.entries(quickValidate).forEach(([name, validator]) => {
      const startTime = performance.now();

      for (let i = 0; i < iterations; i++) {
        validator(testData[name as keyof typeof testData]);
      }

      const endTime = performance.now();
      results[name] = endTime - startTime;
    });

    console.log("Validation benchmark results (ms):", results);
    return results;
  },
};

// Export everything for comprehensive type safety
export type ValidationCodes = typeof validationCodes;
export type ErrorMessages = typeof errorMessages;
export type CommonPatterns = typeof commonPatterns;
export type SchemaMetadata = typeof schemaMetadata;
