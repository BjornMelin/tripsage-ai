/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  loginWithPasswordAction,
  logoutAction,
  registerWithPasswordAction,
  verifyMfaAction,
} from "../actions";

vi.mock("server-only", () => ({}));

vi.mock("botid/server", async () => {
  const { mockBotIdHumanResponse } = await import("@/test/mocks/botid");
  return {
    checkBotId: vi.fn(async () => mockBotIdHumanResponse),
  };
});

const enforceRateLimitMock = vi.hoisted(() => vi.fn(async () => null));

vi.mock("@/lib/api/factory", () => ({
  enforceRateLimit: enforceRateLimitMock,
}));

vi.mock("next/headers", () => ({
  headers: vi.fn(async () => new Headers({ "x-real-ip": "203.0.113.10" })),
}));

// Mock dependencies (hoisted for vi.mock)
const {
  loggerErrorMock,
  loggerWarnMock,
  mockChallenge,
  mockGetAuthenticatorAssuranceLevel,
  mockListFactors,
  mockSignInWithPassword,
  mockSignOut,
  mockSignUp,
  mockSupabase,
  mockVerifyMfa,
} = vi.hoisted(() => {
  const signInWithPassword = vi.fn();
  const signOut = vi.fn();
  const signUp = vi.fn();
  const challenge = vi.fn();
  const getAuthenticatorAssuranceLevel = vi.fn();
  const listFactors = vi.fn();
  const verify = vi.fn();
  const warn = vi.fn();
  const error = vi.fn();
  return {
    loggerErrorMock: error,
    loggerWarnMock: warn,
    mockChallenge: challenge,
    mockGetAuthenticatorAssuranceLevel: getAuthenticatorAssuranceLevel,
    mockListFactors: listFactors,
    mockSignInWithPassword: signInWithPassword,
    mockSignOut: signOut,
    mockSignUp: signUp,
    mockSupabase: {
      auth: {
        mfa: {
          challenge,
          getAuthenticatorAssuranceLevel,
          listFactors,
          verify,
        },
        signInWithPassword,
        signOut,
        signUp,
      },
    },
    mockVerifyMfa: verify,
  };
});

vi.mock("@/lib/supabase/server", () => ({
  createServerSupabase: vi.fn(() => Promise.resolve(mockSupabase)),
}));

vi.mock("@/lib/telemetry/logger", () => ({
  createServerLogger: () => ({
    error: loggerErrorMock,
    info: loggerWarnMock,
    warn: loggerWarnMock,
  }),
}));

vi.mock("next/cache", () => ({
  revalidatePath: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  redirect: vi.fn(),
}));

function createFormData(values: Record<string, string>): FormData {
  const formData = new FormData();
  for (const [key, value] of Object.entries(values)) {
    formData.set(key, value);
  }
  return formData;
}

beforeEach(() => {
  mockSignOut.mockReset();
  mockSignInWithPassword.mockReset();
  mockGetAuthenticatorAssuranceLevel.mockReset();
  mockListFactors.mockReset();
  mockChallenge.mockReset();
  mockVerifyMfa.mockReset();
  mockSignUp.mockReset();
  loggerErrorMock.mockReset();
  loggerWarnMock.mockReset();
  vi.clearAllMocks();
});

describe("logoutAction", () => {
  it("should sign out and redirect to login", async () => {
    const { redirect } = await import("next/navigation");
    const { revalidatePath } = await import("next/cache");

    mockSignOut.mockResolvedValueOnce(undefined);
    await logoutAction();

    expect(mockSignOut).toHaveBeenCalled();
    expect(revalidatePath).toHaveBeenCalledWith("/");
    expect(redirect).toHaveBeenCalledWith("/login");
  });

  it("logs and continues when sign out fails", async () => {
    const { redirect } = await import("next/navigation");
    const { revalidatePath } = await import("next/cache");

    const signOutError = new Error("sign-out-failed");
    mockSignOut.mockRejectedValueOnce(signOutError);

    await logoutAction();

    expect(loggerErrorMock).toHaveBeenCalledWith("Logout error", {
      error: "sign-out-failed",
    });
    expect(revalidatePath).toHaveBeenCalledWith("/");
    expect(redirect).toHaveBeenCalledWith("/login");
  });
});

describe("loginWithPasswordAction", () => {
  it("redirects on successful login when MFA is not required", async () => {
    const { redirect } = await import("next/navigation");

    mockSignInWithPassword.mockResolvedValueOnce({ error: null });
    mockGetAuthenticatorAssuranceLevel.mockResolvedValueOnce({
      data: { currentLevel: "aal1", nextLevel: "aal1" },
      error: null,
    });

    await loginWithPasswordAction(
      { status: "idle" },
      createFormData({
        email: "test@example.com",
        next: "/dashboard",
        password: "password123",
      })
    );

    expect(mockSignInWithPassword).toHaveBeenCalledWith({
      email: "test@example.com",
      password: "password123",
    });
    expect(redirect).toHaveBeenCalledWith("/dashboard");
  });

  it("returns validation errors for invalid login form data", async () => {
    const result = await loginWithPasswordAction(
      { status: "idle" },
      createFormData({
        email: "invalid-email",
        password: "",
      })
    );

    expect(result).toMatchObject({
      error: "Invalid login details",
      status: "error",
    });
    expect(result).toHaveProperty("fieldErrors.email");
    expect(result).toHaveProperty("fieldErrors.password");
  });

  it("returns an MFA challenge when AAL indicates MFA is required", async () => {
    mockSignInWithPassword.mockResolvedValueOnce({ error: null });
    mockGetAuthenticatorAssuranceLevel.mockResolvedValueOnce({
      data: { currentLevel: "aal1", nextLevel: "aal2" },
      error: null,
    });
    mockListFactors.mockResolvedValueOnce({
      data: {
        totp: [{ factor_type: "totp", id: "factor-1", status: "verified" }],
      },
      error: null,
    });
    mockChallenge.mockResolvedValueOnce({ data: { id: "challenge-1" }, error: null });

    const result = await loginWithPasswordAction(
      { status: "idle" },
      createFormData({
        email: "test@example.com",
        next: "/dashboard",
        password: "password123",
      })
    );

    expect(result).toEqual({
      challengeId: "challenge-1",
      factorId: "factor-1",
      nextPath: "/dashboard",
      status: "mfa_required",
    });
  });
});

describe("verifyMfaAction", () => {
  it("returns validation errors for malformed TOTP codes", async () => {
    const result = await verifyMfaAction(
      { status: "idle" },
      createFormData({
        challengeId: "challenge-1",
        code: "123",
        factorId: "factor-1",
        next: "/dashboard",
      })
    );

    expect(result).toMatchObject({
      error: "Invalid verification details",
      status: "error",
    });
    expect(result).toHaveProperty("fieldErrors.code");
  });

  it("redirects after successful MFA verification", async () => {
    const { redirect } = await import("next/navigation");

    mockVerifyMfa.mockResolvedValueOnce({ error: null });

    await verifyMfaAction(
      { status: "idle" },
      createFormData({
        challengeId: "challenge-1",
        code: "123456",
        factorId: "factor-1",
        next: "/dashboard",
      })
    );

    expect(mockVerifyMfa).toHaveBeenCalledWith({
      challengeId: "challenge-1",
      code: "123456",
      factorId: "factor-1",
    });
    expect(redirect).toHaveBeenCalledWith("/dashboard");
  });
});

describe("registerWithPasswordAction", () => {
  it("returns validation errors for mismatched passwords", async () => {
    const result = await registerWithPasswordAction(
      { status: "idle" },
      createFormData({
        acceptTerms: "on",
        confirmPassword: "Different123!",
        email: "test@example.com",
        firstName: "John",
        lastName: "Doe",
        password: "Secure123!",
      })
    );

    expect(result).toMatchObject({
      error: "Invalid registration details",
      status: "error",
    });
    expect(result).toHaveProperty("fieldErrors.confirmPassword");
  });

  it("creates an account and redirects to next path when session is returned", async () => {
    const { redirect } = await import("next/navigation");

    mockSignUp.mockResolvedValueOnce({
      data: { session: { access_token: "token" } },
      error: null,
    });

    await registerWithPasswordAction(
      { status: "idle" },
      createFormData({
        acceptTerms: "on",
        confirmPassword: "Secure123!",
        email: "test@example.com",
        firstName: "John",
        lastName: "Doe",
        marketingOptIn: "on",
        next: "/dashboard",
        password: "Secure123!",
      })
    );

    expect(mockSignUp).toHaveBeenCalledWith({
      email: "test@example.com",
      options: {
        data: expect.objectContaining({
          email: "test@example.com",
          first_name: "John",
          full_name: "John Doe",
          last_name: "Doe",
          marketing_opt_in: true,
          terms_accepted: true,
        }),
        emailRedirectTo: "http://localhost:3000/auth/confirm?next=%2Fdashboard",
      },
      password: "Secure123!",
    });

    expect(redirect).toHaveBeenCalledWith("/dashboard");
  });

  it("redirects to check-email screen when no session is returned", async () => {
    const { redirect } = await import("next/navigation");

    mockSignUp.mockResolvedValueOnce({
      data: { session: null },
      error: null,
    });

    await registerWithPasswordAction(
      { status: "idle" },
      createFormData({
        acceptTerms: "on",
        confirmPassword: "Secure123!",
        email: "test@example.com",
        firstName: "John",
        lastName: "Doe",
        next: "/dashboard",
        password: "Secure123!",
      })
    );

    expect(redirect).toHaveBeenCalledWith("/register?status=check_email");
  });
});
