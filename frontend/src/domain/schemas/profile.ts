/**
 * @fileoverview User profile and settings form validation schemas.
 * Includes personal info, preferences, security settings, and email update forms.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";

// ===== FORM SCHEMAS =====
// UI form validation schemas with user-friendly error messages

// Common validation patterns
const EMAIL_SCHEMA = primitiveSchemas.email.max(255);
const PHONE_SCHEMA = z
  .string()
  .regex(/^\+?[\d\s\-()]{10,20}$/, { error: "Please enter a valid phone number" })
  .optional();
const NAME_SCHEMA = z
  .string()
  .min(1, { error: "Name is required" })
  .max(50, { error: "Name too long" })
  .regex(/^[a-zA-Z\s\-'.]+$/, {
    error: "Name can only contain letters, spaces, hyphens, apostrophes, and periods",
  });
const CURRENCY_SCHEMA = primitiveSchemas.isoCurrency;

/**
 * Zod schema for personal information form validation.
 * Validates user profile data including name, bio, location, and contact information.
 */
export const personalInfoFormSchema = z.object({
  bio: z
    .string()
    .max(500, { error: "Bio must be less than 500 characters" })
    .optional(),
  currency: CURRENCY_SCHEMA.optional(),
  dateOfBirth: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, { error: "Please enter a valid date" })
    .refine(
      (date) => {
        const birthDate = new Date(date);
        const today = new Date();
        const age = today.getFullYear() - birthDate.getFullYear();
        return age >= 13 && age <= 120;
      },
      { error: "You must be between 13 and 120 years old" }
    )
    .optional(),
  displayName: z
    .string()
    .min(1, { error: "Display name is required" })
    .max(50, { error: "Display name must be less than 50 characters" }),
  firstName: NAME_SCHEMA,
  language: z.string().min(2).max(5).optional(),
  lastName: NAME_SCHEMA,
  location: z
    .string()
    .max(100, { error: "Location must be less than 100 characters" })
    .optional(),
  phoneNumber: PHONE_SCHEMA,
  timezone: z.string().optional(),
  website: primitiveSchemas.url.optional().or(z.literal("")),
});

/** TypeScript type for personal information form data. */
export type PersonalInfoFormData = z.infer<typeof personalInfoFormSchema>;

/**
 * Zod schema for user preferences form validation.
 * Validates user preferences including currency, language, theme, and notification settings.
 */
export const preferencesFormSchema = z.object({
  currency: z.string().min(1, { error: "Please select a currency" }),
  dateFormat: z.enum(["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]),
  defaultCurrency: CURRENCY_SCHEMA,
  defaultLanguage: z.string().min(2).max(5),
  emailNotifications: z.boolean(),
  language: z.string().min(1, { error: "Please select a language" }),
  marketingEmails: z.boolean(),
  pushNotifications: z.boolean(),
  smsNotifications: z.boolean(),
  theme: z.enum(["light", "dark", "system"]),
  timeFormat: z.enum(["12h", "24h"]),
  timezone: z.string().min(1, { error: "Please select a timezone" }),
  travelDeals: z.boolean(),
  units: z.enum(["metric", "imperial"]),
  weeklyDigest: z.boolean(),
});

/** TypeScript type for preferences form data. */
export type PreferencesFormData = z.infer<typeof preferencesFormSchema>;

/**
 * Zod schema for security settings form validation.
 * Validates security configuration including two-factor authentication and session settings.
 */
export const securitySettingsFormSchema = z.object({
  backupCodesGenerated: z.boolean().optional(),
  loginAlerts: z.boolean(),
  sessionTimeout: z
    .number()
    .int()
    .positive()
    .max(43200, { error: "Session timeout must be less than 12 hours" }),
  trustedDevices: z.array(z.string()).optional(),
  twoFactorEnabled: z.boolean(),
});

/** TypeScript type for security settings form data. */
export type SecuritySettingsFormData = z.infer<typeof securitySettingsFormSchema>;

/**
 * Zod schema for email update form validation.
 * Validates new email address for account updates.
 */
export const emailUpdateFormSchema = z.object({
  email: EMAIL_SCHEMA,
});

/** TypeScript type for email update form data. */
export type EmailUpdateFormData = z.infer<typeof emailUpdateFormSchema>;
