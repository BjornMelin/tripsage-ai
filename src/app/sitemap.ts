/**
 * @fileoverview sitemap.xml metadata route.
 */

import type { MetadataRoute } from "next";
import { ROUTES } from "@/lib/routes";
import { getServerOrigin } from "@/lib/url/server-origin";

/**
 * sitemap.xml metadata route.
 * @returns The sitemap.xml metadata.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const origin = getServerOrigin();

  const urls = [
    ROUTES.home,
    ROUTES.aiDemo,
    ROUTES.contact,
    ROUTES.faq,
    ROUTES.privacy,
    ROUTES.terms,
  ];

  return urls.map((pathname) => ({
    url: new URL(pathname, origin).toString(),
  }));
}
