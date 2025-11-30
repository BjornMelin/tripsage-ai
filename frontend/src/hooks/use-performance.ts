/**
 * @fileoverview React hooks for performance monitoring.
 *
 * Provides hooks for measuring page load times, component render times,
 * and web vitals tracking.
 */

"use client";

import { useEffect, useState } from "react";
import type { Metric } from "web-vitals";

interface PerformanceMetrics {
  loadTime: number;
  renderTime: number;
  bundleSize: number;
  isHydrated: boolean;
}

/**
 * Hook for measuring page performance metrics.
 *
 * Tracks load time, render time, bundle size, and hydration status.
 *
 * @returns Performance metrics object
 */
export function usePerformance() {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    bundleSize: 0,
    isHydrated: false,
    loadTime: 0,
    renderTime: 0,
  });

  useEffect(() => {
    // Check if performance API is available
    if (typeof window === "undefined" || !window.performance) return;

    const startTime = performance.now();

    // Measure initial load time
    const loadTime =
      performance.timing?.loadEventEnd - performance.timing?.navigationStart || 0;

    // Measure render time
    const renderTime = performance.now() - startTime;

    // Estimate bundle size from network requests
    let bundleSize = 0;
    if (performance.getEntriesByType) {
      const resourceEntries = performance.getEntriesByType(
        "resource"
      ) as PerformanceResourceTiming[];
      bundleSize = resourceEntries
        .filter((entry) => entry.name.includes(".js") || entry.name.includes(".css"))
        .reduce((total, entry) => total + (entry.transferSize || 0), 0);
    }

    setMetrics({
      bundleSize,
      isHydrated: true,
      loadTime,
      renderTime,
    });

    // Development-only performance logging for local debugging
    if (process.env.NODE_ENV === "development") {
      console.log("Performance Metrics:", {
        bundleSize: `${(bundleSize / 1024).toFixed(2)}KB`,
        loadTime: `${loadTime}ms`,
        renderTime: `${renderTime.toFixed(2)}ms`,
      });
    }
  }, []);

  return metrics;
}

/**
 * Hook to measure component render time.
 *
 * Logs render time to console in development mode only.
 *
 * @param componentName - Name of the component for logging
 */
export function useComponentPerformance(componentName: string) {
  useEffect(() => {
    if (process.env.NODE_ENV !== "development") return;

    const startTime = performance.now();

    return () => {
      const renderTime = performance.now() - startTime;
      console.log(`Component ${componentName} render time: ${renderTime.toFixed(2)}ms`);
    };
  }, [componentName]);
}

// No-op handler for web vitals - metrics are tracked but not logged
const noOpVitalsHandler = (_metric: Metric) => {
  // Web vitals are captured but not logged to console
  // Override this with a custom handler for analytics integration
};

/**
 * Hook to report Web Vitals metrics.
 *
 * Dynamically imports and initializes web-vitals library to track
 * Core Web Vitals (CLS, INP, FCP, LCP, TTFB).
 *
 * @param handler - Optional custom handler for web vitals metrics (e.g., for analytics)
 */
export function useWebVitals(handler?: (metric: Metric) => void) {
  const vitalsHandler = handler ?? noOpVitalsHandler;

  useEffect(() => {
    if (typeof window === "undefined") return;

    // Dynamically import web-vitals to avoid increasing bundle size
    import("web-vitals")
      .then(({ onCLS, onINP, onFCP, onLCP, onTTFB }) => {
        onCLS(vitalsHandler);
        onINP(vitalsHandler);
        onFCP(vitalsHandler);
        onLCP(vitalsHandler);
        onTTFB(vitalsHandler);
      })
      .catch(() => {
        // Silently fail if web-vitals is not available
      });
  }, [vitalsHandler]);
}
