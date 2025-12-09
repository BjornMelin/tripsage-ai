/**
 * @fileoverview Authentication form validation schemas.
 * Includes login, registration, password reset, and password change form schemas.
 */

import { z } from "zod";
import { EMAIL_SCHEMA, NAME_SCHEMA, PASSWORD_SCHEMA } from "./shared/person";

// ===== FORM SCHEMAS =====
// UI form validation schemas with user-friendly error messages

/**
 * Zod schema for login form validation.
 * Validates email and password credentials with user-friendly error messages.
 */
export const loginFormSchema = z.object({
  email: EMAIL_SCHEMA,
  password: z
    .string()
    .min(1, { error: "Password is required" })
    .max(128, { error: "Password too long" }),
  rememberMe: z.boolean().optional(),
});

/** TypeScript type for login form data. */
export type LoginFormData = z.infer<typeof loginFormSchema>;

/**
 * Zod schema for registration form validation.
 * Validates user registration data including password confirmation and terms acceptance.
 */
export const registerFormSchema = z
  .object({
    acceptTerms: z.boolean().refine((val) => val === true, {
      error: "You must accept the terms and conditions",
    }),
    confirmPassword: z.string().min(1, { error: "Please confirm your password" }),
    email: EMAIL_SCHEMA,
    firstName: NAME_SCHEMA,
    lastName: NAME_SCHEMA,
    marketingOptIn: z.boolean().optional(),
    password: PASSWORD_SCHEMA,
  })
  .refine((data) => data.password === data.confirmPassword, {
    error: "Passwords don't match",
    path: ["confirmPassword"],
  });

/** TypeScript type for registration form data. */
export type RegisterFormData = z.infer<typeof registerFormSchema>;

/**
 * Zod schema for password reset form validation.
 * Validates email address for password reset initiation.
 */
export const resetPasswordFormSchema = z.object({
  email: EMAIL_SCHEMA,
});

/** TypeScript type for password reset form data. */
export type ResetPasswordFormData = z.infer<typeof resetPasswordFormSchema>;

/**
 * Zod schema for password reset confirmation form validation.
 * Validates new password, confirmation, and reset token.
 */
export const confirmResetPasswordFormSchema = z
  .object({
    confirmPassword: z.string().min(1, { error: "Please confirm your password" }),
    newPassword: PASSWORD_SCHEMA,
    token: z.string().min(1, { error: "Reset token is required" }),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    error: "Passwords don't match",
    path: ["confirmPassword"],
  });

/** TypeScript type for password reset confirmation form data. */
export type ConfirmResetPasswordFormData = z.infer<
  typeof confirmResetPasswordFormSchema
>;

/**
 * Zod schema for password change form validation.
 * Validates current password, new password, and confirmation with business rules.
 */
export const changePasswordFormSchema = z
  .object({
    confirmPassword: z.string().min(1, { error: "Please confirm your password" }),
    currentPassword: z.string().min(1, { error: "Current password is required" }),
    newPassword: PASSWORD_SCHEMA,
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    error: "Passwords don't match",
    path: ["confirmPassword"],
  })
  .refine((data) => data.currentPassword !== data.newPassword, {
    error: "New password must be different from current password",
    path: ["newPassword"],
  });

/** TypeScript type for password change form data. */
export type ChangePasswordFormData = z.infer<typeof changePasswordFormSchema>;
