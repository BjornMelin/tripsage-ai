/**
 * @fileoverview Contact page (v1 placeholder) for public marketing routes.
 */

"use cache";

import type { Metadata } from "next";
import Link from "next/link";
import { ROUTES } from "@/lib/routes";

export const metadata: Metadata = {
  description: "How to reach the TripSage AI team.",
  title: "Contact - TripSage AI",
};

// biome-ignore lint/suspicious/useAwait: Next.js `"use cache"` requires an async function export.
export default async function ContactPage() {
  return (
    <main className="container py-12 space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Contact</h1>
        <p className="text-muted-foreground">
          This is a v1 placeholder page. Replace with a support workflow before
          production launch.
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Support</h2>
        <p className="text-muted-foreground">
          For now, use email support:{" "}
          <a
            className="text-primary underline hover:no-underline"
            href="mailto:support@tripsage.ai"
          >
            support@tripsage.ai
          </a>
          .
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Account & policies</h2>
        <p className="text-muted-foreground">
          Go to{" "}
          <Link
            className="text-primary underline hover:no-underline"
            href={ROUTES.register}
          >
            {ROUTES.register}
          </Link>{" "}
          to create an account, or{" "}
          <Link
            className="text-primary underline hover:no-underline"
            href={ROUTES.login}
          >
            {ROUTES.login}
          </Link>{" "}
          to sign in.
        </p>
      </section>
    </main>
  );
}
