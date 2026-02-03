/**
 * @fileoverview Remote image proxy endpoint (same-origin) for next/image consumers.
 */

import "server-only";

import { remoteImageProxyRequestSchema } from "@schemas/images";
import type { NextRequest } from "next/server";
import { withApiGuards } from "@/lib/api/factory";
import { validateSchema } from "@/lib/api/route-helpers";
import { handleRemoteImageProxy } from "./_handler";

/**
 * Proxies a remote image request after validating the query string.
 *
 * @param req - Incoming request containing a `url` query parameter.
 * @returns Response with the proxied image or a standardized error payload.
 */
export const GET = withApiGuards({
  auth: false,
  botId: true,
  rateLimit: "images:proxy",
  telemetry: "images.proxy",
})(async (req: NextRequest) => {
  const { searchParams } = new URL(req.url);
  const url = searchParams.get("url") ?? "";

  const validation = validateSchema(remoteImageProxyRequestSchema, { url });
  if (!validation.ok) return validation.error;

  return await handleRemoteImageProxy(validation.data);
});
