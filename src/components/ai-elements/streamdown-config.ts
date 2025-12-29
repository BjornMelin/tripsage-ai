/**
 * @fileoverview Centralized Streamdown defaults for TripSage.
 */

import type { MermaidConfig, MermaidOptions, StreamdownProps } from "streamdown";
import { defaultRehypePlugins, defaultRemarkPlugins } from "streamdown";
import type { Pluggable, Plugin } from "unified";

type HardenOptions = {
  allowedImagePrefixes?: string[];
  allowedLinkPrefixes?: string[];
  allowedProtocols?: string[];
  defaultOrigin?: string | undefined;
  allowDataImages?: boolean;
};

type UnifiedPlugin = Plugin<unknown[]>;
type PluggableTuple = [plugin: UnifiedPlugin, ...parameters: unknown[]];

function isPluggableTuple(value: Pluggable): value is PluggableTuple {
  return Array.isArray(value);
}

function resolvePluginDefaults(plugin: Pluggable): {
  plugin: UnifiedPlugin;
  defaults: HardenOptions;
} {
  if (isPluggableTuple(plugin)) {
    const defaults =
      plugin[1] != null && typeof plugin[1] === "object"
        ? (plugin[1] as HardenOptions)
        : {};
    return { defaults, plugin: plugin[0] };
  }

  return { defaults: {}, plugin: plugin as UnifiedPlugin };
}

const { plugin: hardenFn, defaults: hardenDefaults } = resolvePluginDefaults(
  defaultRehypePlugins.harden
);

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
