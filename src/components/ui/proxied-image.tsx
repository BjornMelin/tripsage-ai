/**
 * @fileoverview Client-side helper for rendering proxied images with fallback.
 */

"use client";

import type { StaticImageData } from "next/image";
import Image from "next/image";
import type { ReactNode } from "react";
import {
  buildImageProxyUrl,
  isAbsoluteHttpUrl,
  normalizeNextImageSrc,
} from "@/lib/images/image-proxy";

const DEFAULT_FALLBACK = (
  <div className="flex items-center justify-center h-full text-muted-foreground text-xs">
    No image
  </div>
);

/** Props for the ProxiedImage component. */
export interface ProxiedImageProps {
  src: string | StaticImageData | null | undefined;
  alt: string;
  fill?: boolean;
  className?: string;
  sizes?: string;
  width?: number;
  height?: number;
  priority?: boolean;
  fallback?: ReactNode;
}

/**
 * Renders a Next.js Image using the proxy for remote URLs with a fallback.
 *
 * @remarks
 * When `fill` is false, provide explicit `width` and `height` props to avoid
 * CLS. If omitted, the component falls back to the placeholder.
 *
 * @param props - Image rendering options and raw source input.
 * @returns A proxied Next.js Image element or a fallback node.
 */
export function ProxiedImage({
  src,
  alt,
  fill = false,
  className,
  sizes,
  width,
  height,
  priority,
  fallback,
}: ProxiedImageProps) {
  const normalized = typeof src === "string" ? normalizeNextImageSrc(src) : null;
  const imageSrc =
    typeof src === "string"
      ? normalized && isAbsoluteHttpUrl(normalized)
        ? buildImageProxyUrl(normalized)
        : normalized
      : src;

  if (!imageSrc) {
    return fallback ?? DEFAULT_FALLBACK;
  }

  if (!fill && (width == null || height == null)) {
    if (process.env.NODE_ENV === "development") {
      console.warn("ProxiedImage requires width and height when fill is false.", {
        alt,
        height,
        width,
      });
    }
    return fallback ?? DEFAULT_FALLBACK;
  }

  if (fill) {
    return (
      <Image
        src={imageSrc}
        alt={alt}
        fill
        className={className}
        sizes={sizes}
        priority={priority}
      />
    );
  }

  return (
    <Image
      src={imageSrc}
      alt={alt}
      width={width}
      height={height}
      className={className}
      sizes={sizes}
      priority={priority}
    />
  );
}
