/**
 * @fileoverview MFA domain schemas for enrollment, verification, and backup codes.
 */

import { primitiveSchemas } from "@schemas/registry";
import { z } from "zod";

// ===== CORE SCHEMAS =====

/** The MFA factor schema. */
export const mfaFactorSchema = z.strictObject({
  friendlyName: z.string().min(1).max(100).optional(),
  id: primitiveSchemas.uuid,
  status: z.enum(["unverified", "verified", "recovery"]),
  type: z.enum(["totp", "webauthn", "phone"]),
});

/** The MFA factor type. */
export type MfaFactor = z.infer<typeof mfaFactorSchema>;

/** The MFA enrollment schema. */
export const mfaEnrollmentSchema = z.strictObject({
  challengeId: primitiveSchemas.uuid,
  expiresAt: primitiveSchemas.isoDateTime,
  factorId: primitiveSchemas.uuid,
  issuedAt: primitiveSchemas.isoDateTime,
  qrCode: z.string().min(1),
  ttlSeconds: z.number().int().min(0),
  uri: z.string().optional(),
});

/** The MFA enrollment type. */
export type MfaEnrollment = z.infer<typeof mfaEnrollmentSchema>;

/** The MFA verification input schema. */
export const mfaVerificationInputSchema = z.strictObject({
  challengeId: primitiveSchemas.uuid,
  code: z.string().regex(/^[0-9]{6}$/, { error: "Code must be a 6-digit number" }),
  factorId: primitiveSchemas.uuid,
});

/** The MFA verification input type. */
export type MfaVerificationInput = z.infer<typeof mfaVerificationInputSchema>;

/** The backup code schema. */
export const backupCodeSchema = z
  .string()
  .regex(/^[A-Z0-9]{6}-[A-Z0-9]{6}$/, { error: "Invalid backup code format" });

/** The backup code type. */
export type BackupCode = z.infer<typeof backupCodeSchema>;

/** The backup code list schema. */
export const backupCodeListSchema = z.strictObject({
  codes: z.array(backupCodeSchema),
  remaining: z.number().int().min(0),
});

/** The backup code list type. */
export type BackupCodeList = z.infer<typeof backupCodeListSchema>;

// ===== TOOL INPUT SCHEMAS =====

/** The backup code verify input schema. */
export const backupCodeVerifyInputSchema = z.strictObject({
  code: backupCodeSchema,
});

/** The backup code verify input type. */
export type BackupCodeVerifyInput = z.infer<typeof backupCodeVerifyInputSchema>;

/** The MFA challenge input schema. */
export const mfaChallengeInputSchema = z.strictObject({
  factorId: primitiveSchemas.uuid,
});

/** The MFA challenge input type. */
export type MfaChallengeInput = z.infer<typeof mfaChallengeInputSchema>;

/** The backup code regenerate input schema. */
export const backupCodeRegenerateInputSchema = z.strictObject({
  count: z.number().int().min(1).max(20).default(10),
});

/** The backup code regenerate input type. */
export type BackupCodeRegenerateInput = z.infer<typeof backupCodeRegenerateInputSchema>;

/** The MFA session revoke input schema. */
export const mfaSessionRevokeInputSchema = z.strictObject({
  scope: z.enum(["others", "global", "local"]).default("others"),
});

/** The MFA session revoke input type. */
export type MfaSessionRevokeInput = z.infer<typeof mfaSessionRevokeInputSchema>;
