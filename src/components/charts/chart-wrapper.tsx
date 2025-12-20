/**
 * @fileoverview Chart wrapper component for dynamically importing Recharts components to reduce initial bundle size.
 */

"use client";

import dynamic from "next/dynamic";
import {
  type ComponentProps,
  type ComponentType,
  cloneElement,
  isValidElement,
  type ReactNode,
  useEffect,
  useState,
} from "react";
import type {
  AreaProps as RechartsAreaProps,
  LineProps as RechartsLineProps,
  ResponsiveContainerProps as RechartsResponsiveContainerProps,
  TooltipProps as RechartsTooltipProps,
  XAxisProps as RechartsXAxisProps,
  YAxisProps as RechartsYAxisProps,
} from "recharts";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

type RechartsModule = typeof import("recharts");

let rechartsPromise: Promise<RechartsModule> | null = null;

function LoadRecharts(): Promise<RechartsModule> {
  rechartsPromise ??= import("recharts").catch((error) => {
    rechartsPromise = null;
    throw error;
  });

  return rechartsPromise;
}

function CreateDynamicComponent<P extends object>(
  loader: () => Promise<ComponentType<P>>
) {
  return dynamic<P>(() => loader().then((Component) => ({ default: Component })), {
    ssr: false,
  });
}

export interface WithRechartsProps {
  children: (recharts: RechartsModule) => ReactNode;
  fallback?: ReactNode;
  loadRecharts?: () => Promise<RechartsModule>;
}

export function WithRecharts({ children, fallback, loadRecharts }: WithRechartsProps) {
  const [recharts, setRecharts] = useState<RechartsModule | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    let isActive = true;
    const loadRechartsModule = loadRecharts ?? LoadRecharts;

    if (retryCount > 0) {
      setLoadError(false);
    }

    loadRechartsModule()
      .then((mod) => {
        if (!isActive) return;
        setRecharts(mod);
      })
      .catch(() => {
        if (!isActive) return;
        setLoadError(true);
      });

    return () => {
      isActive = false;
    };
  }, [loadRecharts, retryCount]);

  if (loadError) {
    const errorContent = (
      <div className="flex flex-col items-center justify-center gap-2">
        <p className="text-sm text-muted-foreground">Failed to load chart.</p>
        <Button
          size="sm"
          type="button"
          variant="outline"
          onClick={() => {
            setRetryCount((count) => count + 1);
          }}
        >
          Retry
        </Button>
      </div>
    );

    if (isValidElement(fallback) && typeof fallback.type === "string") {
      return cloneElement(fallback, undefined, errorContent);
    }

    return <div className="flex items-center justify-center">{errorContent}</div>;
  }

  if (!recharts) {
    return (
      fallback ?? (
        <div className="flex items-center justify-center">
          <LoadingSpinner size="sm" />
        </div>
      )
    );
  }

  return children(recharts);
}

/** Dynamically import chart components to reduce initial bundle size */
export function ResponsiveContainer(props: RechartsResponsiveContainerProps) {
  const placeholderHeight =
    typeof props.height === "number" || typeof props.height === "string"
      ? props.height
      : 256;

  const placeholderWidth =
    typeof props.width === "number" || typeof props.width === "string"
      ? props.width
      : "100%";

  const loadingFallback = (
    <div
      className="flex items-center justify-center"
      style={{ height: placeholderHeight, width: placeholderWidth }}
    >
      <LoadingSpinner size="sm" />
    </div>
  );

  return (
    <WithRecharts fallback={loadingFallback}>
      {(Recharts) => <Recharts.ResponsiveContainer {...props} />}
    </WithRecharts>
  );
}

/**
 * Dynamically import the AreaChart component.
 *
 * @returns The AreaChart component.
 */
export const AreaChart = dynamic(() => LoadRecharts().then((mod) => mod.AreaChart), {
  ssr: false,
});

/**
 * Dynamically import the LineChart component.
 *
 * @returns The LineChart component.
 */
export const LineChart = dynamic(() => LoadRecharts().then((mod) => mod.LineChart), {
  ssr: false,
});

/**
 * Dynamically import the Area component.
 *
 * @returns The Area component.
 */
export const Area = CreateDynamicComponent<RechartsAreaProps>(() =>
  LoadRecharts().then((mod) => mod.Area)
);

/**
 * Dynamically import the Line component.
 *
 * @returns The Line component.
 */
export const Line = CreateDynamicComponent<RechartsLineProps>(() =>
  LoadRecharts().then((mod) => mod.Line)
);

/**
 * Dynamically import the CartesianGrid component.
 *
 * @returns The CartesianGrid component.
 */
export const CartesianGrid = dynamic(
  () => LoadRecharts().then((mod) => mod.CartesianGrid),
  { ssr: false }
);

/**
 * Dynamically import the XAxis component.
 *
 * @returns The XAxis component.
 */
export const XAxis = CreateDynamicComponent<RechartsXAxisProps>(() =>
  LoadRecharts().then((mod) => mod.XAxis)
);

/**
 * Dynamically import the YAxis component.
 *
 * @returns The YAxis component.
 */
export const YAxis = CreateDynamicComponent<RechartsYAxisProps>(() =>
  LoadRecharts().then((mod) => mod.YAxis)
);

/**
 * Dynamically import the Tooltip component.
 *
 * @returns The Tooltip component.
 */
export const Tooltip = CreateDynamicComponent<
  RechartsTooltipProps<string | number, string | number>
>(() => LoadRecharts().then((mod) => mod.Tooltip));

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
