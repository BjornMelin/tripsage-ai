import {
  type ErrorReport,
  ErrorReportSchema,
  type ErrorServiceConfig,
} from "@/types/errors";

/**
 * Error service for logging and reporting errors
 */
class ErrorService {
  private config: ErrorServiceConfig;
  private queue: ErrorReport[] = [];
  private isProcessing = false;

  constructor(config: ErrorServiceConfig) {
    this.config = config;
  }

  /**
   * Report an error with validation
   */
  async reportError(report: ErrorReport): Promise<void> {
    try {
      // Validate the error report using Zod
      const validatedReport = ErrorReportSchema.parse(report);

      if (!this.config.enabled) {
        console.error("Error reported:", validatedReport);
        return;
      }

      // Add to queue for processing
      this.queue.push(validatedReport);

      // Store in localStorage for persistence if enabled
      if (this.config.enableLocalStorage) {
        this.storeErrorLocally(validatedReport);
      }

      // Process the queue
      if (!this.isProcessing) {
        await this.processQueue();
      }
    } catch (error) {
      console.error("Failed to report error:", error);
    }
  }

  /**
   * Process error queue with retry logic
   */
  private async processQueue(): Promise<void> {
    if (this.queue.length === 0) return;

    this.isProcessing = true;

    try {
      while (this.queue.length > 0) {
        const report = this.queue.shift()!;
        await this.sendErrorReport(report);
      }
    } catch (error) {
      console.error("Failed to process error queue:", error);
    } finally {
      this.isProcessing = false;
    }
  }

  /**
   * Send error report to remote service
   */
  private async sendErrorReport(report: ErrorReport, retryCount = 0): Promise<void> {
    const maxRetries = this.config.maxRetries ?? 3;

    try {
      if (!this.config.endpoint) {
        console.error("Error report (no endpoint configured):", report);
        return;
      }

      const response = await fetch(this.config.endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(this.config.apiKey && {
            Authorization: `Bearer ${this.config.apiKey}`,
          }),
        },
        body: JSON.stringify(report),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (error) {
      if (retryCount < maxRetries) {
        // Exponential backoff
        const delay = Math.pow(2, retryCount) * 1000;
        setTimeout(() => {
          this.sendErrorReport(report, retryCount + 1);
        }, delay);
      } else {
        console.error("Failed to send error report after retries:", error);
      }
    }
  }

  /**
   * Store error in localStorage for offline persistence
   */
  private storeErrorLocally(report: ErrorReport): void {
    try {
      const key = `error_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem(key, JSON.stringify(report));

      // Clean up old errors (keep last 10)
      this.cleanupLocalErrors();
    } catch (error) {
      console.error("Failed to store error locally:", error);
    }
  }

  /**
   * Clean up old local errors
   */
  private cleanupLocalErrors(): void {
    try {
      const errorKeys = Object.keys(localStorage)
        .filter((key) => key.startsWith("error_"))
        .sort()
        .reverse();

      // Keep only the last 10 errors
      const keysToRemove = errorKeys.slice(10);
      keysToRemove.forEach((key) => localStorage.removeItem(key));
    } catch (error) {
      console.error("Failed to cleanup local errors:", error);
    }
  }

  /**
   * Create error report from error and additional info
   */
  createErrorReport(
    error: Error,
    errorInfo?: { componentStack?: string },
    additionalInfo?: Partial<ErrorReport>
  ): ErrorReport {
    return {
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack,
        digest: (error as any).digest,
      },
      errorInfo: errorInfo
        ? {
            componentStack: errorInfo.componentStack || "",
          }
        : undefined,
      url: window.location.href,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString(),
      ...additionalInfo,
    };
  }
}

// Default error service instance
export const errorService = new ErrorService({
  enabled: process.env.NODE_ENV === "production",
  endpoint: process.env.NEXT_PUBLIC_ERROR_REPORTING_ENDPOINT,
  apiKey: process.env.NEXT_PUBLIC_ERROR_REPORTING_API_KEY,
  maxRetries: 3,
  enableLocalStorage: true,
});

export { ErrorService };
