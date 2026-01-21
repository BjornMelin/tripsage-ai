/**
 * @fileoverview Minimal `rehype-harden` implementation for tests.
 *
 * We keep this local (via `vitest.config.ts` aliases) to avoid ESM/CJS packaging
 * edge-cases in Vitest forks while still testing protocol hardening behavior.
 */

import {
  BLOCKED_PROTOCOLS,
  INVALID_BLOB_MARKER,
  SAFE_PROTOCOLS,
} from "./rehype-harden.constants";

type HardenOptions = {
  defaultOrigin?: string;
  allowedLinkPrefixes?: string[];
  allowedImagePrefixes?: string[];
  allowDataImages?: boolean;
  allowedProtocols?: string[];
  blockedImageClass?: string;
  blockedLinkClass?: string;
};

type HastText = { type: "text"; value: string };
type HastElement = {
  type: "element";
  tagName: string;
  properties: Record<string, unknown>;
  children: HastNode[];
};
type HastRoot = { type: "root"; children: HastNode[] };
type HastParent = HastElement | HastRoot;

type HastNode = HastText | HastElement | HastRoot;

function parseUrl(url: unknown, defaultOrigin: string): URL | null {
  if (typeof url !== "string") return null;
  try {
    return new URL(url);
  } catch {
    if (defaultOrigin) {
      try {
        return new URL(url, defaultOrigin);
      } catch {
        return null;
      }
    }

    if (url.startsWith("/") || url.startsWith("./") || url.startsWith("../")) {
      try {
        return new URL(url, "http://example.com");
      } catch {
        return null;
      }
    }

    return null;
  }
}

function isPathRelativeUrl(url: unknown): url is string {
  if (typeof url !== "string") return false;
  return url.startsWith("/") || url.startsWith("./") || url.startsWith("../");
}

function transformUrl(
  url: unknown,
  allowedPrefixes: string[],
  defaultOrigin: string,
  allowDataImages: boolean,
  isImage: boolean,
  allowedProtocols: string[]
): string | null {
  if (!url) return null;

  if (typeof url === "string" && url.startsWith("#") && !isImage) {
    try {
      const testUrl = new URL(url, "http://example.com");
      if (testUrl.hash === url) return url;
    } catch {
      // Invalid hash format, fall through to normal validation.
    }
  }

  if (typeof url === "string" && url.startsWith("data:")) {
    if (isImage && allowDataImages && url.startsWith("data:image/")) {
      return url;
    }
    return null;
  }

  if (typeof url === "string" && url.startsWith("blob:")) {
    try {
      const blobUrl = new URL(url);
      if (blobUrl.protocol === "blob:" && url.length > 5) {
        const afterProtocol = url.slice("blob:".length);
        if (afterProtocol && afterProtocol !== INVALID_BLOB_MARKER) return url;
      }
    } catch {
      return null;
    }
    return null;
  }

  const parsedUrl = parseUrl(url, defaultOrigin);
  if (!parsedUrl) return null;

  if (BLOCKED_PROTOCOLS.has(parsedUrl.protocol)) return null;

  const protocolAllowed =
    SAFE_PROTOCOLS.has(parsedUrl.protocol) ||
    allowedProtocols.includes(parsedUrl.protocol) ||
    allowedProtocols.includes("*");
  if (!protocolAllowed) return null;

  if (parsedUrl.protocol === "mailto:" || !parsedUrl.protocol.match(/^https?:$/)) {
    return parsedUrl.href;
  }

  const inputWasRelative = isPathRelativeUrl(url);
  if (
    allowedPrefixes.some((prefix) => {
      const parsedPrefix = parseUrl(prefix, defaultOrigin);
      if (!parsedPrefix) return false;
      if (parsedPrefix.origin !== parsedUrl.origin) return false;
      return parsedUrl.href.startsWith(parsedPrefix.href);
    })
  ) {
    return inputWasRelative
      ? parsedUrl.pathname + parsedUrl.search + parsedUrl.hash
      : parsedUrl.href;
  }

  if (allowedPrefixes.includes("*")) {
    if (parsedUrl.protocol !== "https:" && parsedUrl.protocol !== "http:") {
      return null;
    }
    return inputWasRelative
      ? parsedUrl.pathname + parsedUrl.search + parsedUrl.hash
      : parsedUrl.href;
  }

  return null;
}

function isParentNode(node: HastNode): node is HastParent {
  return "children" in node && Array.isArray(node.children);
}

export function harden({
  defaultOrigin = "",
  allowedLinkPrefixes = [],
  allowedImagePrefixes = [],
  allowDataImages = false,
  allowedProtocols = [],
  blockedImageClass = "inline-block bg-muted text-muted-foreground px-3 py-1 rounded text-sm",
  blockedLinkClass = "text-muted-foreground",
}: HardenOptions): (tree: HastRoot) => void {
  const hasSpecificLinkPrefixes =
    allowedLinkPrefixes.length > 0 && !allowedLinkPrefixes.every((p) => p === "*");
  const hasSpecificImagePrefixes =
    allowedImagePrefixes.length > 0 && !allowedImagePrefixes.every((p) => p === "*");
  if (!defaultOrigin && (hasSpecificLinkPrefixes || hasSpecificImagePrefixes)) {
    throw new Error(
      "defaultOrigin is required when allowedLinkPrefixes or allowedImagePrefixes are provided"
    );
  }

  return (tree) => {
    const walk = (node: HastNode, parent?: HastParent, index?: number): void => {
      if (node.type === "element") {
        const element = node;

        if (element.tagName === "a") {
          const transformedUrl = transformUrl(
            element.properties.href,
            allowedLinkPrefixes,
            defaultOrigin,
            false,
            false,
            allowedProtocols
          );

          if (transformedUrl === null) {
            if (isParentNode(element)) {
              for (let i = 0; i < element.children.length; i += 1) {
                walk(element.children[i], element, i);
              }
            }

            if (parent && typeof index === "number") {
              parent.children[index] = {
                children: [
                  ...element.children,
                  { type: "text", value: " [blocked]" } satisfies HastText,
                ],
                properties: {
                  class: blockedLinkClass,
                  title: `Blocked URL: ${String(element.properties.href)}`,
                },
                tagName: "span",
                type: "element",
              } satisfies HastElement;
            }
            return;
          }

          element.properties.href = transformedUrl;
          element.properties.target = "_blank";
          element.properties.rel = "noopener noreferrer";
        } else if (element.tagName === "img") {
          const transformedUrl = transformUrl(
            element.properties.src,
            allowedImagePrefixes,
            defaultOrigin,
            allowDataImages,
            true,
            allowedProtocols
          );

          if (transformedUrl === null) {
            if (parent && typeof index === "number") {
              parent.children[index] = {
                children: [
                  {
                    type: "text",
                    value: `[Image blocked: ${String(
                      element.properties.alt || "No description"
                    )}]`,
                  } satisfies HastText,
                ],
                properties: { class: blockedImageClass },
                tagName: "span",
                type: "element",
              } satisfies HastElement;
            }
            return;
          }

          element.properties.src = transformedUrl;
        }
      }

      if (!isParentNode(node)) return;
      for (let i = 0; i < node.children.length; i += 1) {
        walk(node.children[i], node, i);
      }
    };

    walk(tree);
  };
}

export default harden;
