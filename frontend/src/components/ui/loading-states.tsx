import * as React from "react";
import { cn } from "@/lib/utils";
import { LoadingSpinner } from "./loading-spinner";

/**
 * Loading overlay component for full-screen or container loading
 */
export interface LoadingOverlayProps {
  isVisible: boolean;
  message?: string;
  progress?: number;
  spinnerProps?: React.ComponentProps<typeof LoadingSpinner>;
  className?: string;
  backdrop?: boolean;
  variant?: "overlay" | "page" | "fullscreen";
}

export const LoadingOverlay = React.forwardRef<HTMLDivElement, LoadingOverlayProps>(
  (
    {
      isVisible,
      message,
      progress,
      spinnerProps,
      className,
      backdrop = true,
      variant = "overlay",
      ...props
    },
    ref
  ) => {
    if (!isVisible) return null;

    const isFullScreen = variant === "page" || variant === "fullscreen";
    const baseClasses = isFullScreen
      ? "fixed inset-0 z-50 flex flex-col items-center justify-center bg-background"
      : "absolute inset-0 z-50 flex flex-col items-center justify-center";

    const backdropClasses =
      backdrop && !isFullScreen ? "bg-background/80 backdrop-blur-sm" : "";

    return (
      <div
        ref={ref}
        className={cn(baseClasses, backdropClasses, className)}
        role="status"
        aria-live="polite"
        aria-label={message || "Loading"}
        {...props}
      >
        <div className="flex flex-col items-center space-y-6">
          <div className="relative">
            <LoadingSpinner
              {...spinnerProps}
              size={isFullScreen ? "xl" : spinnerProps?.size}
            />
          </div>

          <div className="text-center space-y-2">
            {message && (
              <h2
                className={cn(
                  "text-center max-w-sm",
                  isFullScreen
                    ? "text-lg font-semibold"
                    : "text-sm text-muted-foreground"
                )}
              >
                {message}
              </h2>
            )}

            {typeof progress === "number" && (
              <div className={cn("space-y-2", isFullScreen ? "w-64" : "w-48")}>
                <div
                  className={cn(
                    "flex justify-between text-muted-foreground",
                    isFullScreen ? "text-sm" : "text-xs"
                  )}
                >
                  <span>{isFullScreen ? "Loading" : "Progress"}</span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300 ease-out"
                    style={{
                      width: `${Math.min(100, Math.max(0, progress))}%`,
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }
);

LoadingOverlay.displayName = "LoadingOverlay";

/**
 * Loading state wrapper that shows skeleton or spinner while loading
 */
export interface LoadingStateProps {
  isLoading: boolean;
  skeleton?: React.ReactNode;
  spinner?: React.ComponentProps<typeof LoadingSpinner>;
  children: React.ReactNode;
  className?: string;
  fallback?: React.ReactNode;
}

export const LoadingState = React.forwardRef<HTMLDivElement, LoadingStateProps>(
  ({ isLoading, skeleton, spinner, children, className, fallback, ...props }, ref) => {
    if (isLoading) {
      if (skeleton) {
        return (
          <div ref={ref} className={className} {...props}>
            {skeleton}
          </div>
        );
      }

      if (fallback) {
        return (
          <div ref={ref} className={className} {...props}>
            {fallback}
          </div>
        );
      }

      return (
        <div
          ref={ref}
          className={cn("flex items-center justify-center p-8", className)}
          {...props}
        >
          <LoadingSpinner {...spinner} />
        </div>
      );
    }

    return (
      <div ref={ref} className={className} {...props}>
        {children}
      </div>
    );
  }
);

LoadingState.displayName = "LoadingState";

/**
 * Button loading state component
 */
export interface LoadingButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  isLoading?: boolean;
  loadingText?: string;
  spinnerProps?: React.ComponentProps<typeof LoadingSpinner>;
  children: React.ReactNode;
}

export const LoadingButton = React.forwardRef<HTMLButtonElement, LoadingButtonProps>(
  (
    {
      isLoading = false,
      loadingText,
      spinnerProps = { size: "sm" },
      children,
      disabled,
      className,
      ...props
    },
    ref
  ) => {
    return (
      <button
        type="button"
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(
          "inline-flex items-center justify-center gap-2 transition-opacity",
          isLoading && "cursor-not-allowed opacity-70",
          className
        )}
        aria-disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && <LoadingSpinner {...spinnerProps} />}
        {isLoading && loadingText ? loadingText : children}
      </button>
    );
  }
);

LoadingButton.displayName = "LoadingButton";

/**
 * Container loading component for inline loading states
 */
export interface LoadingContainerProps {
  isLoading: boolean;
  children: React.ReactNode;
  loadingMessage?: string;
  spinnerProps?: React.ComponentProps<typeof LoadingSpinner>;
  className?: string;
  minHeight?: string | number;
}

export const LoadingContainer = React.forwardRef<HTMLDivElement, LoadingContainerProps>(
  (
    {
      isLoading,
      children,
      loadingMessage,
      spinnerProps,
      className,
      minHeight,
      ...props
    },
    ref
  ) => {
    const containerStyle = minHeight
      ? {
          minHeight: typeof minHeight === "number" ? `${minHeight}px` : minHeight,
        }
      : undefined;

    return (
      <div
        ref={ref}
        className={cn("relative", className)}
        style={containerStyle}
        {...props}
      >
        {isLoading ? (
          <div
            className="flex flex-col items-center justify-center p-8 space-y-4"
            role="status"
            aria-live="polite"
            aria-label={loadingMessage || "Loading content"}
          >
            <LoadingSpinner {...spinnerProps} />
            {loadingMessage && (
              <p className="text-sm text-muted-foreground text-center">
                {loadingMessage}
              </p>
            )}
          </div>
        ) : (
          children
        )}
      </div>
    );
  }
);

LoadingContainer.displayName = "LoadingContainer";

/**
 * Page loading component - convenience wrapper for full page loading
 */
export interface PageLoadingProps {
  message?: string;
  progress?: number;
  className?: string;
}

export const PageLoading = React.forwardRef<HTMLDivElement, PageLoadingProps>(
  ({ message = "Loading page...", progress, className, ...props }, ref) => {
    return (
      <LoadingOverlay
        ref={ref}
        isVisible={true}
        variant="page"
        message={message}
        progress={progress}
        className={className}
        backdrop={false}
        {...props}
      />
    );
  }
);

PageLoading.displayName = "PageLoading";
