/**
 * @fileoverview The login form component.
 */

"use client";

import { SiGithub, SiGoogle } from "@icons-pack/react-simple-icons";
import { Loader2Icon, MailIcon } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { resolveRedirectUrl } from "@/lib/auth/redirect";
import { useSupabaseRequired } from "@/lib/supabase/client";

/** The login form props. */
type LoginFormProps = {
  redirectTo?: string;
};

/**
 * The login form component.
 *
 * @param redirectTo - The redirect URL.
 * @returns The login form component.
 */
export function LoginForm({ redirectTo }: LoginFormProps) {
  const supabase = useSupabaseRequired();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [mfaStep, setMfaStep] = useState<{
    challengeId: string;
    factorId: string;
  } | null>(null);
  const [mfaError, setMfaError] = useState<string | null>(null);
  const [mfaSubmitting, setMfaSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const targetUrl = useMemo(
    () => resolveRedirectUrl(redirectTo, { absolute: true }),
    [redirectTo]
  );

  /** Starts an MFA challenge for a verified factor (prefers TOTP). */
  const startMfaChallenge = async () => {
    setMfaError(null);
    setMfaStep(null);
    const factorsRes = await supabase.auth.mfa.listFactors();
    if (factorsRes.error) {
      throw factorsRes.error;
    }

    const factorsArray = Array.isArray(factorsRes.data)
      ? factorsRes.data
      : [
          ...(factorsRes.data.totp ?? []),
          ...(factorsRes.data.webauthn ?? []),
          ...(factorsRes.data.phone ?? []),
        ];

    // Prefer TOTP for code-based verification; WebAuthn requires different handling
    const factor = factorsArray.find(
      (f) => f.status === "verified" && f.factor_type === "totp"
    ) ?? factorsArray.find((f) => f.status === "verified");
    if (!factor) {
      throw new Error("No verified MFA factor found for this account");
    }

    if (factor.factor_type !== "totp") {
      throw new Error("Only TOTP-based MFA is currently supported");
    }

    const challenge = await supabase.auth.mfa.challenge({ factorId: factor.id });
    if (challenge.error || !challenge.data?.id) {
      throw challenge.error ?? new Error("Failed to start MFA challenge");
    }

    setMfaStep({ challengeId: challenge.data.id, factorId: factor.id });
  };

  /** Handles the password login. */
  const handlePasswordLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setMfaError(null);
    setMfaStep(null);
    setLoading(true);
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    setLoading(false);
    if (signInError) {
      const code = (signInError as { code?: string } | null)?.code;
      const status = (signInError as { status?: number } | null)?.status;
      const isMfa =
        code === "insufficient_aal" ||
        code === "mfa_required";
      if (isMfa) {
        try {
          await startMfaChallenge();
        } catch (mfaStartError) {
          const message =
            (mfaStartError as { message?: string } | null)?.message ??
            "MFA required but challenge could not be started";
          setError(message);
        }
        return;
      }
      setError(signInError.message ?? "Login failed");
      return;
    }
    window.location.assign(targetUrl);
  };

  /** Handles MFA code verification once a challenge is active. */
  const handleMfaVerify = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!mfaStep) {
      return;
    }
    setMfaSubmitting(true);
    setMfaError(null);
    const verifyResult = await supabase.auth.mfa.verify({
      challengeId: mfaStep.challengeId,
      code: mfaCode,
      factorId: mfaStep.factorId,
    });
    setMfaSubmitting(false);
    if (verifyResult.error) {
      setMfaError(verifyResult.error.message ?? "Invalid or expired MFA code");
      return;
    }
    window.location.assign(targetUrl);
  };

  /** Handles the OAuth login. */
  const handleOAuth = async (provider: "github" | "google") => {
    setError(null);
    setLoading(true);
    const { error: oauthError } = await supabase.auth.signInWithOAuth({
      options: { redirectTo: targetUrl },
      provider,
    });
    setLoading(false);
    if (oauthError) {
      setError(oauthError.message);
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Sign in</CardTitle>
        <CardDescription>Access your TripSage dashboard</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form className="space-y-4" onSubmit={handlePasswordLogin}>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button
            type="submit"
            className="w-full"
            disabled={loading || !!mfaStep}
            data-testid="password-login"
          >
            {loading ? (
              <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <MailIcon className="mr-2 h-4 w-4" />
            )}
            Continue with email
          </Button>
        </form>
        {mfaStep ? (
          <form className="space-y-3" onSubmit={handleMfaVerify}>
            <div className="space-y-2">
              <Label htmlFor="mfa-code">Enter your 6-digit code</Label>
              <Input
                id="mfa-code"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                pattern="\d{6}"
                required
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value)}
                aria-describedby={mfaError ? "mfa-error" : undefined}
                aria-invalid={!!mfaError}
              />
            </div>
            {mfaError ? (
              <p id="mfa-error" className="text-sm text-destructive">
                {mfaError}
              </p>
            ) : null}
            <Button
              type="submit"
              className="w-full"
              disabled={mfaSubmitting}
              data-testid="mfa-verify"
            >
              {mfaSubmitting ? (
                <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Verify code
            </Button>
          </form>
        ) : null}
        <div className="grid grid-cols-1 gap-2">
          <Button
            variant="outline"
            className="w-full"
            onClick={() => handleOAuth("github")}
            disabled={loading}
            data-testid="oauth-github"
          >
            <SiGithub className="mr-2 h-4 w-4" /> Continue with GitHub
          </Button>
          <Button
            variant="outline"
            className="w-full"
            onClick={() => handleOAuth("google")}
            disabled={loading}
            data-testid="oauth-google"
          >
            <SiGoogle className="mr-2 h-4 w-4" /> Continue with Google
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
