/**
 * @fileoverview React hooks for performance monitoring.
 */

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Metric } from "web-vitals";
import { patchPerformanceMeasureForPrerender } from "@/lib/performance/patch-performance-measure";

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

    // Measure initial load time using Navigation Timing L2
    let loadTime = 0;
    const navEntry = performance.getEntriesByType?.("navigation")?.[0];
    if (navEntry) {
      const navTiming = navEntry as PerformanceNavigationTiming;
      if (Number.isFinite(navTiming.loadEventEnd) && navTiming.loadEventEnd > 0) {
        loadTime = navTiming.loadEventEnd - navTiming.startTime;
      } else {
        // Page load not complete yet - use current time as approximation
        loadTime = performance.now();
      }
    }

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
const noOpVitalsHandler: (metric: Metric) => void = () => {
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
  const handlerRef = useRef(handler ?? noOpVitalsHandler);

  useEffect(() => {
    handlerRef.current = handler ?? noOpVitalsHandler;
  }, [handler]);

  const stableHandler = useCallback((metric: Metric) => {
    handlerRef.current(metric);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;

    patchPerformanceMeasureForPrerender();

    let isCancelled = false;

    const init = () => {
      // Dynamically import web-vitals to avoid increasing bundle size.
      // Some browsers may throw when measuring during prerender; we defer init
      // until activation to avoid noisy `performance.measure` errors.
      import("web-vitals")
        .then(({ onCLS, onINP, onFCP, onLCP, onTTFB }) => {
          if (isCancelled) return;
          onCLS(stableHandler);
          onINP(stableHandler);
          onFCP(stableHandler);
          onLCP(stableHandler);
          onTTFB(stableHandler);
        })
        .catch(() => {
          // Silently fail if web-vitals is not available
        });
    };

    if ("prerendering" in document && document.prerendering) {
      const handlePrerenderingChange = () => {
        if (isCancelled) return;
        init();
      };

      document.addEventListener("prerenderingchange", handlePrerenderingChange, {
        once: true,
      });

      return () => {
        isCancelled = true;
        document.removeEventListener("prerenderingchange", handlePrerenderingChange);
      };
    }

    init();

    return () => {
      isCancelled = true;
    };
  }, [stableHandler]);
}
