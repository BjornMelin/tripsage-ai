/**
 * @fileoverview Client-side helper for rendering proxied images with fallback.
 */

"use client";

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

export interface ProxiedImageProps {
  src: unknown;
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
  const normalized = normalizeNextImageSrc(src);
  const imageSrc =
    normalized && isAbsoluteHttpUrl(normalized)
      ? buildImageProxyUrl(normalized)
      : normalized;

  if (!imageSrc) {
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
      width={width ?? 1}
      height={height ?? 1}
      className={className}
      sizes={sizes}
      priority={priority}
    />
  );
}
