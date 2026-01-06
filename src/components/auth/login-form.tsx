/**
 * @fileoverview The login form component.
 */

"use client";

import { SiGithub, SiGoogle } from "@icons-pack/react-simple-icons";
import { Loader2Icon, MailIcon } from "lucide-react";
import { useActionState, useMemo, useState } from "react";
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
import {
  type LoginActionState,
  loginWithPasswordAction,
  type VerifyMfaActionState,
  verifyMfaAction,
} from "@/lib/auth/actions";
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
  const [loginState, loginAction, loginPending] = useActionState<
    LoginActionState,
    FormData
  >(loginWithPasswordAction, { status: "idle" });
  const [mfaState, mfaAction, mfaPending] = useActionState<
    VerifyMfaActionState,
    FormData
  >(verifyMfaAction, { status: "idle" });
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [oauthError, setOauthError] = useState<string | null>(null);
  const [oauthLoading, setOauthLoading] = useState(false);
  const nextPath = useMemo(() => resolveRedirectUrl(redirectTo), [redirectTo]);
  const targetUrl = useMemo(
    () => resolveRedirectUrl(redirectTo, { absolute: true }),
    [redirectTo]
  );

  /** Handles the OAuth login. */
  const handleOAuth = async (provider: "github" | "google") => {
    setOauthError(null);
    setOauthLoading(true);
    const { error: oauthError } = await supabase.auth.signInWithOAuth({
      options: { redirectTo: targetUrl },
      provider,
    });
    setOauthLoading(false);
    if (oauthError) {
      setOauthError(oauthError.message);
    }
  };

  const passwordError = loginState.status === "error" ? loginState.error : null;
  const mfaError = mfaState.status === "error" ? mfaState.error : null;
  const mfaStep =
    loginState.status === "mfa_required"
      ? { challengeId: loginState.challengeId, factorId: loginState.factorId }
      : null;
  const mfaNextPath =
    loginState.status === "mfa_required" ? loginState.nextPath : nextPath;

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Sign in</CardTitle>
        <CardDescription>Access your TripSage dashboard</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form className="space-y-4" action={loginAction}>
          <input type="hidden" name="next" value={nextPath} />
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              name="email"
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
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {passwordError ? (
            <p className="text-sm text-destructive">{passwordError}</p>
          ) : null}
          {oauthError ? <p className="text-sm text-destructive">{oauthError}</p> : null}
          <Button
            type="submit"
            className="w-full"
            disabled={oauthLoading || loginPending || !!mfaStep}
            data-testid="password-login"
          >
            {loginPending ? (
              <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <MailIcon className="mr-2 h-4 w-4" />
            )}
            Continue with email
          </Button>
        </form>
        {mfaStep ? (
          <form className="space-y-3" action={mfaAction}>
            <input type="hidden" name="challengeId" value={mfaStep.challengeId} />
            <input type="hidden" name="factorId" value={mfaStep.factorId} />
            <input type="hidden" name="next" value={mfaNextPath} />
            <div className="space-y-2">
              <Label htmlFor="mfa-code">Enter your 6-digit code</Label>
              <Input
                id="mfa-code"
                name="code"
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
              disabled={mfaPending}
              data-testid="mfa-verify"
            >
              {mfaPending ? (
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
            disabled={oauthLoading || loginPending || mfaPending || !!mfaStep}
            data-testid="oauth-github"
          >
            <SiGithub className="mr-2 h-4 w-4" /> Continue with GitHub
          </Button>
          <Button
            variant="outline"
            className="w-full"
            onClick={() => handleOAuth("google")}
            disabled={oauthLoading || loginPending || mfaPending || !!mfaStep}
            data-testid="oauth-google"
          >
            <SiGoogle className="mr-2 h-4 w-4" /> Continue with Google
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
