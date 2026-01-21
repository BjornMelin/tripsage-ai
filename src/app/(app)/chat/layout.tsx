/**
 * @fileoverview Chat route layout implementation.
 */

import "server-only";

import type { ReactNode } from "react";
import { MAIN_CONTENT_ID } from "@/lib/a11y/landmarks";
import { requireUser } from "@/lib/auth/server";
import { ROUTES } from "@/lib/routes";

/**
 * Chat route layout that requires an authenticated user.
 *
 * If the request is unauthenticated, this layout triggers a redirect to the login
 * page with `next=/chat` so the user returns here after signing in.
 *
 * @param props - Layout props.
 * @param props.children - Nested route content.
 * @returns The nested route content once authentication is verified.
 */
export default async function ChatLayout({
  children,
}: {
  children: ReactNode;
}): Promise<ReactNode> {
  await requireUser({ redirectTo: ROUTES.chat });
  return (
    <main id={MAIN_CONTENT_ID} className="flex-1" tabIndex={-1}>
      {children}
    </main>
  );
}
