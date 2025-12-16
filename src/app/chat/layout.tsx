/**
 * @fileoverview Chat route layout implementation.
 *
 * Implements and exports the ChatLayout component used by the chat route group.
 */

import "server-only";

import type { ReactNode } from "react";
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
  return children;
}
