/**
 * @fileoverview robots.txt metadata route.
 */

import type { MetadataRoute } from "next";
import { getServerOrigin } from "@/lib/url/server-origin";

/**
 * robots.txt metadata route.
 * @returns The robots.txt metadata.
 */
export default function robots(): MetadataRoute.Robots {
  const origin = getServerOrigin();

  return {
    rules: [
      {
        allow: ["/"],
        disallow: [
          "/api/",
          "/auth/",
          "/chat/",
          "/dashboard/",
          "/login",
          "/register",
          "/reset-password",
        ],
        userAgent: "*",
      },
    ],
    sitemap: `${origin}/sitemap.xml`,
  };
}
