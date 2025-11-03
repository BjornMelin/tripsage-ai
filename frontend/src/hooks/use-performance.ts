/**
 * @fileoverview React hooks for performance monitoring.
 *
 * Provides hooks for measuring page load times, component render times,
 * and web vitals tracking.
 */

"use client";

import { useEffect, useState } from "react";

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

    // Report to console in development
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
 * Logs render time to console in development mode.
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

/**
 * Hook to report Web Vitals metrics.
 *
 * Dynamically imports and initializes web-vitals library to track
 * Core Web Vitals (CLS, INP, FCP, LCP, TTFB).
 */
export function useWebVitals() {
  useEffect(() => {
    if (typeof window === "undefined") return;

    // Dynamically import web-vitals to avoid increasing bundle size
    import("web-vitals")
      .then(({ onCLS, onINP, onFCP, onLCP, onTTFB }) => {
        onCLS(console.log);
        onINP(console.log); // Replaced getFID with onINP in v5
        onFCP(console.log);
        onLCP(console.log);
        onTTFB(console.log);
      })
      .catch(() => {
        // Silently fail if web-vitals is not available
      });
  }, []);
}
