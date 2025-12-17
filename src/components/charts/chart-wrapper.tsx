/**
 * @fileoverview Chart wrapper component for dynamically importing Recharts components to reduce initial bundle size.
 */

"use client";

import dynamic from "next/dynamic";
import type { ComponentProps, ComponentType } from "react";
import type {
  AreaProps as RechartsAreaProps,
  LineProps as RechartsLineProps,
  TooltipProps as RechartsTooltipProps,
  XAxisProps as RechartsXAxisProps,
  YAxisProps as RechartsYAxisProps,
} from "recharts";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

function CreateDynamicComponent<P extends object>(
  loader: () => Promise<ComponentType<P>>
) {
  return dynamic<P>(() => loader().then((Component) => ({ default: Component })), {
    ssr: false,
  });
}

/** Dynamically import chart components to reduce initial bundle size */
export const ResponsiveContainer = dynamic(
  () => import("recharts").then((mod) => mod.ResponsiveContainer),
  {
    loading: () => (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="sm" />
      </div>
    ),
    ssr: false,
  }
);

/**
 * Dynamically import the AreaChart component.
 *
 * @returns The AreaChart component.
 */
export const AreaChart = dynamic(
  () => import("recharts").then((mod) => mod.AreaChart),
  { ssr: false }
);

/**
 * Dynamically import the LineChart component.
 *
 * @returns The LineChart component.
 */
export const LineChart = dynamic(
  () => import("recharts").then((mod) => mod.LineChart),
  { ssr: false }
);

/**
 * Dynamically import the Area component.
 *
 * @returns The Area component.
 */
export const Area = CreateDynamicComponent<RechartsAreaProps>(() =>
  import("recharts").then((mod) => mod.Area)
);

/**
 * Dynamically import the Line component.
 *
 * @returns The Line component.
 */
export const Line = CreateDynamicComponent<RechartsLineProps>(() =>
  import("recharts").then((mod) => mod.Line)
);

/**
 * Dynamically import the CartesianGrid component.
 *
 * @returns The CartesianGrid component.
 */
export const CartesianGrid = dynamic(
  () => import("recharts").then((mod) => mod.CartesianGrid),
  { ssr: false }
);

/**
 * Dynamically import the XAxis component.
 *
 * @returns The XAxis component.
 */
export const XAxis = CreateDynamicComponent<RechartsXAxisProps>(() =>
  import("recharts").then((mod) => mod.XAxis)
);

/**
 * Dynamically import the YAxis component.
 *
 * @returns The YAxis component.
 */
export const YAxis = CreateDynamicComponent<RechartsYAxisProps>(() =>
  import("recharts").then((mod) => mod.YAxis)
);

/**
 * Dynamically import the Tooltip component.
 *
 * @returns The Tooltip component.
 */
export const Tooltip = CreateDynamicComponent<
  RechartsTooltipProps<string | number, string | number>
>(() => import("recharts").then((mod) => mod.Tooltip));

/** Export types for better TypeScript support */
export type ResponsiveContainerProps = ComponentProps<typeof ResponsiveContainer>;
export type AreaChartProps = ComponentProps<typeof AreaChart>;
export type LineChartProps = ComponentProps<typeof LineChart>;
export type AreaProps = ComponentProps<typeof Area>;
export type LineProps = ComponentProps<typeof Line>;
export type CartesianGridProps = ComponentProps<typeof CartesianGrid>;
export type XAxisProps = ComponentProps<typeof XAxis>;
export type YAxisProps = ComponentProps<typeof YAxis>;
export type TooltipProps = ComponentProps<typeof Tooltip>;
