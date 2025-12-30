/**
 * @fileoverview Centralized Streamdown defaults for TripSage.
 */

import type { MermaidConfig, MermaidOptions, StreamdownProps } from "streamdown";
import { defaultRehypePlugins, defaultRemarkPlugins } from "streamdown";
import type { Pluggable, Plugin } from "unified";
import { z } from "zod";

const hardenOptionsSchema = z.looseObject({
  allowDataImages: z.boolean().optional(),
  allowedImagePrefixes: z.array(z.string()).optional(),
  allowedLinkPrefixes: z.array(z.string()).optional(),
  allowedProtocols: z.array(z.string()).optional(),
  defaultOrigin: z.string().optional(),
});

type HardenOptions = z.infer<typeof hardenOptionsSchema>;

type UnifiedPlugin = Plugin<unknown[]>;
type PluggableTuple = [plugin: UnifiedPlugin, ...parameters: unknown[]];

function isPluggableTuple(value: Pluggable): value is PluggableTuple {
  return Array.isArray(value);
}

function isUnifiedPlugin(value: unknown): value is UnifiedPlugin {
  return typeof value === "function";
}

function resolvePluginDefaults(plugin: Pluggable): {
  plugin: UnifiedPlugin;
  defaults: HardenOptions;
} {
  if (isPluggableTuple(plugin)) {
    const parsed = hardenOptionsSchema.safeParse(plugin[1]);
    const defaults = parsed.success ? parsed.data : {};
    if (!isUnifiedPlugin(plugin[0])) {
      throw new Error("Invalid Streamdown rehype plugin configuration");
    }
    return { defaults, plugin: plugin[0] };
  }

  if (!isUnifiedPlugin(plugin)) {
    throw new Error("Invalid Streamdown rehype plugin configuration");
  }

  return { defaults: {}, plugin };
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
