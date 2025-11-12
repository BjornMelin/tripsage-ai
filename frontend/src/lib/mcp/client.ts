/**
 * @fileoverview MCP client creation helper for consistent SSE transport setup.
 *
 * Centralizes MCP client initialization to avoid duplication across tools.
 * Provides type-safe wrappers for tool discovery and execution.
 */

import { experimental_createMCPClient as createMcpClient } from "@ai-sdk/mcp";

/**
 * MCP client interface for tool discovery and resource management.
 */
export type McpClient = {
  /**
   * Retrieve available tools from the MCP server.
   *
   * @returns Promise resolving to a record of tool names to tool definitions.
   */
  tools: () => Promise<Record<string, unknown>>;
  /**
   * Close the MCP client connection and clean up resources.
   *
   * @returns Promise resolving when cleanup is complete.
   */
  close: () => Promise<void>;
};

/**
 * Create an MCP client with SSE transport.
 *
 * Initializes a client connection to an MCP server using Server-Sent Events
 * (SSE) transport. Supports optional authorization headers for authenticated
 * endpoints.
 *
 * @param url - MCP server URL (SSE endpoint).
 * @param headers - Optional headers (e.g., authorization). Merged with default transport headers.
 * @returns Promise resolving to an MCP client instance.
 */
export async function createMcpClientHelper(
  url: string,
  headers?: Record<string, string>
): Promise<McpClient> {
  const client = await createMcpClient({
    transport: {
      headers,
      type: "sse",
      url,
    },
  });
  return client as unknown as McpClient;
}

/**
 * Get the first available tool from an MCP client by trying multiple names.
 *
 * Searches for tools in the order specified by `names`. Returns the first
 * tool that exists and has an `execute` method.
 *
 * @param client - MCP client instance.
 * @param names - Tool names to try in order. First match is returned.
 * @returns Promise resolving to the first available tool with an `execute` method,
 *   or undefined if none found.
 */
export async function getMcpTool(
  client: McpClient,
  ...names: string[]
): Promise<
  { execute: (args: unknown, options?: unknown) => Promise<unknown> } | undefined
> {
  const tools = await client.tools();
  for (const name of names) {
    const tool = tools[name];
    if (tool && typeof tool === "object" && "execute" in tool) {
      return tool as {
        execute: (args: unknown, options?: unknown) => Promise<unknown>;
      };
    }
  }
  return undefined;
}
