/**
 * @fileoverview MSW handlers for Upstash Redis REST endpoints used in tests.
 */

import type { HttpHandler } from "msw";
import { HttpResponse, http } from "msw";

export const upstashHandlers: HttpHandler[] = [
  http.all(/https?:\/\/[^/]*upstash\.io\/.*/, () =>
    HttpResponse.json({ result: "OK", success: true })
  ),
];
