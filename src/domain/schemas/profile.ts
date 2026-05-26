/**
 * @fileoverview User profile and settings form validation schemas. Includes personal info, preferences, security settings, and email update forms.
 */

import { z } from "zod";
import { primitiveSchemas } from "./registry";
import { EMAIL_SCHEMA, NAME_SCHEMA, PHONE_SCHEMA } from "./shared/person";
import { ISO_DATE_STRING } from "./shared/time";

// ===== FORM SCHEMAS =====
// UI form validation schemas with user-friendly error messages

const CURRENCY_SCHEMA = primitiveSchemas.isoCurrency;

type DateParts = {
  day: number;
  month: number;
  year: number;
};

type DateOfBirthReference = Date | number | string;

const currentIsoTimestamp = (): string => new Date().toISOString();

const parseIsoDateParts = (date: string): DateParts | null => {
  const [yearStr, monthStr, dayStr] = date.split("-");
  const year = Number(yearStr);
  const month = Number(monthStr);
  const day = Number(dayStr);

  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) {
    return null;
  }

  const parsedDate = new Date(year, month - 1, day);
  if (
    parsedDate.getFullYear() !== year ||
    parsedDate.getMonth() !== month - 1 ||
    parsedDate.getDate() !== day
  ) {
    return null;
  }

  return { day, month, year };
};

const calculateAge = (birthDate: DateParts, today: DateParts): number => {
  const birthdayHasPassed =
    today.month > birthDate.month ||
    (today.month === birthDate.month && today.day >= birthDate.day);

  return today.year - birthDate.year - (birthdayHasPassed ? 0 : 1);
};

const getReferenceDateParts = (reference?: DateOfBirthReference): DateParts => {
  const today =
    reference instanceof Date
      ? new Date(reference.getTime())
      : new Date(reference ?? currentIsoTimestamp());

  if (!Number.isFinite(today.getTime())) {
    throw new Error("Invalid date-of-birth reference");
  }

  return {
    day: today.getDate(),
    month: today.getMonth() + 1,
    year: today.getFullYear(),
  };
};

/**
 * Zod schema for personal information form validation.
 * Validates user profile data including name, bio, location, and contact information.
 */
export const createPersonalInfoFormSchema = (referenceDate?: DateOfBirthReference) =>
  z.object({
    bio: z
      .string()
      .max(500, { error: "Bio must be less than 500 characters" })
      .optional(),
    currency: CURRENCY_SCHEMA.optional(),
    dateOfBirth: ISO_DATE_STRING.refine(
      (date) => {
        const birthDate = parseIsoDateParts(date);
        if (!birthDate) return false;

        const age = calculateAge(birthDate, getReferenceDateParts(referenceDate));
        return age >= 13 && age <= 120;
      },
      { error: "You must be between 13 and 120 years old" }
    ).optional(),
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
    phoneNumber: PHONE_SCHEMA.optional(),
    timezone: z.string().optional(),
    website: primitiveSchemas.url.optional().or(z.literal("")),
  });

export const personalInfoFormSchema = createPersonalInfoFormSchema();

/** TypeScript type for personal information form data. */
export type PersonalInfoFormData = z.infer<typeof personalInfoFormSchema>;

/**
 * Zod schema for user preferences form validation.
 * Validates user preferences including currency, language, theme, and notification settings.
 */
export const preferencesFormSchema = z.object({
  currency: CURRENCY_SCHEMA,
  dateFormat: z.enum(["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"]),
  language: z.string().min(1, { error: "Please select a language" }),
  theme: z.enum(["light", "dark", "system"]),
  timeFormat: z.enum(["12h", "24h"]),
  timezone: z.string().min(1, { error: "Please select a timezone" }),
  units: z.enum(["metric", "imperial"]),
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
