/**
 * @fileoverview Security domain schemas for security dashboard APIs.
 */

import { z } from "zod";

// ===== CORE SCHEMAS =====

/** Zod schema for security event. */
export const securityEventSchema = z.strictObject({
  description: z.string(),
  device: z.string().optional(),
  id: z.string(),
  ipAddress: z.string(),
  location: z.string().optional(),
  riskLevel: z.enum(["low", "medium", "high"]),
  timestamp: z.string(),
  type: z.enum([
    "login_success",
    "login_failure",
    "logout",
    "password_change",
    "mfa_enabled",
    "suspicious_activity",
  ]),
});

/** Type for security event. */
export type SecurityEvent = z.infer<typeof securityEventSchema>;

/** Zod schema for active session. */
export const activeSessionSchema = z.strictObject({
  browser: z.string(),
  device: z.string(),
  id: z.string(),
  ipAddress: z.string(),
  isCurrent: z.boolean(),
  lastActivity: z.string(),
  location: z.string(),
});

/** Type for active session. */
export type ActiveSession = z.infer<typeof activeSessionSchema>;

/** Zod schema for security metrics. */
export const securityMetricsSchema = z.strictObject({
  activeSessions: z.number().int(),
  failedLoginAttempts: z.number().int(),
  lastLogin: z.string(),
  oauthConnections: z.array(z.string()),
  securityScore: z.number().int(),
  trustedDevices: z.number().int(),
});

/** Type for security metrics. */
export type SecurityMetrics = z.infer<typeof securityMetricsSchema>;
