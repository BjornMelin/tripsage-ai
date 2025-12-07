/**
 * @fileoverview Supabase MFA service helpers (TOTP + backup codes).
 */

import "server-only";

import { createHash } from "node:crypto";

import {
  type BackupCodeList,
  backupCodeRegenerateInputSchema,
  backupCodeSchema,
  backupCodeVerifyInputSchema,
  type MfaEnrollment,
  type MfaFactor,
  type MfaVerificationInput,
  mfaChallengeInputSchema,
  mfaEnrollmentSchema,
  mfaFactorSchema,
  mfaVerificationInputSchema,
} from "@schemas/mfa";
import type { SupabaseClient } from "@supabase/supabase-js";
import { getServerEnv } from "@/lib/env/server";
import { incrCounter } from "@/lib/redis";
import { nowIso, secureId } from "@/lib/security/random";
import { getAdminSupabase, type TypedAdminSupabase } from "@/lib/supabase/admin";
import type { Database } from "@/lib/supabase/database.types";
import { createServerLogger } from "@/lib/telemetry/logger";
import { withTelemetrySpan } from "@/lib/telemetry/span";

type TypedSupabase = SupabaseClient<Database>;
type BackupAuditMeta = { ip?: string; userAgent?: string };

const auditLogger = createServerLogger("security.mfa.audit");

/** A custom error class for invalid backup codes. */
export class InvalidBackupCodeError extends Error {
  constructor(message = "invalid_backup_code") {
    super(message);
    this.name = "InvalidBackupCodeError";
  }
}

/** A custom error class for user lookup errors. */
class UserLookupError extends Error {
  constructor(message = "user_not_found") {
    super(message);
    this.name = "UserLookupError";
  }
}

/** A custom error class for AAL2 enforcement failures. */
export class MfaRequiredError extends Error {
  /** Stable machine-readable error code for step-up MFA requirements. */
  readonly code = "MFA_REQUIRED" as const;

  constructor(message = "mfa_required") {
    super(message);
    this.name = "MfaRequiredError";
  }
}

/** Indicates a client-visible TOTP validation failure (bad/expired code). */
export class InvalidTotpError extends Error {
  readonly code = "invalid_or_expired_code" as const;

  constructor(message = "invalid_or_expired_code") {
    super(message);
    this.name = "InvalidTotpError";
  }
}

/** Indicates an internal failure verifying TOTP (DB/network). */
export class TotpVerificationInternalError extends Error {
  readonly code: string;
  readonly status = 500;

  constructor(message = "mfa_verify_failed") {
    super(message);
    this.name = "TotpVerificationInternalError";
    this.code = message;
  }
}

/** The cache of the backup code pepper. */
let backupCodePepperCache: string | null = null;

/** Resets the backup code pepper for testing. */
export function resetBackupCodePepperForTest() {
  backupCodePepperCache = null;
}

/** Gets the backup code pepper. */
function getBackupCodePepper(): string {
  if (backupCodePepperCache) {
    return backupCodePepperCache;
  }
  const env = getServerEnv();
  const value = env.MFA_BACKUP_CODE_PEPPER ?? env.SUPABASE_JWT_SECRET;
  if (!env.MFA_BACKUP_CODE_PEPPER && env.SUPABASE_JWT_SECRET) {
    auditLogger.warn(
      "MFA_BACKUP_CODE_PEPPER not set; falling back to SUPABASE_JWT_SECRET. Rotating the JWT secret will invalidate existing backup codes."
    );
  }
  if (!value || value.trim().length < 16) {
    throw new Error(
      "MFA_BACKUP_CODE_PEPPER must be set to a non-empty secret (>=16 chars) or SUPABASE_JWT_SECRET must be provided as fallback"
    );
  }
  backupCodePepperCache = value.trim();
  return backupCodePepperCache;
}

/** Validates MFA configuration; throws if required secrets are missing. */
export function validateMfaConfig(): void {
  getBackupCodePepper();
}

/**
 * Gets the authenticated user ID.
 *
 * @param supabase - The Supabase client.
 * @returns The authenticated user ID.
 */
async function getAuthenticatedUserId(supabase: TypedSupabase): Promise<string> {
  const { data, error } = await supabase.auth.getUser();
  if (error || !data?.user?.id) {
    throw new UserLookupError(error?.message ?? "user_not_found");
  }
  return data.user.id;
}

/**
 * Generates a list of backup codes.
 *
 * @param count - The number of backup codes to generate.
 * @returns A list of backup codes.
 */
function generateBackupCodes(count: number): string[] {
  return Array.from({ length: count }, () => {
    const raw = secureId(12).toUpperCase();
    return `${raw.slice(0, 6)}-${raw.slice(6, 12)}`;
  });
}

/**
 * Starts a TOTP enrollment.
 *
 * @param supabase - The Supabase client.
 * @returns The enrollment result.
 */
export async function startTotpEnrollment(
  supabase: TypedSupabase,
  deps?: { adminSupabase?: TypedAdminSupabase }
): Promise<MfaEnrollment> {
  return await withTelemetrySpan(
    "mfa.start_enrollment",
    { attributes: { factor: "totp", feature: "mfa" } },
    async (span) => {
      const now = new Date();
      const expiresAt = new Date(now.getTime() + 15 * 60 * 1000);
      const ttlSeconds = Math.max(
        0,
        Math.floor((expiresAt.getTime() - now.getTime()) / 1000)
      );

      const userId = await getAuthenticatedUserId(supabase).catch((error) => {
        span.recordException(error as Error);
        throw error;
      });

      const enrollResult = await supabase.auth.mfa.enroll({ factorType: "totp" });
      if (enrollResult.error || !enrollResult.data?.id || !enrollResult.data.totp) {
        throw new Error(enrollResult.error?.message ?? "mfa_enroll_failed");
      }

      const challenge = await supabase.auth.mfa.challenge({
        factorId: enrollResult.data.id,
      });
      if (challenge.error || !challenge.data?.id) {
        throw new Error(challenge.error?.message ?? "mfa_challenge_failed");
      }

      const payload = {
        challengeId: challenge.data.id,
        expiresAt: expiresAt.toISOString(),
        factorId: enrollResult.data.id,
        issuedAt: now.toISOString(),
        qrCode: enrollResult.data.totp.qr_code ?? "",
        ttlSeconds,
        uri: enrollResult.data.totp.uri ?? undefined,
      };
      const parsed = mfaEnrollmentSchema.parse(payload);
      const adminSupabase = deps?.adminSupabase ?? getAdminSupabase();
      const { error: expireError } = await adminSupabase
        .from("mfa_enrollments")
        .update({ status: "expired" })
        .eq("user_id", userId)
        .eq("status", "pending")
        .lt("expires_at", nowIso());
      if (expireError) {
        span.recordException(expireError);
        throw new Error(expireError.message ?? "mfa_enrollment_expire_failed");
      }

      const { error: insertError } = await adminSupabase
        .from("mfa_enrollments")
        .insert({
          // biome-ignore lint/style/useNamingConvention: snake_case columns
          challenge_id: parsed.challengeId,
          // biome-ignore lint/style/useNamingConvention: snake_case columns
          expires_at: parsed.expiresAt,
          // biome-ignore lint/style/useNamingConvention: snake_case columns
          factor_id: parsed.factorId,
          // biome-ignore lint/style/useNamingConvention: snake_case columns
          issued_at: parsed.issuedAt,
          status: "pending",
          // biome-ignore lint/style/useNamingConvention: snake_case columns
          user_id: userId,
        });
      if (insertError) {
        span.recordException(insertError);
        throw new Error(insertError.message ?? "mfa_enrollment_store_failed");
      }

      return parsed;
    }
  );
}

/**
 * Challenges a TOTP factor.
 *
 * @param supabase - The Supabase client.
 * @param input - The input to challenge the TOTP factor.
 * @returns The challenge result.
 */
export async function challengeTotp(
  supabase: TypedSupabase,
  input: { factorId: string }
): Promise<{ challengeId: string }> {
  const parsed = mfaChallengeInputSchema.parse(input);
  return await withTelemetrySpan(
    "mfa.challenge",
    { attributes: { factor: "totp", factorId: parsed.factorId, feature: "mfa" } },
    async (span) => {
      const challenge = await supabase.auth.mfa.challenge({
        factorId: parsed.factorId,
      });
      if (challenge.error || !challenge.data?.id) {
        span.recordException(challenge.error ?? new Error("challenge_failed"));
        throw new Error(challenge.error?.message ?? "mfa_challenge_failed");
      }
      return { challengeId: challenge.data.id };
    }
  );
}

/** Result of TOTP verification indicating enrollment state. */
export interface TotpVerificationResult {
  /** True if this verification consumed an initial enrollment (first-time setup). */
  isInitialEnrollment: boolean;
}

/**
 * Verifies a TOTP code.
 *
 * Handles both initial enrollment verification (pending enrollment exists) and
 * ongoing MFA challenge verification (no enrollment). Backup codes should only
 * be generated when `isInitialEnrollment` is true.
 *
 * @param supabase - The Supabase client.
 * @param input - The input to verify the TOTP code.
 * @returns Verification result with enrollment state.
 */
export async function verifyTotp(
  supabase: TypedSupabase,
  input: MfaVerificationInput,
  deps?: { adminSupabase?: TypedAdminSupabase }
): Promise<TotpVerificationResult> {
  const parsed = mfaVerificationInputSchema.parse(input);
  return await withTelemetrySpan(
    "mfa.verify_totp",
    {
      attributes: {
        factor: "totp",
        factorId: parsed.factorId,
        feature: "mfa",
      },
      redactKeys: ["factorId", "code"],
    },
    async (span) => {
      const adminSupabase = deps?.adminSupabase ?? getAdminSupabase();

      // Check for pending enrollment (initial setup flow)
      const { data: pendingEnrollment, error: enrollmentError } = await supabase
        .from("mfa_enrollments")
        .select("expires_at,status")
        .eq("factor_id", parsed.factorId)
        .eq("challenge_id", parsed.challengeId)
        .order("issued_at", { ascending: false })
        .limit(1)
        .maybeSingle();

      if (enrollmentError) {
        span.recordException(enrollmentError);
        throw new TotpVerificationInternalError(
          enrollmentError.message ?? "mfa_enrollment_lookup_failed"
        );
      }

      const isInitialEnrollment =
        pendingEnrollment !== null && pendingEnrollment.status === "pending";

      // If this is initial enrollment, validate expiration
      if (isInitialEnrollment) {
        if (new Date(pendingEnrollment.expires_at).getTime() < Date.now()) {
          const { error: expireError } = await adminSupabase
            .from("mfa_enrollments")
            .update({ status: "expired" })
            .eq("challenge_id", parsed.challengeId)
            .eq("factor_id", parsed.factorId);
          if (expireError) {
            span.recordException(expireError);
            throw new TotpVerificationInternalError(
              expireError.message ?? "mfa_enrollment_expire_failed"
            );
          }
          throw new InvalidTotpError("mfa_enrollment_expired");
        }
      }

      // Verify TOTP code with Supabase Auth (works for both enrollment and challenges)
      const result = await supabase.auth.mfa.verify({
        challengeId: parsed.challengeId,
        code: parsed.code,
        factorId: parsed.factorId,
      });
      if (result.error) {
        span.recordException(result.error);
        if (result.error.status && result.error.status >= 500) {
          throw new TotpVerificationInternalError(
            result.error.message ?? "mfa_verify_failed"
          );
        }
        throw new InvalidTotpError("invalid_or_expired_code");
      }

      // Mark enrollment consumed if this was initial enrollment
      if (isInitialEnrollment) {
        const userId = await getAuthenticatedUserId(supabase);
        const { error: consumeError } = await adminSupabase
          .from("mfa_enrollments")
          .update({
            // biome-ignore lint/style/useNamingConvention: snake_case columns
            consumed_at: nowIso(),
            status: "consumed",
          })
          .eq("user_id", userId)
          .eq("factor_id", parsed.factorId)
          .eq("challenge_id", parsed.challengeId)
          .eq("status", "pending");
        if (consumeError) {
          span.recordException(consumeError);
          throw new TotpVerificationInternalError(
            consumeError.message ?? "mfa_enrollment_update_failed"
          );
        }
      }

      return { isInitialEnrollment };
    }
  );
}

/**
 * Lists the factors for a user.
 *
 * @param supabase - The Supabase client.
 * @returns The list of factors.
 */
export async function listFactors(supabase: TypedSupabase): Promise<MfaFactor[]> {
  return await withTelemetrySpan(
    "mfa.list_factors",
    { attributes: { feature: "mfa" } },
    async () => {
      const { data, error } = await supabase.auth.mfa.listFactors();
      if (error) throw new Error(error.message);
      const factors = [
        ...(data?.totp ?? []),
        ...(data?.phone ?? []),
        ...(data?.webauthn ?? []),
      ].map((f) => ({
        friendlyName: f.friendly_name ?? undefined,
        id: f.id,
        status: f.status as MfaFactor["status"],
        type: f.factor_type as MfaFactor["type"],
      }));
      return mfaFactorSchema.array().parse(factors);
    }
  );
}

/**
 * Unenrolls a factor.
 *
 * @param supabase - The Supabase client.
 * @param factorId - The ID of the factor to unenroll.
 * @returns The unenrollment result.
 */
export async function unenrollFactor(
  supabase: TypedSupabase,
  factorId: string
): Promise<void> {
  const validatedFactorId = mfaChallengeInputSchema.pick({ factorId: true }).parse({
    factorId,
  }).factorId;
  await withTelemetrySpan(
    "mfa.unenroll",
    {
      attributes: { factorId: validatedFactorId, feature: "mfa" },
      redactKeys: ["factorId"],
    },
    async (span) => {
      const { error } = await supabase.auth.mfa.unenroll({
        factorId: validatedFactorId,
      });
      if (error) {
        span.recordException(error);
        throw new Error(error.message ?? "mfa_unenroll_failed");
      }
    }
  );
}

/**
 * Creates backup codes.
 *
 * @param adminSupabase - The Admin Supabase client.
 * @param userId - The ID of the user to create backup codes for.
 * @param count - The number of backup codes to create.
 * @returns The backup codes.
 */
export async function createBackupCodes(
  adminSupabase: TypedAdminSupabase,
  userId: string,
  count = 10,
  meta: BackupAuditMeta = {}
): Promise<BackupCodeList> {
  return await withTelemetrySpan(
    "mfa.backup_codes.generate",
    { attributes: { feature: "mfa", userId }, redactKeys: ["userId"] },
    async (span) => {
      const codes = generateBackupCodes(count);
      const rows = codes.map((code) => ({
        // biome-ignore lint/style/useNamingConvention: DB column naming
        code_hash: hashBackupCode(backupCodeSchema.parse(code)),
        // biome-ignore lint/style/useNamingConvention: DB column naming
        user_id: userId,
      }));

      const adminClient = adminSupabase as unknown as SupabaseClient<Database>;
      const { data, error } = await adminClient.rpc(
        "replace_backup_codes" as never,
        {
          // biome-ignore lint/style/useNamingConvention: RPC parameters must match SQL function names
          p_code_hashes: rows.map((row) => row.code_hash),
          // biome-ignore lint/style/useNamingConvention: RPC parameters must match SQL function names
          p_user_id: userId,
        } as never
      );

      if (error) {
        span.recordException(error);
        throw new Error(error.message ?? "backup_codes_store_failed");
      }

      const remaining = typeof data === "number" ? data : rows.length;

      await logBackupCodeAudit(adminSupabase, userId, "regenerated", remaining, meta);

      return { codes, remaining };
    }
  );
}

/**
 * Verifies a backup code.
 *
 * @param adminSupabase - The Admin Supabase client.
 * @param userId - The ID of the user to verify the backup code for.
 * @param code - The code to verify.
 * @returns The verification result.
 */
export async function verifyBackupCode(
  adminSupabase: TypedAdminSupabase,
  userId: string,
  code: string,
  meta: BackupAuditMeta = {}
): Promise<BackupCodeList> {
  const parsed = backupCodeVerifyInputSchema.safeParse({ code });
  if (!parsed.success) {
    throw new InvalidBackupCodeError("invalid_backup_code");
  }
  const parsedCode = parsed.data.code;
  return await withTelemetrySpan(
    "mfa.backup_codes.verify",
    { attributes: { feature: "mfa", userId }, redactKeys: ["userId"] },
    async (span) => {
      const hashedInput = hashBackupCode(parsedCode);
      const table = adminSupabase.from("auth_backup_codes");
      const { data, error } = await table
        .select("id")
        .eq("user_id", userId)
        .eq("code_hash", hashedInput)
        .is("consumed_at", null)
        .maybeSingle();

      if (error) {
        span.recordException(error);
        throw new Error(error.message ?? "backup_codes_lookup_failed");
      }
      if (!data) {
        throw new InvalidBackupCodeError("invalid_backup_code");
      }

      const { data: updatedRows, error: updateError } = await table
        // biome-ignore lint/style/useNamingConvention: DB column naming
        .update({ consumed_at: nowIso() })
        .eq("id", data.id)
        .is("consumed_at", null)
        .select("id");
      if (updateError) {
        span.recordException(updateError);
        throw new Error(updateError.message ?? "backup_code_consume_failed");
      }
      const updatedCount = updatedRows?.length ?? 0;
      if (!updatedCount || updatedCount === 0) {
        throw new InvalidBackupCodeError("backup_code_already_consumed");
      }

      const { count } = await table
        .select("id", { count: "exact", head: true })
        .eq("user_id", userId)
        .is("consumed_at", null);

      await logBackupCodeAudit(adminSupabase, userId, "consumed", 1, meta);

      return { codes: [], remaining: count ?? 0 };
    }
  );
}

/**
 * Refreshes the AAL for a user.
 *
 * @param supabase - The Supabase client.
 * @returns The AAL.
 */
export async function refreshAal(supabase: TypedSupabase): Promise<"aal1" | "aal2"> {
  return await withTelemetrySpan(
    "mfa.refresh_aal",
    { attributes: { feature: "mfa" } },
    async (span) => {
      const { data, error } = await supabase.auth.mfa.getAuthenticatorAssuranceLevel();
      if (error) {
        span.recordException(error);
        throw new Error(error.message ?? "aal_check_failed");
      }
      return (data?.currentLevel as "aal1" | "aal2" | null) ?? "aal1";
    }
  );
}

export async function requireAal2(supabase: TypedSupabase): Promise<void> {
  const level = await refreshAal(supabase);
  if (level !== "aal2") {
    throw new MfaRequiredError();
  }
}

/**
 * Regenerates backup codes.
 *
 * @param adminSupabase - The Admin Supabase client.
 * @param userId - The ID of the user to regenerate backup codes for.
 * @param count - The number of backup codes to regenerate.
 * @returns The regenerated backup codes.
 */
export async function regenerateBackupCodes(
  adminSupabase: TypedAdminSupabase,
  userId: string,
  count: number,
  meta: BackupAuditMeta = {}
): Promise<BackupCodeList> {
  const parsed = backupCodeRegenerateInputSchema.parse({ count });
  return await createBackupCodes(adminSupabase, userId, parsed.count, meta);
}

/**
 * Revokes sessions.
 *
 * @param supabase - The Supabase client.
 * @param scope - The scope of the sessions to revoke.
 * @returns The revocation result.
 */
export async function revokeSessions(
  supabase: TypedSupabase,
  scope: "others" | "global" | "local" = "others"
): Promise<void> {
  await withTelemetrySpan(
    "mfa.sessions.revoke",
    { attributes: { feature: "mfa", scope } },
    async (span) => {
      const { error } = await supabase.auth.signOut({ scope });
      if (error) {
        span.recordException(error);
        throw new Error(error.message ?? "session_revoke_failed");
      }
    }
  );
}

async function logBackupCodeAudit(
  adminSupabase: TypedAdminSupabase,
  userId: string,
  event: "regenerated" | "consumed",
  count: number,
  meta: BackupAuditMeta
) {
  const adminClient = adminSupabase as unknown as SupabaseClient<Database>;
  const { error } = await adminClient.from("mfa_backup_code_audit" as never).insert({
    count,
    event,
    ip: meta.ip,
    // biome-ignore lint/style/useNamingConvention: DB column naming
    user_agent: meta.userAgent,
    // biome-ignore lint/style/useNamingConvention: DB column naming
    user_id: userId,
  } as never);
  if (error) {
    auditLogger.error("mfa backup code audit insert failed", {
      error: error.message,
      event,
      userId,
    });
    await Promise.allSettled([
      incrCounter("metrics:mfa_backup_code_audit_failure"),
      incrCounter(`metrics:mfa_backup_code_audit_failure:event:${event}`),
      incrCounter(`metrics:mfa_backup_code_audit_failure:user:${userId}`, 3600),
    ]);
    return;
  }
}

/**
 * Hashes a backup code.
 *
 * @param code - The code to hash.
 * @returns The hashed code.
 */
function hashBackupCode(code: string): string {
  const normalized = code.trim().toUpperCase();
  const pepper = getBackupCodePepper();
  // Lightweight pepper to avoid plain deterministic hash reuse
  return createHash("sha256").update(`${pepper}:${normalized}`, "utf8").digest("hex");
}

if (process.env.NODE_ENV !== "test") {
  validateMfaConfig();
}
