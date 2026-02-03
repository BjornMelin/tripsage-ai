/**
 * @fileoverview MSW server instance for Node.js test environment.
 *
 * This server intercepts HTTP requests during test execution, providing
 * predictable mock responses without requiring real network calls.
 *
 * The server is integrated into the Vitest setup (setup-node / setup-jsdom) and is
 * active for all tests. Individual tests can override default handlers using
 * server.use() for specific scenarios.
 */

import { setupServer } from "msw/node";
import { aiProviderHandlers } from "./handlers/ai-providers";
import { aiRouteHandlers } from "./handlers/ai-routes";
import { amadeusHandlers } from "./handlers/amadeus";
import { apiRouteHandlers } from "./handlers/api-routes";
import { authHandlers } from "./handlers/auth";
import { authRouteHandlers } from "./handlers/auth-routes";
import { chatHandlers } from "./handlers/chat";
import { errorReportingHandlers } from "./handlers/error-reporting";
import { externalApiHandlers } from "./handlers/external-apis";
import { googleHandlers } from "./handlers/google";
import { imageProxyHandlers } from "./handlers/image-proxy";
import { stripeHandlers } from "./handlers/stripe";
import { supabaseHandlers } from "./handlers/supabase";
import { telemetryHandlers } from "./handlers/telemetry";
import { upstashHandlers } from "./handlers/upstash";
import { composeHandlers } from "./handlers/utils";

const handlers = composeHandlers(
  apiRouteHandlers,
  aiRouteHandlers,
  authHandlers,
  authRouteHandlers,
  chatHandlers,
  amadeusHandlers,
  externalApiHandlers,
  errorReportingHandlers,
  googleHandlers,
  imageProxyHandlers,
  aiProviderHandlers,
  stripeHandlers,
  supabaseHandlers,
  upstashHandlers,
  telemetryHandlers
);

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
