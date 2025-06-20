"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AlertCircle, ArrowLeft, KeyRound, Loader2 } from "lucide-react";
import type React from "react";
import { useState } from "react";

interface BackupCodeVerificationProps {
  userEmail: string;
  onVerified: (remainingCodes?: number) => void;
  onCancel: () => void;
  onUseAuthenticator: () => void;
}

export function BackupCodeVerification({
  userEmail,
  onVerified,
  onCancel,
  onUseAuthenticator,
}: BackupCodeVerificationProps) {
  const [backupCode, setBackupCode] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleVerifyCode = async () => {
    if (!backupCode || backupCode.length < 10) {
      setError("Please enter a valid backup code");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Mock API call - replace with actual implementation
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // Mock verification (accept any code with correct format for demo)
      if (backupCode.includes("-") && backupCode.length >= 10) {
        // Simulate remaining backup codes
        const remainingCodes = Math.floor(Math.random() * 8) + 1;
        onVerified(remainingCodes);
      } else {
        setError("Invalid backup code. Please check and try again.");
        setBackupCode("");
      }
    } catch (_err) {
      setError("Failed to verify backup code. Please try again.");
      setBackupCode("");
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = e.target.value.toUpperCase().replace(/[^A-Z0-9-]/g, "");

    // Auto-format as XXXXX-XXXXX
    if (value.length <= 5) {
      // First part
      setBackupCode(value);
    } else if (value.length <= 11) {
      // Add hyphen after 5 characters if not present
      if (!value.includes("-")) {
        value = `${value.slice(0, 5)}-${value.slice(5)}`;
      }
      setBackupCode(value);
    }

    setError(null);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && backupCode.length >= 10) {
      handleVerifyCode();
    }
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center space-y-2">
        <div className="flex items-center justify-center mb-2">
          <KeyRound className="h-8 w-8 text-primary" />
        </div>
        <CardTitle className="text-2xl">Use Backup Code</CardTitle>
        <CardDescription>
          Enter one of your saved backup codes to sign in
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="text-center">
          <p className="text-sm text-muted-foreground">
            Signing in as <span className="font-medium">{userEmail}</span>
          </p>
        </div>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="backup-code">Backup Code</Label>
            <Input
              id="backup-code"
              type="text"
              placeholder="12345-67890"
              value={backupCode}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              maxLength={11}
              className="text-center text-lg tracking-widest font-mono"
              disabled={isLoading}
              autoComplete="off"
              autoFocus
            />
            <p className="text-xs text-muted-foreground text-center">
              Format: XXXXX-XXXXX (e.g., 12345-67890)
            </p>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <Button
            onClick={handleVerifyCode}
            disabled={isLoading || backupCode.length < 10}
            className="w-full h-12"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Verifying...
              </>
            ) : (
              <>
                <KeyRound className="mr-2 h-4 w-4" />
                Verify Backup Code
              </>
            )}
          </Button>
        </div>

        <div className="space-y-4">
          <div className="text-center">
            <button
              type="button"
              onClick={onUseAuthenticator}
              className="text-sm text-primary hover:underline"
            >
              Use authenticator app instead
            </button>
          </div>

          <div className="text-center">
            <button
              type="button"
              onClick={onCancel}
              className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="mr-1 h-3 w-3" />
              Back to sign in
            </button>
          </div>
        </div>

        {/* Important notes */}
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="text-sm">
            <strong>Important:</strong> Each backup code can only be used once. After
            using this code, you'll have fewer backup codes remaining.
          </AlertDescription>
        </Alert>

        {/* Tips */}
        <div className="bg-muted/50 rounded-lg p-4">
          <h4 className="text-sm font-medium mb-2">Can't find your backup codes?</h4>
          <ul className="text-xs text-muted-foreground space-y-1">
            <li>• Check your password manager or secure notes</li>
            <li>• Look for codes saved when you first set up 2FA</li>
            <li>• Contact support if you've lost access to all backup codes</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}
