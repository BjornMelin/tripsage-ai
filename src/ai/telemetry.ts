/**
 * @fileoverview Privacy-safe AI SDK telemetry configuration.
 */

import type { TelemetryOptions } from "ai";

type AiTelemetryOptions = Omit<TelemetryOptions, "recordInputs" | "recordOutputs">;

type ContentPrivacy = {
  readonly recordInputs: false;
  readonly recordOutputs: false;
};

/**
 * Creates native AI SDK telemetry options without recording model content.
 *
 * Global telemetry integrations are enabled for every AI SDK operation, so every
 * production call must use this helper to keep prompts, documents, and outputs out
 * of exported spans.
 *
 * @param options Native telemetry options excluding content-recording controls.
 * @returns Telemetry options with input and output recording disabled.
 */
export function createAiTelemetry<const Options extends AiTelemetryOptions>(
  options: Options & {
    recordInputs?: never;
    recordOutputs?: never;
  }
): Options & ContentPrivacy {
  return {
    ...options,
    recordInputs: false,
    recordOutputs: false,
  };
}
