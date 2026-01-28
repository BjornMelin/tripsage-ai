/**
 * @fileoverview Privacy policy (v1 placeholder) for public marketing routes.
 */

"use cache";

import type { Metadata } from "next";
import Link from "next/link";
import { MarketingContainer } from "@/components/marketing/marketing-container";
import { MAIN_CONTENT_ID } from "@/lib/a11y/landmarks";
import { ROUTES } from "@/lib/routes";

export const metadata: Metadata = {
  description: "Learn how TripSage AI collects, uses, and protects your information.",
  title: "Privacy Policy - TripSage AI",
};

// biome-ignore lint/suspicious/useAwait: Next.js `"use cache"` requires an async function export.
export default async function PrivacyPage() {
  return (
    <main id={MAIN_CONTENT_ID} className="flex-1" tabIndex={-1}>
      <MarketingContainer className="py-12 space-y-8">
        <header className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">Privacy Policy</h1>
          <p className="text-muted-foreground">
            This is a v1 placeholder policy intended to unblock navigation and
            onboarding. Replace with counsel-reviewed text before production launch.
          </p>
        </header>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">Summary</h2>
          <ul className="list-disc pl-5 space-y-2 text-muted-foreground">
            <li>We collect account and usage data to provide the service.</li>
            <li>We do not sell personal information.</li>
            <li>Security controls include least-privilege access and audit logs.</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">Contact</h2>
          <p className="text-muted-foreground">
            Questions? Use the contact page:{" "}
            <Link
              className="text-primary underline hover:no-underline"
              href={ROUTES.contact}
            >
              {ROUTES.contact}
            </Link>
            .
          </p>
        </section>
      </MarketingContainer>
    </main>
  );
}
