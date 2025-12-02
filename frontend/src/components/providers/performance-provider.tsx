/**
 * @fileoverview Wrapper for performance monitoring provider.
 */

"use client";

import type { ReactNode } from "react";
import { useWebVitals } from "@/hooks/use-performance";

/** Props for the PerformanceMonitor component. */
interface PerformanceMonitorProps {
  children: ReactNode;
}

/**
 * PerformanceMonitor component.
 *
 * Initializes Web Vitals monitoring and returns the children.
 *
 * @param children - React children to wrap.
 * @returns The children wrapped in a PerformanceMonitor component.
 */
export function PerformanceMonitor({ children }: PerformanceMonitorProps) {
  // Initialize Web Vitals monitoring
  useWebVitals();

  return <>{children}</>;
}
