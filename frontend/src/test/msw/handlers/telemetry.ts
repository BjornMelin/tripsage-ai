/**
 * @fileoverview MSW handlers for telemetry endpoints used in tests.
 */

import { HttpResponse, http } from "msw";

export const telemetryHandlers = [
  http.post("/api/telemetry/activities", () => {
    return HttpResponse.json({ ok: true });
  }),
];
