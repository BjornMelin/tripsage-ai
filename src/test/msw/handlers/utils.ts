/**
 * @fileoverview Small helpers for composing MSW handler sets in tests.
 */

import type { HttpHandler } from "msw";

/**
 * Flatten multiple handler groups into a single array for `server.use(...)`.
 */
export const composeHandlers = (
  ...groups: ReadonlyArray<HttpHandler>[]
): HttpHandler[] => groups.flat();
