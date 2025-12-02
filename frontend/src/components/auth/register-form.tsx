/**
 * @fileoverview The register form component.
 */

"use client";

import { SiGithub, SiGoogle } from "@icons-pack/react-simple-icons";
import { Loader2Icon, MailIcon } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
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
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const targetUrl = useMemo(() => resolveRedirectUrl(redirectTo), [redirectTo]);

  /** Handles the signup. */
  const handleSignup = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);

    // Validate required fields
    if (!firstName.trim()) {
      setError("First name is required");
      return;
    }
    if (!lastName.trim()) {
      setError("Last name is required");
      return;
    }
    if (!acceptTerms) {
      setError("You must accept the terms and conditions");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);
    // Build emailRedirectTo with next parameter for post-confirmation redirect
    const emailRedirectTo =
      typeof window === "undefined"
        ? undefined
        : new URL("/auth/confirm", window.location.origin).toString() +
          `?type=email&next=${encodeURIComponent(targetUrl)}`;

    const { data, error: signUpError } = await supabase.auth.signUp({
      email,
      options: {
        data: {
          email,
          first_name: firstName.trim(),
          full_name: `${firstName.trim()} ${lastName.trim()}`,
          last_name: lastName.trim(),
        },
        emailRedirectTo,
      },
      password,
    });
    setLoading(false);

    if (signUpError) {
      setError(signUpError.message);
      return;
    }
    // When email confirmation is required, data.session is null
    // Redirect to check_email page instead of dashboard
    if (!data?.session) {
      const checkEmailUrl =
        typeof window === "undefined"
          ? "/register?status=check_email"
          : new URL("/register?status=check_email", window.location.origin).toString();
      window.location.assign(checkEmailUrl);
      return;
    }
    // Only redirect to targetUrl if session exists (email confirmation disabled)
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
        <CardTitle>Create account</CardTitle>
        <CardDescription>Join TripSage to start planning</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <form className="space-y-4" onSubmit={handleSignup}>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="firstName">First name</Label>
              <Input
                id="firstName"
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
              <Link href="/privacy" className="text-primary underline hover:no-underline">
                Privacy Policy
              </Link>
            </Label>
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button
            type="submit"
            className="w-full"
            disabled={loading}
            data-testid="password-signup"
          >
            {loading ? (
              <Loader2Icon className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <MailIcon className="mr-2 h-4 w-4" />
            )}
            Create account
          </Button>
        </form>
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
