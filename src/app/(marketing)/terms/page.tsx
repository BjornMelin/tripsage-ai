/**
 * @fileoverview Terms of service (v1 placeholder) for public marketing routes.
 */

"use cache";

import type { Metadata } from "next";
import Link from "next/link";
import { ROUTES } from "@/lib/routes";

export const metadata: Metadata = {
  description: "The terms that govern use of TripSage AI.",
  title: "Terms of Service - TripSage AI",
};

export default function TermsPage() {
  return (
    <main className="container py-12 space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Terms of Service</h1>
        <p className="text-muted-foreground">
          This is a v1 placeholder intended to unblock the product journey. Replace with
          counsel-reviewed terms before production launch.
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Key points</h2>
        <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
          <li>You must be authorized to use your connected accounts.</li>
          <li>You are responsible for travel decisions and booking details.</li>
          <li>We may rate limit or suspend abuse to protect the service.</li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Privacy</h2>
        <p className="text-muted-foreground">
          Review the privacy policy:{" "}
          <Link
            className="text-primary underline hover:no-underline"
            href={ROUTES.privacy}
          >
            {ROUTES.privacy}
          </Link>
          .
        </p>
      </section>
    </main>
  );
}
