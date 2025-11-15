import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";
import { createServerSupabase, getCurrentUser } from "@/lib/supabase/server";

export const metadata: Metadata = {
  description: "Reset your TripSage account password",
  title: "Reset Password - TripSage",
};

export default async function ResetPasswordPage() {
  const supabase = await createServerSupabase();

  // Use unified getCurrentUser to eliminate duplicate auth.getUser() calls
  const { user } = await getCurrentUser(supabase);

  if (user) {
    redirect("/dashboard");
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-linear-to-br from-background to-muted/20">
      {/* Background pattern */}
      <div className="absolute inset-0 bg-grid-white/10 bg-grid-16 mask-[radial-gradient(ellipse_at_center,white,transparent_70%)]" />

      {/* Content */}
      <div className="relative z-10 w-full max-w-md space-y-8">
        {/* Logo */}
        <div className="text-center">
          <Link href="/" className="inline-flex items-center justify-center space-x-2">
            <div className="w-12 h-12 bg-primary rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-2xl">T</span>
            </div>
            <span className="text-3xl font-bold">TripSage</span>
          </Link>
        </div>

        {/* Form */}
        <ResetPasswordForm />

        {/* Additional help */}
        <div className="text-center space-y-2">
          <p className="text-sm text-muted-foreground">
            Remember your password?{" "}
            <Link href="/login" className="text-primary hover:underline font-medium">
              Sign in instead
            </Link>
          </p>
          <p className="text-sm text-muted-foreground">
            Need help?{" "}
            <Link href="/support" className="text-primary hover:underline font-medium">
              Contact support
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
