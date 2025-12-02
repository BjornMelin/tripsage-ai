/**
 * @fileoverview MFA domain schemas for enrollment, verification, and backup codes.
 */

import { z } from "zod";

// ===== CORE SCHEMAS =====

export const mfaFactorSchema = z.strictObject({
  friendlyName: z.string().min(1).max(100).optional(),
  id: z.string().min(1),
  status: z.enum(["unverified", "verified", "recovery"]),
  type: z.enum(["totp", "webauthn", "phone"]),
});

export type MfaFactor = z.infer<typeof mfaFactorSchema>;

export const mfaEnrollmentSchema = z.strictObject({
  challengeId: z.string().min(1),
  expiresAt: z.string().datetime({ offset: true }),
  factorId: z.string().min(1),
  issuedAt: z.string().datetime({ offset: true }),
  qrCode: z.string().min(1),
  ttlSeconds: z.number().int().min(0),
  uri: z.string().optional(),
});

export type MfaEnrollment = z.infer<typeof mfaEnrollmentSchema>;

export const mfaVerificationInputSchema = z.strictObject({
  challengeId: z.string().min(1),
  code: z.string().regex(/^[0-9]{6}$/, { message: "Code must be a 6-digit number" }),
  factorId: z.string().min(1),
});

export type MfaVerificationInput = z.infer<typeof mfaVerificationInputSchema>;

export const backupCodeSchema = z
  .string()
  .regex(/^[A-Z0-9]{5}-[A-Z0-9]{5}$/, { message: "Invalid backup code format" });

export type BackupCode = z.infer<typeof backupCodeSchema>;

export const backupCodeListSchema = z.strictObject({
  codes: z.array(backupCodeSchema),
  remaining: z.number().int().min(0),
});

export type BackupCodeList = z.infer<typeof backupCodeListSchema>;

// ===== TOOL INPUT SCHEMAS =====

export const backupCodeVerifyInputSchema = z.strictObject({
  code: backupCodeSchema,
});

export type BackupCodeVerifyInput = z.infer<typeof backupCodeVerifyInputSchema>;

export const mfaChallengeInputSchema = z.strictObject({
  factorId: z.string().min(1),
});

export type MfaChallengeInput = z.infer<typeof mfaChallengeInputSchema>;

export const backupCodeRegenerateInputSchema = z.strictObject({
  count: z.number().int().min(1).max(20).default(10),
});

export type BackupCodeRegenerateInput = z.infer<typeof backupCodeRegenerateInputSchema>;

export const mfaSessionRevokeInputSchema = z.strictObject({
  scope: z.enum(["others", "global", "local"]).default("others"),
});

export type MfaSessionRevokeInput = z.infer<typeof mfaSessionRevokeInputSchema>;
