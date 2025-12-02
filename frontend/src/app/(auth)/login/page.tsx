/**
 * @fileoverview Login page component for the TripSage application.
 */

import type { Metadata } from "next";
import Link from "next/link";
import { LoginForm } from "@/components/auth/login-form";

/** The metadata for the login page. */
export const metadata: Metadata = {
  description: "Sign in to your TripSage account to start planning your perfect trips",
  title: "Sign In - TripSage",
};

/** The login page component. */
export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ from?: string; error?: string }>;
}) {
  const params = await searchParams;
  const redirectTo = params?.from || "/dashboard";

  return (
    <div className="min-h-screen flex">
      {/* Left side - Branding and imagery */}
      <div className="hidden lg:flex lg:w-1/2 bg-linear-to-br from-primary/10 via-primary/5 to-background relative overflow-hidden">
        <div className="absolute inset-0 bg-grid-white/10 bg-grid-16 mask-[radial-gradient(ellipse_at_center,transparent_20%,black)]" />

        <div className="relative z-10 flex flex-col justify-between p-12 text-white">
          <div>
            <Link href="/" className="flex items-center space-x-2">
              <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-xl">T</span>
              </div>
              <span className="text-2xl font-bold text-foreground">TripSage</span>
            </Link>
          </div>

          <div className="space-y-6">
            <h1 className="text-4xl font-bold text-foreground">
              Welcome back to TripSage
            </h1>
            <p className="text-lg text-muted-foreground max-w-md">
              Your AI-powered travel companion is ready to help you plan your next
              adventure. Sign in to access your personalized travel recommendations and
              itineraries.
            </p>
          </div>

          <div className="space-y-4">
            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-primary/20 rounded-full flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-primary"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  role="img"
                  aria-label="Smart Trip Planning icon"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064"
                  />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-foreground">Smart Trip Planning</h3>
                <p className="text-sm text-muted-foreground">
                  AI-powered recommendations tailored to your preferences
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-primary/20 rounded-full flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-primary"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  role="img"
                  aria-label="Collaborative Planning icon"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                  />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-foreground">
                  Collaborative Planning
                </h3>
                <p className="text-sm text-muted-foreground">
                  Plan trips together with friends and family
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <div className="w-12 h-12 bg-primary/20 rounded-full flex items-center justify-center">
                <svg
                  className="w-6 h-6 text-primary"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  role="img"
                  aria-label="Detailed Itineraries icon"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
                  />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-foreground">Detailed Itineraries</h3>
                <p className="text-sm text-muted-foreground">
                  Travel plans with all the details
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right side - Login form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 lg:p-12">
        <div className="w-full max-w-lg">
          <LoginForm redirectTo={redirectTo} />
        </div>
      </div>
    </div>
  );
}
