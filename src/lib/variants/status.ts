/**
 * @fileoverview CVA variants for status and urgency colors with Tailwind classes. Provides consistent styling for badges, pills, and status indicators across the application.
 */

import { cva, type VariantProps } from "class-variance-authority";

/**
 * Status/action/urgency variants normalized to a single tone axis so only one
 * bg/text/ring set is ever emitted. `statusVariants` resolves precedence
 * status > action > urgency > tone fallback.
 *
 * Note: Some tone keys intentionally reuse the same semantic color group:
 * - active/create/low/success use success (positive/affirmative states)
 * - pending/medium use warning (intermediate/waiting states)
 */

export const TONE_CLASSES = {
  active: "bg-success/10 text-success ring-success/20",
  calendar: "bg-info/10 text-info ring-info/20",
  create: "bg-success/10 text-success ring-success/20",
  deals: "bg-warning/10 text-warning ring-warning/20",
  error: "bg-destructive/10 text-destructive ring-destructive/20",
  explore: "bg-highlight/10 text-highlight ring-highlight/20",
  high: "bg-destructive/10 text-destructive ring-destructive/20",
  info: "bg-info/10 text-info ring-info/20",
  low: "bg-success/10 text-success ring-success/20",
  medium: "bg-warning/10 text-warning ring-warning/20",
  pending: "bg-warning/10 text-warning ring-warning/20",
  search: "bg-info/10 text-info ring-info/20",
  success: "bg-success/10 text-success ring-success/20",
  unknown: "bg-muted text-muted-foreground ring-border/40",
} as const;

const statusToneVariants = cva(
  "inline-flex items-center rounded-md px-2 py-1 text-xs font-medium",
  {
    defaultVariants: {
      ring: "default",
      tone: "unknown",
    },
    variants: {
      ring: {
        default: "ring-1 ring-inset",
        none: "",
      },
      tone: TONE_CLASSES,
    },
  }
);

export type ActionVariant = "calendar" | "create" | "deals" | "explore" | "search";
export type StatusVariant = "active" | "error" | "info" | "pending" | "success";
export type UrgencyVariant = "high" | "medium" | "low";
export type ToneVariant = ActionVariant | StatusVariant | UrgencyVariant | "unknown";

export type StatusVariantInput = {
  action?: ActionVariant;
  status?: StatusVariant;
  urgency?: UrgencyVariant;
  tone?: ToneVariant;
  excludeRing?: boolean;
};

/**
 * Color set for a tone variant with text, background, and border colors.
 */
export type ToneColorSet = {
  text: string;
  bg: string;
  border: string;
};

/**
 * Static mapping of ToneVariant to ToneColorSet with explicit Tailwind classes.
 * Ensures all classes are statically present for Tailwind JIT compilation.
 */
export const TONE_COLOR_SETS: Record<ToneVariant, ToneColorSet> = {
  active: {
    bg: "bg-success/10",
    border: "border-success/20",
    text: "text-success",
  },
  calendar: {
    bg: "bg-info/10",
    border: "border-info/20",
    text: "text-info",
  },
  create: {
    bg: "bg-success/10",
    border: "border-success/20",
    text: "text-success",
  },
  deals: {
    bg: "bg-warning/10",
    border: "border-warning/20",
    text: "text-warning",
  },
  error: {
    bg: "bg-destructive/10",
    border: "border-destructive/20",
    text: "text-destructive",
  },
  explore: {
    bg: "bg-highlight/10",
    border: "border-highlight/20",
    text: "text-highlight",
  },
  high: {
    bg: "bg-destructive/10",
    border: "border-destructive/20",
    text: "text-destructive",
  },
  info: { bg: "bg-info/10", border: "border-info/20", text: "text-info" },
  low: { bg: "bg-success/10", border: "border-success/20", text: "text-success" },
  medium: {
    bg: "bg-warning/10",
    border: "border-warning/20",
    text: "text-warning",
  },
  pending: {
    bg: "bg-warning/10",
    border: "border-warning/20",
    text: "text-warning",
  },
  search: { bg: "bg-info/10", border: "border-info/20", text: "text-info" },
  success: {
    bg: "bg-success/10",
    border: "border-success/20",
    text: "text-success",
  },
  unknown: {
    bg: "bg-muted",
    border: "border-border",
    text: "text-muted-foreground",
  },
};

/**
 * Get the static color set for a tone variant.
 *
 * @param tone The tone variant to get colors for.
 * @returns Object with text, bg, and border color classes.
 */
export function getToneColors(tone: ToneVariant): ToneColorSet {
  return TONE_COLOR_SETS[tone] ?? TONE_COLOR_SETS.unknown;
}

export const AGENT_STATUS_COLORS = {
  active: "bg-success",
  busy: "bg-warning",
  idle: "bg-info",
  offline: "bg-muted-foreground",
} as const;

export const HANDOFF_STATUS_COLORS = {
  completed: {
    bg: "bg-success/10",
    border: "border-success/20",
    text: "text-success",
  },
  failed: {
    bg: "bg-destructive/10",
    border: "border-destructive/20",
    text: "text-destructive",
  },
  pending: {
    bg: "bg-warning/10",
    border: "border-warning/20",
    text: "text-warning",
  },
} as const;

export const DEFAULT_HANDOFF_STATUS_COLOR = {
  bg: "bg-muted",
  border: "border-border",
  text: "text-muted-foreground",
} as const;

export const TREND_COLORS = {
  decreasing: "text-destructive",
  down: "text-destructive",
  increasing: "text-success",
  stable: "text-muted-foreground",
  up: "text-success",
} as const;

export type StatusVariantProps = VariantProps<typeof statusToneVariants> &
  StatusVariantInput;

/** Type guard to check if a value is a valid ToneVariant. */
function isToneVariant(value: string): value is ToneVariant {
  return value in TONE_CLASSES;
}

const resolveTone = (input: StatusVariantInput): ToneVariant => {
  const candidate = input.status ?? input.action ?? input.urgency ?? input.tone;
  if (candidate && isToneVariant(candidate)) {
    return candidate;
  }
  return "unknown";
};

export const statusVariants = (input: StatusVariantInput = {}) => {
  const tone = resolveTone(input);
  const ring = input.excludeRing ? "none" : "default";
  return statusToneVariants({ ring, tone });
};
