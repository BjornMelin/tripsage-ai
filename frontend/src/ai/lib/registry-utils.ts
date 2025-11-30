/**
 * @fileoverview Registry utilities for AI tools with telemetry and validation.
 *
 * Provides strongly-typed helpers for accessing and executing tools from
 * the shared tool registry with validation and telemetry integration.
 */

import "server-only";

import type { toolRegistry } from "@ai/tools";
import type { Tool, ToolCallOptions } from "ai";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/** Strongly typed view of a tool from the shared registry; enforces execute presence. */
export type RegisteredTool<Params = unknown, Result = unknown> = Tool<
  Params,
  Result
> & {
  description?: string;
  inputSchema?: unknown;
  execute: (params: Params, callOptions?: ToolCallOptions) => Promise<Result> | Result;
};

/** Validate a registry entry is present and executable. @throws Error if missing or lacks execute. */
export const requireTool = <Params, Result>(
  tool: unknown,
  name: string
): RegisteredTool<Params, Result> => {
  if (!tool) {
    throw new Error(`Tool ${name} not registered in toolRegistry`);
  }
  if (typeof (tool as { execute?: unknown }).execute !== "function") {
    throw new Error(`Tool ${name} missing execute binding`);
  }
  return tool as RegisteredTool<Params, Result>;
};

/** Fetch a named tool from the registry with validation and typing. */
export const getRegistryTool = <Params, Result>(
  registry: typeof toolRegistry,
  name: keyof typeof registry
): RegisteredTool<Params, Result> => requireTool(registry[name], String(name));

/** Execute a registry tool and normalize to a Promise-based result. */
export const invokeTool = <Params, Result>(
  tool: RegisteredTool<Params, Result>,
  params: Params,
  callOptions?: ToolCallOptions
): Promise<Result> => {
  return withTelemetrySpan(
    "agent.tool.execute",
    {
      attributes: {
        hasCallOptions: Boolean(callOptions),
        toolDescription: tool.description ?? "unknown",
        toolName: (tool as { name?: string }).name ?? "unknown",
      },
    },
    async () => {
      const result = tool.execute(params, callOptions);
      return result && typeof (result as { then?: unknown }).then === "function"
        ? await Promise.resolve(result)
        : result;
    }
  );
};
