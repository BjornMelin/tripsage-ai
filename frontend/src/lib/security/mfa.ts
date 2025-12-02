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
import { secureId } from "@/lib/security/random";
import type { TypedAdminSupabase } from "@/lib/supabase/admin";
import { withTelemetrySpan } from "@/lib/telemetry/span";

type TypedSupabase = SupabaseClient;

const BACKUP_CODE_PEPPER = "mfa-backup-code";

/**
 * Generates a list of backup codes.
 *
 * @param count - The number of backup codes to generate.
 * @returns A list of backup codes.
 */
function generateBackupCodes(count: number): string[] {
  return Array.from({ length: count }, () => {
    const raw = secureId(12).toUpperCase();
    return `${raw.slice(0, 5)}-${raw.slice(5, 10)}`;
  });
}

/**
 * Starts a TOTP enrollment.
 *
 * @param supabase - The Supabase client.
 * @returns The enrollment result.
 */
export async function startTotpEnrollment(
  supabase: TypedSupabase
): Promise<MfaEnrollment> {
  return await withTelemetrySpan(
    "mfa.start_enrollment",
    { attributes: { factor: "totp", feature: "mfa" } },
    async () => {
      const now = new Date();
      const expiresAt = new Date(now.getTime() + 15 * 60 * 1000);
      const ttlSeconds = Math.max(
        0,
        Math.floor((expiresAt.getTime() - now.getTime()) / 1000)
      );

      const { data: authUser } = await supabase.auth.getUser();
      const enrollResult = await supabase.auth.mfa.enroll({ factorType: "totp" });
      if (enrollResult.error || !enrollResult.data?.id || !enrollResult.data.totp) {
        throw new Error(enrollResult.error?.message ?? "mfa_enroll_failed");
      }
      const userId = authUser.user?.id ?? null;

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

      if (userId) {
        await supabase
          .from("mfa_enrollments")
          .update({ status: "expired" })
          .eq("user_id", userId)
          .eq("status", "pending")
          .lt("expires_at", now.toISOString());

        await supabase.from("mfa_enrollments").insert({
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

/**
 * Verifies a TOTP code.
 *
 * @param supabase - The Supabase client.
 * @param input - The input to verify the TOTP code.
 * @returns The verification result.
 */
export async function verifyTotp(
  supabase: TypedSupabase,
  input: MfaVerificationInput
): Promise<void> {
  const parsed = mfaVerificationInputSchema.parse(input);
  await withTelemetrySpan(
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
        throw new Error(enrollmentError.message ?? "mfa_enrollment_lookup_failed");
      }

      if (!pendingEnrollment || pendingEnrollment.status !== "pending") {
        throw new Error("mfa_enrollment_not_found");
      }

      if (new Date(pendingEnrollment.expires_at).getTime() < Date.now()) {
        await supabase
          .from("mfa_enrollments")
          .update({ status: "expired" })
          .eq("challenge_id", parsed.challengeId)
          .eq("factor_id", parsed.factorId);
        throw new Error("mfa_enrollment_expired");
      }

      const result = await supabase.auth.mfa.verify({
        challengeId: parsed.challengeId,
        code: parsed.code,
        factorId: parsed.factorId,
      });
      if (result.error) {
        span.recordException(result.error);
        throw new Error(result.error.message ?? "mfa_verify_failed");
      }

      // Mark enrollment consumed if present
      const { data: userData } = await supabase.auth.getUser();
      const userId = userData.user?.id;
      if (userId) {
        await supabase
          .from("mfa_enrollments")
          .update({
            // biome-ignore lint/style/useNamingConvention: snake_case columns
            consumed_at: new Date().toISOString(),
            status: "consumed",
          })
          .eq("user_id", userId)
          .eq("factor_id", parsed.factorId)
          .eq("challenge_id", parsed.challengeId)
          .eq("status", "pending");
      }
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
  await withTelemetrySpan(
    "mfa.unenroll",
    { attributes: { factorId, feature: "mfa" }, redactKeys: ["factorId"] },
    async (span) => {
      const { error } = await supabase.auth.mfa.unenroll({ factorId });
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
  count = 10
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

      const table = adminSupabase.from("auth_backup_codes");

      const { error: deleteError } = await table.delete().eq("user_id", userId);
      if (deleteError) {
        span.recordException(deleteError);
        throw new Error(deleteError.message ?? "backup_codes_cleanup_failed");
      }

      const { error } = await table.insert(rows);
      if (error) {
        span.recordException(error);
        throw new Error(error.message ?? "backup_codes_store_failed");
      }

      return { codes, remaining: rows.length };
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
  code: string
): Promise<BackupCodeList> {
  const parsedCode = backupCodeVerifyInputSchema.parse({ code }).code;
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
        throw new Error("invalid_backup_code");
      }

      const { error: updateError } = await table
        // biome-ignore lint/style/useNamingConvention: DB column naming
        .update({ consumed_at: new Date().toISOString() })
        .eq("id", data.id);
      if (updateError) {
        span.recordException(updateError);
        throw new Error(updateError.message ?? "backup_code_consume_failed");
      }

      const { count } = await table
        .select("id", { count: "exact", head: true })
        .eq("user_id", userId)
        .is("consumed_at", null);

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
  count: number
): Promise<BackupCodeList> {
  const parsed = backupCodeRegenerateInputSchema.parse({ count });
  return await createBackupCodes(adminSupabase, userId, parsed.count);
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

/**
 * Hashes a backup code.
 *
 * @param code - The code to hash.
 * @returns The hashed code.
 */
function hashBackupCode(code: string): string {
  const normalized = code.trim().toUpperCase();
  // Lightweight pepper to avoid plain deterministic hash reuse
  return createHash("sha256")
    .update(`${BACKUP_CODE_PEPPER}:${normalized}`, "utf8")
    .digest("hex");
}
