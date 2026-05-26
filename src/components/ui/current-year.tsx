"use client";

import { nowIso } from "@/lib/security/random";

function GetCurrentYear() {
  return new Date(nowIso()).getFullYear();
}

/**
 * Displays the current year on the client to avoid server prerender time coupling.
 */
export function CurrentYear() {
  return <>{GetCurrentYear()}</>;
}
