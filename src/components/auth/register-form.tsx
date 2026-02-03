/**
 * @fileoverview The register form component.
 */

"use client";

import { Loader2Icon, MailIcon } from "lucide-react";
import Link from "next/link";
import { useActionState, useMemo, useState } from "react";
import { GitHubMarkIcon, GoogleGIcon } from "@/components/icons/oauth-provider-icons";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  type RegisterActionState,
  registerWithPasswordAction,
} from "@/lib/auth/actions";
import { resolveRedirectUrl } from "@/lib/auth/redirect";
import { useSupabaseRequired } from "@/lib/supabase/client";

/** The register form props. */
type RegisterFormProps = {
  redirectTo?: string;
};

/**
 * The register form component.
 *
 * @param redirectTo - The redirect URL.
 * @returns The register form component.
 */
export function RegisterForm({ redirectTo }: RegisterFormProps) {
  const supabase = useSupabaseRequired();
  const [registerState, registerAction, registerPending] = useActionState<
    RegisterActionState,
    FormData
  >(registerWithPasswordAction, { status: "idle" });
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [acceptTerms, setAcceptTerms] = useState(false);
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
    try {
      const { error: oauthError } = await supabase.auth.signInWithOAuth({
        options: { redirectTo: targetUrl },
        provider,
      });
      if (oauthError) {
        setOauthError(oauthError.message);
      }
    } catch {
      setOauthError("OAuth failed. Please try again.");
    } finally {
      setOauthLoading(false);
    }
  };

  const registerError = registerState.status === "error" ? registerState.error : null;

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Create account</CardTitle>
        <CardDescription>Join TripSage to start planning</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form className="space-y-4" action={registerAction}>
          <input type="hidden" name="next" value={nextPath} />
          <input type="hidden" name="acceptTerms" value={acceptTerms ? "on" : ""} />
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="firstName">First name</Label>
              <Input
                id="firstName"
                name="firstName"
                type="text"
                autoComplete="given-name"
                required
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="lastName">Last name</Label>
              <Input
                id="lastName"
                name="lastName"
                type="text"
                autoComplete="family-name"
                required
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              spellCheck={false}
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
              autoComplete="new-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirm-password">Confirm password</Label>
            <Input
              id="confirm-password"
              name="confirmPassword"
              type="password"
              autoComplete="new-password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>
          <div className="flex items-start space-x-2">
            <Checkbox
              id="acceptTerms"
              checked={acceptTerms}
              onCheckedChange={(checked) => setAcceptTerms(checked === true)}
            />
            <Label htmlFor="acceptTerms" className="text-sm leading-tight">
              I agree to the{" "}
              <Link href="/terms" className="text-primary underline hover:no-underline">
                Terms of Service
              </Link>{" "}
              and{" "}
              <Link
                href="/privacy"
                className="text-primary underline hover:no-underline"
              >
                Privacy Policy
              </Link>
            </Label>
          </div>
          {registerError ? (
            <p className="text-sm text-destructive">{registerError}</p>
          ) : null}
          {oauthError ? <p className="text-sm text-destructive">{oauthError}</p> : null}
          <Button
            type="submit"
            className="w-full"
            disabled={oauthLoading || registerPending}
            data-testid="password-signup"
          >
            {registerPending ? (
              <Loader2Icon aria-hidden="true" className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <MailIcon aria-hidden="true" className="mr-2 h-4 w-4" />
            )}
            Create account
          </Button>
        </form>
        <div className="grid grid-cols-1 gap-2">
          <Button
            variant="outline"
            className="w-full"
            onClick={() => handleOAuth("github")}
            disabled={oauthLoading || registerPending}
            data-testid="oauth-github"
          >
            <GitHubMarkIcon aria-hidden="true" className="mr-2 h-4 w-4" /> Continue with
            GitHub
          </Button>
          <Button
            variant="outline"
            className="w-full"
            onClick={() => handleOAuth("google")}
            disabled={oauthLoading || registerPending}
            data-testid="oauth-google"
          >
            <GoogleGIcon aria-hidden="true" className="mr-2 h-4 w-4" /> Continue with
            Google
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
