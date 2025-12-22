/**
 * @fileoverview CVA variants for status and urgency colors with Tailwind classes. Provides consistent styling for badges, pills, and status indicators across the application.
 */

import { cva, type VariantProps } from "class-variance-authority";

/**
 * Status/action/urgency variants normalized to a single tone axis so only one
 * bg/text/ring set is ever emitted. `statusVariants` resolves precedence
 * status > action > urgency > tone fallback.
 *
 * Note: Some tone keys intentionally reuse the same color for semantic grouping:
 * - active/create/low/success all use green (positive/affirmative states)
 * - pending/medium both use amber (intermediate/waiting states)
 */

export const TONE_CLASSES = {
  active: "bg-green-50 text-green-700 ring-green-600/20",
  calendar: "bg-indigo-50 text-indigo-700 ring-indigo-600/20",
  create: "bg-green-50 text-green-700 ring-green-600/20",
  deals: "bg-orange-50 text-orange-700 ring-orange-600/20",
  error: "bg-red-50 text-red-700 ring-red-600/20",
  explore: "bg-purple-50 text-purple-700 ring-purple-600/20",
  high: "bg-red-50 text-red-700 ring-red-600/20",
  info: "bg-blue-50 text-blue-700 ring-blue-600/20",
  low: "bg-green-50 text-green-700 ring-green-600/20",
  medium: "bg-amber-50 text-amber-700 ring-amber-600/20",
  pending: "bg-amber-50 text-amber-700 ring-amber-600/20",
  search: "bg-blue-50 text-blue-700 ring-blue-600/20",
  success: "bg-green-50 text-green-700 ring-green-600/20",
  unknown: "bg-slate-50 text-slate-700 ring-slate-600/20",
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
    bg: "bg-green-700/10",
    border: "border-green-700/20",
    text: "text-green-700",
  },
  calendar: {
    bg: "bg-indigo-700/10",
    border: "border-indigo-700/20",
    text: "text-indigo-700",
  },
  create: {
    bg: "bg-green-700/10",
    border: "border-green-700/20",
    text: "text-green-700",
  },
  deals: {
    bg: "bg-orange-700/10",
    border: "border-orange-700/20",
    text: "text-orange-700",
  },
  error: { bg: "bg-red-700/10", border: "border-red-700/20", text: "text-red-700" },
  explore: {
    bg: "bg-purple-700/10",
    border: "border-purple-700/20",
    text: "text-purple-700",
  },
  high: { bg: "bg-red-700/10", border: "border-red-700/20", text: "text-red-700" },
  info: { bg: "bg-blue-700/10", border: "border-blue-700/20", text: "text-blue-700" },
  low: { bg: "bg-green-700/10", border: "border-green-700/20", text: "text-green-700" },
  medium: {
    bg: "bg-amber-700/10",
    border: "border-amber-700/20",
    text: "text-amber-700",
  },
  pending: {
    bg: "bg-amber-700/10",
    border: "border-amber-700/20",
    text: "text-amber-700",
  },
  search: { bg: "bg-blue-700/10", border: "border-blue-700/20", text: "text-blue-700" },
  success: {
    bg: "bg-green-700/10",
    border: "border-green-700/20",
    text: "text-green-700",
  },
  unknown: {
    bg: "bg-slate-700/10",
    border: "border-slate-700/20",
    text: "text-slate-700",
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
  active: "bg-green-500",
  busy: "bg-yellow-500",
  idle: "bg-blue-500",
  offline: "bg-gray-500",
} as const;

export const HANDOFF_STATUS_COLORS = {
  completed: {
    bg: "bg-green-50",
    border: "border-green-200",
    text: "text-green-600",
  },
  failed: {
    bg: "bg-red-50",
    border: "border-red-200",
    text: "text-red-600",
  },
  pending: {
    bg: "bg-yellow-50",
    border: "border-yellow-200",
    text: "text-yellow-600",
  },
} as const;

export const DEFAULT_HANDOFF_STATUS_COLOR = {
  bg: "bg-gray-50",
  border: "border-gray-200",
  text: "text-gray-600",
} as const;

export const TREND_COLORS = {
  decreasing: "text-red-500",
  down: "text-red-500",
  increasing: "text-green-500",
  stable: "text-gray-500",
  up: "text-green-500",
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
