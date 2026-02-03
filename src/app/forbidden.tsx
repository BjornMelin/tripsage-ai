/**
 * @fileoverview Global 403 page for App Router auth errors.
 */

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { MAIN_CONTENT_ID } from "@/lib/a11y/landmarks";
import { ROUTES } from "@/lib/routes";

/**
 * Global 403 page for App Router auth errors.
 * @returns The forbidden page.
 */
export default function Forbidden() {
  return (
    <main
      id={MAIN_CONTENT_ID}
      className="flex min-h-[60vh] flex-col items-center justify-center gap-6 px-6 text-center"
      tabIndex={-1}
    >
      <div className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">Access denied</h1>
        <p className="text-muted-foreground">
          Your account doesn’t have access to this resource.
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-3">
        <Button asChild>
          <Link href={ROUTES.dashboard.root}>Go to dashboard</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={ROUTES.home}>Go to homepage</Link>
        </Button>
      </div>
    </main>
  );
}
