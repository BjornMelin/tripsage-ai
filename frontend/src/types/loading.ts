/**
 * @fileoverview Loading state types and schemas for UI components.
 */
import { z } from "zod";

/**
 * Loading state schemas for validation
 */
export const LOADING_STATE_SCHEMA = z.object({
  isLoading: z.boolean(),
  message: z.string().optional(),
  progress: z.number().min(0).max(100).optional(),
});

export const SKELETON_CONFIG_SCHEMA = z.object({
  animate: z.boolean().default(true),
  avatar: z.boolean().optional(),
  className: z.string().optional(),
  height: z.union([z.string(), z.number()]).optional(),
  lines: z.number().min(1).max(20).optional(),
  width: z.union([z.string(), z.number()]).optional(),
});

export const LOADING_SPINNER_CONFIG_SCHEMA = z.object({
  className: z.string().optional(),
  color: z.string().optional(),
  size: z.enum(["sm", "md", "lg", "xl"]).default("md"),
  variant: z.enum(["default", "dots", "bars", "pulse"]).default("default"),
});

/**
 * TypeScript types derived from schemas
 */
export type LoadingState = z.infer<typeof LOADING_STATE_SCHEMA>;
export type SkeletonConfig = z.infer<typeof SKELETON_CONFIG_SCHEMA>;
export type LoadingSpinnerConfig = z.infer<typeof LOADING_SPINNER_CONFIG_SCHEMA>;

/**
 * Content type enums for skeleton variations
 */
export enum SkeletonType {
  Text = "text",
  Paragraph = "paragraph",
  Card = "card",
  List = "list",
  Avatar = "avatar",
  Image = "image",
  Button = "button",
  Form = "form",
  Table = "table",
  Chart = "chart",
}

/**
 * Loading context types
 */
export interface LoadingContextValue {
  isLoading: boolean;
  message?: string;
  progress?: number;
  setLoading: (loading: boolean, message?: string, progress?: number) => void;
}

/**
 * Props interfaces for components
 */
export interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  lines?: number;
  className?: string;
  animate?: boolean;
  "aria-label"?: string;
}

export interface LoadingSpinnerBaseProps {
  size?: "sm" | "md" | "lg" | "xl";
  variant?: "default" | "dots" | "bars" | "pulse";
  color?: string;
  className?: string;
  "aria-label"?: string;
}

export interface LoadingOverlayProps {
  isVisible: boolean;
  message?: string;
  progress?: number;
  spinner?: LoadingSpinnerBaseProps;
  className?: string;
}

export interface LoadingStateProps {
  isLoading: boolean;
  skeleton?: React.ReactNode;
  spinner?: LoadingSpinnerBaseProps;
  children: React.ReactNode;
  className?: string;
}
