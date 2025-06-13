"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { Eye, EyeOff } from "lucide-react";
import { useEffect, useRef, useState } from "react";

interface ApiKeyInputProps {
  value: string;
  onChange: (value: string) => void;
  onBlur?: () => void;
  placeholder?: string;
  autoFocus?: boolean;
  className?: string;
  disabled?: boolean;
  error?: string;
}

export function ApiKeyInput({
  value,
  onChange,
  onBlur,
  placeholder = "Enter API key",
  autoFocus = false,
  className,
  disabled = false,
  error,
}: ApiKeyInputProps) {
  const [visible, setVisible] = useState(false);
  const inactivityTimerRef = useRef<NodeJS.Timeout | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-clear after 2 minutes of inactivity for security
  useEffect(() => {
    if (value && !disabled) {
      if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current);

      const timer = setTimeout(
        () => {
          onChange("");
          if (inputRef.current) inputRef.current.blur();
        },
        1000 * 60 * 2
      ); // 2 minutes

      inactivityTimerRef.current = timer;
    }

    return () => {
      if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current);
    };
  }, [value, onChange, disabled]);

  // Clear value when component unmounts
  useEffect(() => {
    return () => {
      onChange("");
    };
  }, [onChange]);

  return (
    <div className="relative">
      <Input
        ref={inputRef}
        type={visible ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={onBlur}
        placeholder={placeholder}
        autoFocus={autoFocus}
        className={cn(
          "pr-10", // Make room for the toggle button
          error ? "border-destructive" : "",
          className
        )}
        disabled={disabled}
        // Disable browser features that might store the value
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="off"
        spellCheck="false"
      />
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="absolute right-0 top-0 h-full px-3 py-2 text-muted-foreground"
        onClick={() => setVisible(!visible)}
        disabled={disabled}
        tabIndex={-1}
      >
        {visible ? (
          <EyeOff className="h-4 w-4" aria-hidden="true" />
        ) : (
          <Eye className="h-4 w-4" aria-hidden="true" />
        )}
        <span className="sr-only">{visible ? "Hide API key" : "Show API key"}</span>
      </Button>
      {error && <p className="mt-1 text-sm text-destructive">{error}</p>}
    </div>
  );
}
