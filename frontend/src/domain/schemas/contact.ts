/**
 * @fileoverview Contact and feedback form validation schemas.
 * Includes contact forms, feedback forms, and newsletter subscription schemas.
 */

import { z } from "zod";
import { EMAIL_SCHEMA, NAME_SCHEMA } from "./shared/person";

// ===== FORM SCHEMAS =====
// UI form validation schemas with user-friendly error messages

/**
 * Zod schema for contact form validation.
 * Validates contact form data including category, message, and urgency.
 */
export const contactFormSchema = z.object({
  category: z.enum(["support", "feedback", "bug", "feature", "other"]),
  email: EMAIL_SCHEMA,
  message: z
    .string()
    .min(10, { error: "Message must be at least 10 characters" })
    .max(2000, { error: "Message too long" }),
  name: NAME_SCHEMA,
  subject: z
    .string()
    .min(1, { error: "Subject is required" })
    .max(200, { error: "Subject too long" }),
  urgency: z.enum(["low", "medium", "high"]),
});

/** TypeScript type for contact form data. */
export type ContactFormData = z.infer<typeof contactFormSchema>;

/**
 * Zod schema for feedback form validation.
 * Validates feedback data including rating, category, and description.
 */
export const feedbackFormSchema = z.object({
  anonymous: z.boolean(),
  category: z.enum(["ui", "performance", "feature", "bug", "other"]),
  description: z
    .string()
    .min(10, { error: "Please provide more details" })
    .max(1000, { error: "Description too long" }),
  email: EMAIL_SCHEMA.optional(),
  rating: z
    .number()
    .int()
    .min(1, { error: "Please provide a rating" })
    .max(5, { error: "Rating must be between 1 and 5" }),
  title: z
    .string()
    .min(1, { error: "Title is required" })
    .max(100, { error: "Title too long" }),
});

/** TypeScript type for feedback form data. */
export type FeedbackFormData = z.infer<typeof feedbackFormSchema>;

/**
 * Zod schema for newsletter subscription form validation.
 * Validates subscription preferences including frequency and content preferences.
 */
export const newsletterSubscriptionFormSchema = z.object({
  email: EMAIL_SCHEMA,
  frequency: z.enum(["daily", "weekly", "monthly"]),
  preferences: z.object({
    newFeatures: z.boolean(),
    tips: z.boolean(),
    travelDeals: z.boolean(),
    weeklyDigest: z.boolean(),
  }),
});

/** TypeScript type for newsletter subscription form data. */
export type NewsletterSubscriptionFormData = z.infer<
  typeof newsletterSubscriptionFormSchema
>;
