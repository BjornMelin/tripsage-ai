/**
 * @fileoverview Shared telemetry constants.
 *
 * This module exports telemetry constants that can be used in both
 * server and client contexts without boundary violations.
 */

/** Canonical tracer/service name for frontend observability. */
export const TELEMETRY_SERVICE_NAME = "tripsage-frontend";

/** Whether to suppress console output in telemetry alerts (for performance tests). */
export const TELEMETRY_SILENT = process.env.TELEMETRY_SILENT === "1";
