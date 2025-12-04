/**
 * @fileoverview CVA variants for status and urgency colors with Tailwind classes.
 * Provides consistent styling for badges, pills, and status indicators across the application.
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

const TONE_CLASSES = {
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
