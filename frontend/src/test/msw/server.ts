/**
 * @fileoverview MSW server instance for Node.js test environment.
 *
 * This server intercepts HTTP requests during test execution, providing
 * predictable mock responses without requiring real network calls.
 *
 * The server is integrated into the global test setup (test-setup.ts) and is
 * active for all tests. Individual tests can override default handlers using
 * server.use() for specific scenarios.
 */

import { setupServer } from "msw/node";
import { amadeusHandlers } from "./handlers/amadeus";
import { apiRouteHandlers } from "./handlers/api-routes";
import { attachmentHandlers } from "./handlers/attachments";
import { authHandlers } from "./handlers/auth";
import { authRouteHandlers } from "./handlers/auth-routes";
import { chatHandlers } from "./handlers/chat";
import { errorReportingHandlers } from "./handlers/error-reporting";
import { externalApiHandlers } from "./handlers/external-apis";
import { googlePlacesHandlers } from "./handlers/google-places";
import { providersHandlers } from "./handlers/providers";
import { stripeHandlers } from "./handlers/stripe";
import { supabaseHandlers } from "./handlers/supabase";
import { telemetryHandlers } from "./handlers/telemetry";
import { upstashHandlers } from "./handlers/upstash";

const handlers = [
  ...attachmentHandlers,
  ...apiRouteHandlers,
  ...authHandlers,
  ...authRouteHandlers,
  ...chatHandlers,
  ...amadeusHandlers,
  ...externalApiHandlers,
  ...errorReportingHandlers,
  ...googlePlacesHandlers,
  ...providersHandlers,
  ...stripeHandlers,
  ...supabaseHandlers,
  ...upstashHandlers,
  ...telemetryHandlers,
];

/**
 * MSW server instance configured with default request handlers.
 *
 * Lifecycle:
 * - beforeAll: server.listen() starts request interception
 * - afterEach: server.resetHandlers() removes test-specific overrides
 * - afterAll: server.close() stops interception and cleanup
 *
 * @example
 * ```typescript
 * import { server } from '@/test/msw/server';
 * import { http, HttpResponse } from 'msw';
 *
 * test('handles API error', () => {
 *   server.use(
 *     http.post('/api/endpoint', () => {
 *       return new HttpResponse(null, { status: 500 });
 *     })
 *   );
 *   // Test code that expects 500 error
 * });
 * ```
 */
export const server = setupServer(...handlers);
