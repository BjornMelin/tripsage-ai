/**
 * @fileoverview Canonical Streamdown v2 Markdown renderer with streaming and security support.
 */

"use client";

import { code as codePlugin } from "@streamdown/code";
import { math as mathPlugin } from "@streamdown/math";
import { mermaid as mermaidPlugin } from "@streamdown/mermaid";
import { type ComponentProps, memo, useMemo } from "react";
import {
  type ControlsConfig,
  type MermaidOptions,
  Streamdown,
  type StreamdownProps,
  defaultRehypePlugins as streamdownDefaultRehypePlugins,
  defaultRemarkPlugins as streamdownDefaultRemarkPlugins,
} from "streamdown";
import type { Pluggable, PluggableList, Plugin } from "unified";
import { z } from "zod";
import { getClientOrigin } from "@/lib/url/client-origin";
import { cn } from "@/lib/utils";

/** Security profile controlling allowed content sources and sanitization strictness. */
export type MarkdownSecurityProfile = "ai" | "user" | "trusted";

/**
 * Props for the Markdown component.
 * Extends Streamdown props with security profile and streaming controls.
 */
export type MarkdownProps = {
  content: string;
  className?: string;
  mode?: NonNullable<StreamdownProps["mode"]>;
  isAnimating?: boolean;
  caret?: StreamdownProps["caret"];
  remend?: StreamdownProps["remend"];
  controls?: StreamdownProps["controls"];
  mermaid?: StreamdownProps["mermaid"];
  remarkPlugins?: StreamdownProps["remarkPlugins"];
  rehypePlugins?: StreamdownProps["rehypePlugins"];
  securityProfile?: MarkdownSecurityProfile;
  components?: StreamdownProps["components"];
} & Omit<
  ComponentProps<typeof Streamdown>,
  "children" | "className" | "components" | "plugins" | "linkSafety" | "allowedTags"
>;

const HardenOptionsSchema = z.looseObject({
  allowDataImages: z.boolean().optional(),
  allowedImagePrefixes: z.array(z.string()).optional(),
  allowedLinkPrefixes: z.array(z.string()).optional(),
  allowedProtocols: z.array(z.string()).optional(),
  defaultOrigin: z.string().optional(),
});

type HardenOptions = z.infer<typeof HardenOptionsSchema>;
type UnifiedPlugin = Plugin<unknown[]>;
type PluggableTuple = [plugin: UnifiedPlugin, ...parameters: unknown[]];

// biome-ignore lint/style/useNamingConvention: helper function uses camelCase.
function isPluggableTuple(value: Pluggable): value is PluggableTuple {
  return Array.isArray(value);
}

// biome-ignore lint/style/useNamingConvention: helper function uses camelCase.
function isUnifiedPlugin(value: unknown): value is UnifiedPlugin {
  return typeof value === "function";
}

// biome-ignore lint/style/useNamingConvention: helper function uses camelCase.
function resolvePluginDefaults(plugin: Pluggable): {
  plugin: UnifiedPlugin;
  defaults: HardenOptions;
} {
  if (isPluggableTuple(plugin)) {
    const parsed = HardenOptionsSchema.safeParse(plugin[1]);
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

// biome-ignore lint/style/useNamingConvention: helper function uses camelCase.
function parseCommaSeparatedList(value: string | undefined): string[] {
  if (!value) return [];
  return value
    .split(",")
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0);
}

const DefaultShikiTheme: NonNullable<StreamdownProps["shikiTheme"]> = [
  "github-light",
  "github-dark",
];

const DefaultControls: NonNullable<StreamdownProps["controls"]> = {
  code: true,
  mermaid: {
    copy: true,
    download: true,
    fullscreen: true,
    panZoom: true,
  },
  table: true,
};

const DefaultMermaid: NonNullable<StreamdownProps["mermaid"]> = {
  config: {
    theme: "base",
    themeVariables: {
      fontFamily: "Inter, system-ui, sans-serif",
    },
  },
};

const DefaultRemend: NonNullable<StreamdownProps["remend"]> = {
  bold: true,
  boldItalic: true,
  images: true,
  inlineCode: true,
  italic: true,
  katex: true,
  links: true,
  setextHeadings: true,
  strikethrough: true,
} satisfies NonNullable<StreamdownProps["remend"]>;

const DefaultRemarkPlugins: NonNullable<StreamdownProps["remarkPlugins"]> =
  Object.values(streamdownDefaultRemarkPlugins);

const { plugin: HardenFn, defaults: HardenDefaults } = resolvePluginDefaults(
  streamdownDefaultRehypePlugins.harden
);

// biome-ignore lint/style/useNamingConvention: helper function uses camelCase.
function createHardenOptions({
  profile,
  origin,
}: {
  profile: MarkdownSecurityProfile;
  origin: string;
}): HardenOptions {
  const extraLinkPrefixes = parseCommaSeparatedList(
    process.env.NEXT_PUBLIC_STREAMDOWN_ALLOWED_LINK_PREFIXES
  );

  // By default we allow any http(s)/mailto link (protocol-hardened). If a deployment
  // wants to tighten this further, it can provide an allowlist via env.
  const allowedLinkPrefixes =
    extraLinkPrefixes.length > 0 ? [origin, ...extraLinkPrefixes] : undefined;

  const allowedImagePrefixes = [
    origin,
    ...parseCommaSeparatedList(
      process.env.NEXT_PUBLIC_STREAMDOWN_ALLOWED_IMAGE_PREFIXES
    ),
  ];

  if (profile === "trusted") {
    const base: HardenOptions = {
      ...HardenDefaults,
      allowDataImages: true,
      allowedProtocols: ["http", "https", "mailto"],
      defaultOrigin: origin,
    };

    if (allowedImagePrefixes.length > 0)
      base.allowedImagePrefixes = allowedImagePrefixes;
    if (allowedLinkPrefixes) base.allowedLinkPrefixes = allowedLinkPrefixes;

    return base;
  }

  // AI/user content is treated as untrusted by default.
  const base: HardenOptions = {
    ...HardenDefaults,
    allowDataImages: false,
    allowedProtocols: ["http", "https", "mailto"],
    defaultOrigin: origin,
  };

  if (allowedImagePrefixes.length > 0) base.allowedImagePrefixes = allowedImagePrefixes;
  if (allowedLinkPrefixes) base.allowedLinkPrefixes = allowedLinkPrefixes;

  return base;
}

// biome-ignore lint/style/useNamingConvention: helper function uses camelCase.
function createDefaultRehypePlugins({
  profile,
  origin,
}: {
  profile: MarkdownSecurityProfile;
  origin: string;
}): PluggableList {
  const hardenOptions = createHardenOptions({ origin, profile });

  // For untrusted content, we intentionally omit `defaultRehypePlugins.raw`.
  // This means raw HTML is rendered as text instead of becoming DOM nodes.
  if (profile !== "trusted") {
    return [[HardenFn, hardenOptions]];
  }

  return [
    streamdownDefaultRehypePlugins.raw,
    streamdownDefaultRehypePlugins.sanitize,
    [HardenFn, hardenOptions],
  ];
}

type MarkdownLinkProps = ComponentProps<"a"> & { node?: unknown };

function TripSageMarkdownLink({
  children,
  className,
  href,
  node: _node,
  ...rest
}: MarkdownLinkProps) {
  const isIncomplete = href === "streamdown:incomplete-link";
  return (
    <a
      {...rest}
      className={cn("wrap-anywhere font-medium text-primary underline", className)}
      data-incomplete={isIncomplete}
      data-streamdown="link"
      href={href}
      rel="noopener noreferrer"
      target="_blank"
    >
      {children}
    </a>
  );
}

export const Markdown = memo(
  ({
    className,
    content,
    mode = "streaming",
    isAnimating = false,
    caret,
    remend = DefaultRemend,
    controls = DefaultControls,
    mermaid = DefaultMermaid,
    remarkPlugins = DefaultRemarkPlugins,
    rehypePlugins,
    securityProfile = "ai",
    components,
    ...props
  }: MarkdownProps) => {
    const origin = getClientOrigin();
    const resolvedCaret =
      caret ?? (mode === "streaming" && isAnimating ? "block" : undefined);

    // Disable controls while streaming animation is active to avoid interacting with
    // partially-rendered content and to reduce visual churn.
    const resolvedControls: ControlsConfig =
      mode === "streaming" && isAnimating ? false : controls;

    const resolvedRehypePlugins = useMemo<PluggableList>(() => {
      return (
        rehypePlugins ??
        createDefaultRehypePlugins({ origin, profile: securityProfile })
      );
    }, [origin, rehypePlugins, securityProfile]);

    return (
      <Streamdown
        className={cn("max-w-none", className)}
        caret={resolvedCaret}
        components={{ ...(components ?? {}), a: TripSageMarkdownLink }}
        controls={resolvedControls}
        isAnimating={isAnimating}
        linkSafety={{ enabled: false }}
        mermaid={mermaid as MermaidOptions}
        mode={mode}
        plugins={{ code: codePlugin, math: mathPlugin, mermaid: mermaidPlugin }}
        parseIncompleteMarkdown={mode === "streaming"}
        rehypePlugins={resolvedRehypePlugins}
        remarkPlugins={remarkPlugins}
        remend={remend}
        shikiTheme={DefaultShikiTheme}
        {...props}
      >
        {content}
      </Streamdown>
    );
  }
);

Markdown.displayName = "Markdown";
