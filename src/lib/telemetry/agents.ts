/**
 * @fileoverview Telemetry recording for agent tool execution events.
 *
 * Provides structured event recording with OpenTelemetry spans for agent
 * workflow tool execution, including cache hits, durations, and errors.
 */

import type { AgentWorkflowKind } from "@schemas/agents";
import { withTelemetrySpan } from "./span";

/**
 * Agent tool execution event data.
 *
 * Captures workflow context, tool name, execution status, duration,
 * cache hit status, and optional error message for observability.
 */
export type AgentToolEvent = {
  workflow: AgentWorkflowKind;
  tool: string;
  status: "success" | "error";
  durationMs: number;
  cacheHit?: boolean;
  errorMessage?: string;
};

/**
 * Record an agent tool execution event with telemetry.
 *
 * Creates an OpenTelemetry span with attributes for workflow, tool name,
 * status, duration, cache hit, and error message (if present). Error
 * messages are redacted from span attributes for security.
 *
 * @param event - Tool execution event data to record.
 * @returns Promise that resolves when telemetry is recorded.
 */
export function recordAgentToolEvent(event: AgentToolEvent): Promise<void> {
  const { workflow, tool, durationMs, status, cacheHit, errorMessage } = event;
  return withTelemetrySpan(
    `agent.tool.${tool}`,
    {
      attributes: {
        "agent.cache_hit": Boolean(cacheHit),
        "agent.duration_ms": durationMs,
        "agent.status": status,
        "agent.tool": tool,
        "agent.workflow": workflow,
      },
      redactKeys: ["agent.error"],
    },
    (span) => {
      if (errorMessage) {
        span.setAttribute("agent.error", errorMessage);
      }
    }
  );
}
