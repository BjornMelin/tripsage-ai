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
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const targetUrl = useMemo(
    () => resolveRedirectUrl(redirectTo, { absolute: true }),
    [redirectTo]
  );

  /** Handles the password login. */
  const handlePasswordLogin = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    setLoading(false);
    if (signInError) {
      setError(signInError.message);
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
            disabled={loading}
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
