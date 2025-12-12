/**
 * @fileoverview Centralized Streamdown defaults for TripSage.
 *
 * Streamdown is used as the markdown renderer for AI Elements Response. We keep
 * the built-in remark/rehype pipeline (GFM, math, CJK-friendly parsing, Shiki,
 * Mermaid) but tighten link/image protocol handling for AI-generated content.
 */

import type { MermaidConfig, MermaidOptions, StreamdownProps } from "streamdown";
import { defaultRehypePlugins, defaultRemarkPlugins } from "streamdown";
import type { Plugin } from "unified";

type HardenOptions = {
  allowedImagePrefixes?: string[];
  allowedLinkPrefixes?: string[];
  allowedProtocols?: string[];
  defaultOrigin?: string | undefined;
  allowDataImages?: boolean;
};

const hardenRaw = defaultRehypePlugins.harden as unknown;
const hardenFn = (Array.isArray(hardenRaw) ? hardenRaw[0] : hardenRaw) as Plugin;
const hardenDefaults =
  Array.isArray(hardenRaw) && hardenRaw[1] != null && typeof hardenRaw[1] === "object"
    ? (hardenRaw[1] as HardenOptions)
    : {};

export const streamdownShikiTheme: NonNullable<StreamdownProps["shikiTheme"]> = [
  "github-light",
  "github-dark",
];

export const streamdownControls: NonNullable<StreamdownProps["controls"]> = {
  code: true,
  mermaid: {
    copy: true,
    download: true,
    fullscreen: true,
    panZoom: true,
  },
  table: true,
};

const mermaidConfig: MermaidConfig = {
  theme: "base",
  themeVariables: {
    fontFamily: "Inter, system-ui, sans-serif",
    lineColor: "hsl(var(--border))",
    primaryBorderColor: "hsl(var(--border))",
    primaryColor: "hsl(var(--muted))",
    primaryTextColor: "hsl(var(--foreground))",
    secondaryColor: "hsl(var(--background))",
    tertiaryColor: "hsl(var(--accent))",
  },
};

export const streamdownMermaid: MermaidOptions = { config: mermaidConfig };

export const streamdownRemarkPlugins: NonNullable<StreamdownProps["remarkPlugins"]> =
  Object.values(defaultRemarkPlugins);

export const streamdownRehypePlugins: NonNullable<StreamdownProps["rehypePlugins"]> = [
  defaultRehypePlugins.raw,
  defaultRehypePlugins.katex,
  [
    hardenFn,
    {
      ...hardenDefaults,
      allowDataImages: false,
      allowedProtocols: ["http", "https", "mailto"],
    },
  ],
];
