/**
 * Comprehensive example demonstrating Zod validation integration
 * This file shows how our validation system works across different boundaries
 */

import { z } from "zod";
// import { ValidatedApiClient } from "./api/validated-client"; // Future implementation
import { apiResponseSchema } from "./schemas/api";
import { flightSearchFormSchema } from "./schemas/forms";
import { ValidationContext, validateFormData, validateStrict } from "./validation";

// Example 1: Form Validation
export function demonstrateFormValidation() {
  console.log("=== Form Validation Example ===");

  // Valid form data
  const validFormData = {
    tripType: "round-trip" as const,
    origin: "NYC",
    destination: "LAX",
    departureDate: "2025-07-15",
    returnDate: "2025-07-22",
    passengers: {
      adults: 2,
      children: 0,
      infants: 0,
    },
    cabinClass: "economy" as const,
    directOnly: false,
  };

  const result = validateFormData(flightSearchFormSchema, validFormData);

  if (result.success) {
    console.log("✅ Form validation passed:", result.data);
  } else {
    console.log("❌ Form validation failed:", result.errors);
  }

  // Invalid form data - missing required fields
  const invalidFormData = {
    tripType: "round-trip" as const,
    // Missing origin, destination, etc.
  };

  const invalidResult = validateFormData(flightSearchFormSchema, invalidFormData);

  if (!invalidResult.success) {
    console.log("❌ Expected validation failure:", invalidResult.errors);
  }
}

// Example 2: API Response Validation
export function demonstrateApiValidation() {
  console.log("\n=== API Response Validation Example ===");

  const userSchema = z.object({
    id: z.string(),
    email: z.string().email(),
    name: z.string(),
  });

  const responseSchema = apiResponseSchema(userSchema);

  // Valid API response
  const validResponse = {
    success: true,
    data: {
      id: "user-123",
      email: "test@example.com",
      name: "Test User",
    },
  };

  try {
    const validatedResponse = validateStrict(
      responseSchema,
      validResponse,
      ValidationContext.API
    );
    console.log("✅ API validation passed:", validatedResponse);
  } catch (error) {
    console.log("❌ API validation failed:", error);
  }

  // Invalid API response
  const invalidResponse = {
    success: true,
    data: {
      id: "user-123",
      email: "invalid-email", // Invalid email format
      name: "Test User",
    },
  };

  try {
    validateStrict(responseSchema, invalidResponse, ValidationContext.API);
  } catch (error) {
    console.log("❌ Expected API validation failure:", error);
  }
}

// Example 3: Component Props Validation
export function demonstrateComponentValidation() {
  console.log("\n=== Component Props Validation Example ===");

  const buttonPropsSchema = z.object({
    variant: z.enum(["primary", "secondary", "outline"]).default("primary"),
    size: z.enum(["sm", "md", "lg"]).default("md"),
    disabled: z.boolean().default(false),
    children: z.string().min(1, "Button text is required"),
    onClick: z.function().optional(),
  });

  // Valid props
  const validProps = {
    variant: "primary" as const,
    size: "lg" as const,
    disabled: false,
    children: "Click me",
  };

  try {
    const validatedProps = validateStrict(
      buttonPropsSchema,
      validProps,
      ValidationContext.COMPONENT
    );
    console.log("✅ Component props validation passed:", validatedProps);
  } catch (error) {
    console.log("❌ Component props validation failed:", error);
  }
}

// Example 4: Comprehensive Error Handling
export function demonstrateErrorHandling() {
  console.log("\n=== Error Handling Example ===");

  const complexSchema = z.object({
    user: z.object({
      email: z.string().email("Please enter a valid email address"),
      age: z
        .number()
        .min(13, "Must be at least 13 years old")
        .max(120, "Age must be realistic"),
    }),
    preferences: z.object({
      theme: z.enum(["light", "dark"], {
        errorMap: () => ({ message: "Theme must be either 'light' or 'dark'" }),
      }),
      notifications: z.boolean(),
    }),
    metadata: z.record(z.string(), z.unknown()).optional(),
  });

  const invalidData = {
    user: {
      email: "not-an-email",
      age: 5, // Too young
    },
    preferences: {
      theme: "purple", // Invalid theme
      notifications: "yes", // Should be boolean
    },
  };

  const result = validateFormData(complexSchema, invalidData);

  if (!result.success) {
    console.log("❌ Validation errors found:");
    result.errors?.forEach((error, index) => {
      console.log(
        `  ${index + 1}. ${error.path?.join(".") || "root"}: ${error.message}`
      );
    });
  }
}

// Example 5: Using the Validated API Client
export async function demonstrateValidatedApiClient() {
  console.log("\n=== Validated API Client Example ===");

  // const apiClient = new ValidatedApiClient({ // Future implementation
  //   baseUrl: process.env.NEXT_PUBLIC_API_URL || "",
  // });

  try {
    // This would make a real API call with validation
    console.log("📡 Making validated API call...");

    // Mock successful response
    const userProfile = {
      id: "user-123",
      email: "test@example.com",
      personalInfo: {
        firstName: "John",
        lastName: "Doe",
      },
    };

    console.log("✅ Validated API response:", userProfile);
  } catch (error) {
    console.log("❌ API client error:", error);
  }
}

// Run all examples
export function runAllValidationExamples() {
  console.log("🔍 Running Comprehensive Zod Validation Examples\n");

  demonstrateFormValidation();
  demonstrateApiValidation();
  demonstrateComponentValidation();
  demonstrateErrorHandling();
  demonstrateValidatedApiClient();

  console.log("\n✨ All validation examples completed!");
}

// Performance monitoring helper
export function measureValidationPerformance() {
  console.log("\n=== Validation Performance Test ===");

  const testSchema = z.object({
    id: z.string().uuid(),
    email: z.string().email(),
    data: z.array(
      z.object({
        name: z.string(),
        value: z.number(),
      })
    ),
  });

  const testData = {
    id: "123e4567-e89b-12d3-a456-426614174000",
    email: "test@example.com",
    data: Array.from({ length: 1000 }, (_, i) => ({
      name: `item-${i}`,
      value: i,
    })),
  };

  const iterations = 1000;
  const startTime = performance.now();

  for (let i = 0; i < iterations; i++) {
    try {
      testSchema.parse(testData);
    } catch {
      // Ignore errors for performance test
    }
  }

  const endTime = performance.now();
  const avgTime = (endTime - startTime) / iterations;

  console.log(`⚡ Validation performance: ${avgTime.toFixed(3)}ms per validation`);
  console.log(
    `📊 Total time for ${iterations} validations: ${(endTime - startTime).toFixed(2)}ms`
  );
}
