/**
 * @fileoverview Global 404 page for the App Router.
 */

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { MAIN_CONTENT_ID } from "@/lib/a11y/landmarks";
import { ROUTES } from "@/lib/routes";

/**
 * Global 404 page for the App Router.
 * @returns The not found page.
 */
export default function NotFound() {
  return (
    <main
      id={MAIN_CONTENT_ID}
      className="flex min-h-[60vh] flex-col items-center justify-center gap-6 px-6 text-center"
      tabIndex={-1}
    >
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Page not found</h1>
        <p className="text-muted-foreground">
          The page you’re looking for doesn’t exist or has moved.
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-3">
        <Button asChild>
          <Link href={ROUTES.home}>Go to homepage</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={ROUTES.dashboard.root}>Go to dashboard</Link>
        </Button>
      </div>
    </main>
  );
}
