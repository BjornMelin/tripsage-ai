/**
 * @fileoverview MSW handlers for Stripe API calls used in tests.
 */

import type { HttpHandler } from "msw";
import { HttpResponse, http } from "msw";

export const stripeHandlers: HttpHandler[] = [
  http.post("https://api.stripe.com/:path*", async () =>
    HttpResponse.json({ id: "pi_mock", status: "succeeded" })
  ),
];
