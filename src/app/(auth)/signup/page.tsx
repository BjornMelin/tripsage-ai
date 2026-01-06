/**
 * @fileoverview Signup page alias for the TripSage application.
 */

import { redirect } from "next/navigation";

export default async function SignupPage({
  searchParams,
}: {
  searchParams: Promise<{ from?: string; next?: string }>;
}) {
  const params = await searchParams;
  const query = new URLSearchParams();

  if (params.from) query.set("from", params.from);
  if (params.next) query.set("next", params.next);

  const suffix = query.toString();
  redirect(suffix ? `/register?${suffix}` : "/register");
}
