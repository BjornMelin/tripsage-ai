/**
 * @fileoverview Server actions for authentication.
 */

"use server";

import "server-only";

import { loginFormSchema, registerFormSchema } from "@schemas/auth";
import { revalidatePath } from "next/cache";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { z } from "zod";
import { enforceRateLimit } from "@/lib/api/factory";
import { safeNextPath } from "@/lib/auth/redirect-server";
import { getTrustedRateLimitIdentifierFromHeaders } from "@/lib/ratelimit/identifier";
import type { RouteRateLimitKey } from "@/lib/ratelimit/routes";
import { type FieldErrors, zodErrorToFieldErrors } from "@/lib/result";
import {
  assertHumanOrThrow,
  isBotDetectedError,
  isBotIdEnabledForCurrentEnvironment,
} from "@/lib/security/botid";
import { createServerSupabase } from "@/lib/supabase/server";
import { createServerLogger } from "@/lib/telemetry/logger";
import { toAbsoluteUrl } from "@/lib/url/server-origin";
import { isMfaRequiredError } from "./supabase-errors";

const logger = createServerLogger("auth.actions");

async function enforceBotIdForAuthAction(
  actionName: string,
  requestHeaders?: Headers
): Promise<{ status: "error"; error: string } | null> {
  if (!isBotIdEnabledForCurrentEnvironment()) return null;
  try {
    const effectiveHeaders = requestHeaders ?? (await headers());
    await assertHumanOrThrow(actionName, {
      allowVerifiedAiAssistants: false,
      headers: effectiveHeaders,
    });
    return null;
  } catch (error) {
    if (isBotDetectedError(error)) {
      return { error: "Automated access is not allowed.", status: "error" };
    }
    logger.error("botid_check_failed", {
      actionName,
      error: error instanceof Error ? error.message : String(error ?? "unknown_error"),
    });
    return {
      error: "Security verification failed. Please try again.",
      status: "error",
    };
  }
}

async function enforceRateLimitForAuthAction(
  rateLimitKey: RouteRateLimitKey,
  requestHeaders?: Headers
): Promise<{ status: "error"; error: string } | null> {
  const effectiveHeaders = requestHeaders ?? (await headers());
  const ipHash = getTrustedRateLimitIdentifierFromHeaders(effectiveHeaders);
  const identifier = ipHash === "unknown" ? "ip:unknown" : `ip:${ipHash}`;

  const degradedMode =
    process.env.NODE_ENV === "development" ? "fail_open" : "fail_closed";
  const result = await enforceRateLimit(rateLimitKey, identifier, {
    degradedMode,
  });
  if (!result) return null;

  if (result.status === 429) {
    return { error: "Too many requests. Please try again later.", status: "error" };
  }

  logger.error("auth_rate_limit_unavailable", { rateLimitKey, status: result.status });
  return {
    error: "Service temporarily unavailable. Please try again.",
    status: "error",
  };
}

export type LoginActionState =
  | { status: "idle" }
  | {
      status: "error";
      error: string;
      fieldErrors?: FieldErrors;
    }
  | {
      status: "mfa_required";
      challengeId: string;
      factorId: string;
      nextPath: string;
    };

const mfaVerificationSchema = z.strictObject({
  challengeId: z.string().min(1, { error: "Challenge ID is required" }),
  code: z.string().regex(/^\d{6}$/, { error: "Enter a valid 6-digit code" }),
  factorId: z.string().min(1, { error: "Factor ID is required" }),
  next: z.string().optional(),
});

export type VerifyMfaActionState =
  | { status: "idle" }
  | { status: "error"; error: string; fieldErrors?: FieldErrors };

export type RegisterActionState =
  | { status: "idle" }
  | { status: "error"; error: string; fieldErrors?: FieldErrors };

function getFormString(formData: FormData, key: string): string | null {
  const value = formData.get(key);
  return typeof value === "string" ? value : null;
}

type MfaFactorCandidate = {
  id: string;
  factorType: string;
  status: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function getErrorDetails(err: unknown): { code?: string; status?: number } {
  if (!isRecord(err)) {
    return {};
  }

  const code = err.code;
  const status = err.status;

  return {
    code: typeof code === "string" ? code : undefined,
    status: typeof status === "number" ? status : undefined,
  };
}

function parseMfaFactorCandidate(value: unknown): MfaFactorCandidate | null {
  if (!isRecord(value)) {
    return null;
  }

  const id = value.id;
  const status = value.status;
  const factorType = value.factor_type;

  if (
    typeof id !== "string" ||
    typeof status !== "string" ||
    typeof factorType !== "string"
  ) {
    return null;
  }

  return { factorType, id, status };
}

function describeListFactorsData(value: unknown): Record<string, unknown> {
  if (Array.isArray(value)) {
    return { kind: "array", length: value.length };
  }

  if (isRecord(value)) {
    const keys = Object.keys(value);
    return {
      keys: keys.length > 0 ? keys.sort() : [],
      kind: "object",
      totpLength: Array.isArray(value.totp) ? value.totp.length : undefined,
    };
  }

  return { kind: typeof value };
}

function pickTotpFactorId(listFactorsData: unknown): string {
  const factorCandidates: MfaFactorCandidate[] = [];

  const pushCandidate = (candidate: unknown) => {
    const parsed = parseMfaFactorCandidate(candidate);
    if (parsed) {
      factorCandidates.push(parsed);
    }
  };

  if (Array.isArray(listFactorsData)) {
    listFactorsData.forEach(pushCandidate);
  } else if (isRecord(listFactorsData) && Array.isArray(listFactorsData.totp)) {
    listFactorsData.totp.forEach(pushCandidate);
  }

  const factor = factorCandidates.find(
    (entry) => entry.status === "verified" && entry.factorType === "totp"
  );

  if (!factor) {
    logger.warn("pickTotpFactorId: no verified totp factor found", {
      factorCandidates: factorCandidates.map((candidate) => ({
        factorType: candidate.factorType,
        status: candidate.status,
      })),
      listFactorsData: describeListFactorsData(listFactorsData),
    });

    if (factorCandidates.length === 0) {
      throw new Error("No MFA factors configured for this account");
    }

    throw new Error("No verified TOTP MFA factor found for this account");
  }

  return factor.id;
}

/**
 * Authenticates a user with email/password and redirects to the requested page.
 *
 * Uses Supabase SSR client so the session is stored in HTTP-only cookies.
 * When the account has a verified MFA factor, returns a challenge request
 * so the client can prompt for a TOTP code.
 */
export async function loginWithPasswordAction(
  _prevState: LoginActionState,
  formData: FormData
): Promise<LoginActionState | never> {
  const requestHeaders = await headers();

  const [rateLimitResult, botIdResult] = await Promise.all([
    enforceRateLimitForAuthAction("auth:login", requestHeaders),
    enforceBotIdForAuthAction("auth.login.action", requestHeaders),
  ]);
  if (rateLimitResult) return rateLimitResult;
  if (botIdResult) return botIdResult;

  const nextPath = safeNextPath(getFormString(formData, "next"));

  const parsed = loginFormSchema.safeParse({
    email: getFormString(formData, "email"),
    password: getFormString(formData, "password"),
    rememberMe: undefined,
  });

  if (!parsed.success) {
    return {
      error: "Invalid login details",
      fieldErrors: zodErrorToFieldErrors(parsed.error),
      status: "error",
    };
  }

  const supabase = await createServerSupabase();

  const { error: signInError } = await supabase.auth.signInWithPassword({
    email: parsed.data.email,
    password: parsed.data.password,
  });

  const mfaRequiredByError = signInError ? isMfaRequiredError(signInError) : false;
  if (signInError && !mfaRequiredByError) {
    return {
      error: signInError.message || "Login failed",
      status: "error",
    };
  }

  let aalData:
    | { currentLevel?: string | null; nextLevel?: string | null }
    | null
    | undefined;
  if (!mfaRequiredByError) {
    try {
      const aal = await supabase.auth.mfa.getAuthenticatorAssuranceLevel();
      if (aal.error) {
        const errorDetails = getErrorDetails(aal.error);
        logger.warn("AAL check failed during login", {
          error: aal.error.message,
          errorCode: errorDetails.code,
          status: errorDetails.status,
        });
      } else {
        aalData = aal.data;
      }
    } catch (error) {
      logger.error("AAL check threw during login", {
        error:
          error instanceof Error ? error.message : String(error ?? "unknown_error"),
      });
    }
  }

  const needsMfa =
    mfaRequiredByError ||
    (aalData?.nextLevel === "aal2" && aalData?.currentLevel !== "aal2");
  if (needsMfa) {
    const factors = await supabase.auth.mfa.listFactors();
    if (factors.error) {
      return {
        error: factors.error.message || "Unable to list MFA factors",
        status: "error",
      };
    }

    const factorData = factors.data;
    if (!factorData) {
      return {
        error: "MFA required but factors are unavailable",
        status: "error",
      };
    }

    let factorId: string;
    try {
      factorId = pickTotpFactorId(factorData);
    } catch (error) {
      return {
        error: error instanceof Error ? error.message : "MFA required but unavailable",
        status: "error",
      };
    }

    const challenge = await supabase.auth.mfa.challenge({ factorId });
    const challengeId = challenge.data?.id;
    if (challenge.error || !challengeId) {
      return {
        error: challenge.error?.message ?? "Failed to start MFA challenge",
        status: "error",
      };
    }

    return {
      challengeId,
      factorId,
      nextPath,
      status: "mfa_required",
    };
  }

  redirect(nextPath);
}

/**
 * Verifies a user-provided TOTP code and redirects to the requested page.
 */
export async function verifyMfaAction(
  _prevState: VerifyMfaActionState,
  formData: FormData
): Promise<VerifyMfaActionState | never> {
  const requestHeaders = await headers();

  const [rateLimitResult, botIdResult] = await Promise.all([
    enforceRateLimitForAuthAction("auth:mfa:verify", requestHeaders),
    enforceBotIdForAuthAction("auth.mfa.verify.action", requestHeaders),
  ]);
  if (rateLimitResult) return rateLimitResult;
  if (botIdResult) return botIdResult;

  const parsed = mfaVerificationSchema.safeParse({
    challengeId: getFormString(formData, "challengeId"),
    code: getFormString(formData, "code"),
    factorId: getFormString(formData, "factorId"),
    next: getFormString(formData, "next") ?? undefined,
  });

  if (!parsed.success) {
    return {
      error: "Invalid verification details",
      fieldErrors: zodErrorToFieldErrors(parsed.error),
      status: "error",
    };
  }

  const nextPath = safeNextPath(parsed.data.next);

  const supabase = await createServerSupabase();
  const result = await supabase.auth.mfa.verify({
    challengeId: parsed.data.challengeId,
    code: parsed.data.code,
    factorId: parsed.data.factorId,
  });

  if (result.error) {
    return {
      error: result.error.message ?? "Invalid or expired MFA code",
      status: "error",
    };
  }

  redirect(nextPath);
}

/**
 * Creates a new user account and redirects to either a check-email screen or the dashboard.
 */
export async function registerWithPasswordAction(
  _prevState: RegisterActionState,
  formData: FormData
): Promise<RegisterActionState | never> {
  const requestHeaders = await headers();

  const [rateLimitResult, botIdResult] = await Promise.all([
    enforceRateLimitForAuthAction("auth:register", requestHeaders),
    enforceBotIdForAuthAction("auth.register.action", requestHeaders),
  ]);
  if (rateLimitResult) return rateLimitResult;
  if (botIdResult) return botIdResult;

  const nextParam = getFormString(formData, "next");
  const nextPath = safeNextPath(nextParam);

  const parsed = registerFormSchema.safeParse({
    acceptTerms: getFormString(formData, "acceptTerms") === "on",
    confirmPassword: getFormString(formData, "confirmPassword"),
    email: getFormString(formData, "email"),
    firstName: getFormString(formData, "firstName"),
    lastName: getFormString(formData, "lastName"),
    marketingOptIn: getFormString(formData, "marketingOptIn") === "on",
    password: getFormString(formData, "password"),
  });

  if (!parsed.success) {
    return {
      error: "Invalid registration details",
      fieldErrors: zodErrorToFieldErrors(parsed.error),
      status: "error",
    };
  }

  const supabase = await createServerSupabase();

  const emailRedirectTo = `${toAbsoluteUrl("/auth/confirm")}?next=${encodeURIComponent(
    nextPath
  )}`;

  const userMetadata: Record<string, string | boolean> = {
    email: parsed.data.email,
  };
  const firstName = parsed.data.firstName.trim();
  const lastName = parsed.data.lastName.trim();
  userMetadata.first_name = firstName;
  userMetadata.full_name = [firstName, lastName]
    .filter((part) => part.length > 0)
    .join(" ");
  userMetadata.last_name = lastName;
  userMetadata.marketing_opt_in = Boolean(parsed.data.marketingOptIn);
  userMetadata.terms_accepted = true;

  const { data, error } = await supabase.auth.signUp({
    email: parsed.data.email,
    options: {
      data: userMetadata,
      emailRedirectTo,
    },
    password: parsed.data.password,
  });

  if (error) {
    return {
      error: error.message || "Registration failed",
      status: "error",
    };
  }

  if (!data.session) {
    redirect("/register?status=check_email");
  }

  redirect(nextPath);
}

/**
 * Signs the user out and redirects to the login page.
 */
export async function logoutAction(): Promise<never> {
  const supabase = await createServerSupabase();
  try {
    await supabase.auth.signOut();
  } catch (error) {
    logger.error("Logout error", {
      error: error instanceof Error ? error.message : String(error ?? "unknown_error"),
    });
  }
  revalidatePath("/");
  redirect("/login");
}
