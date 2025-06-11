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
import { AlertCircle, ArrowLeft, Loader2, Shield, Smartphone } from "lucide-react";
import React, { useState, useEffect } from "react";

interface MFAVerificationProps {
  userEmail: string;
  onVerified: () => void;
  onCancel: () => void;
  onUseBackupCode: () => void;
}

export function MFAVerification({ 
  userEmail, 
  onVerified, 
  onCancel,
  onUseBackupCode 
}: MFAVerificationProps) {
  const [verificationCode, setVerificationCode] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeRemaining, setTimeRemaining] = useState(30);

  // Auto-submit when 6 digits are entered
  useEffect(() => {
    if (verificationCode.length === 6) {
      handleVerifyCode();
    }
  }, [verificationCode]);

  // Countdown timer for resend
  useEffect(() => {
    if (timeRemaining > 0) {
      const timer = setTimeout(() => setTimeRemaining(timeRemaining - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [timeRemaining]);

  const handleVerifyCode = async () => {
    if (!verificationCode || verificationCode.length !== 6) {
      setError("Please enter a 6-digit verification code");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Mock API call - replace with actual implementation
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Mock verification (accept any 6-digit code for demo)
      if (verificationCode.length === 6) {
        onVerified();
      } else {
        setError("Invalid verification code. Please try again.");
        setVerificationCode("");
      }
    } catch (err) {
      setError("Failed to verify code. Please try again.");
      setVerificationCode("");
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, "").slice(0, 6);
    setVerificationCode(value);
    setError(null);
  };

  const handleResendCode = async () => {
    setTimeRemaining(30);
    setError(null);
    
    try {
      // Mock API call for resending
      await new Promise(resolve => setTimeout(resolve, 500));
      // In real implementation, this would trigger a new SMS or push notification
      console.log("Resend request sent");
    } catch (err) {
      setError("Failed to resend code. Please try again.");
    }
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center space-y-2">
        <div className="flex items-center justify-center mb-2">
          <Shield className="h-8 w-8 text-primary" />
        </div>
        <CardTitle className="text-2xl">Two-Factor Authentication</CardTitle>
        <CardDescription>
          Enter the 6-digit code from your authenticator app
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
            <Label htmlFor="mfa-code" className="sr-only">
              Verification Code
            </Label>
            <Input
              id="mfa-code"
              type="text"
              placeholder="123456"
              value={verificationCode}
              onChange={handleInputChange}
              maxLength={6}
              className="text-center text-2xl tracking-[0.5em] font-mono h-14"
              disabled={isLoading}
              autoComplete="one-time-code"
              autoFocus
            />
            <p className="text-xs text-muted-foreground text-center">
              Open your authenticator app and enter the 6-digit code
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
            disabled={isLoading || verificationCode.length !== 6}
            className="w-full h-12"
          >
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Verifying...
              </>
            ) : (
              <>
                <Smartphone className="mr-2 h-4 w-4" />
                Verify Code
              </>
            )}
          </Button>
        </div>

        <div className="space-y-4">
          <div className="text-center">
            <p className="text-sm text-muted-foreground">
              Didn't receive a code?{" "}
              {timeRemaining > 0 ? (
                <span>Resend in {timeRemaining}s</span>
              ) : (
                <button
                  type="button"
                  onClick={handleResendCode}
                  className="text-primary hover:underline"
                >
                  Resend code
                </button>
              )}
            </p>
          </div>

          <div className="text-center">
            <button
              type="button"
              onClick={onUseBackupCode}
              className="text-sm text-primary hover:underline"
            >
              Use backup code instead
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

        {/* Tips */}
        <div className="bg-muted/50 rounded-lg p-4">
          <h4 className="text-sm font-medium mb-2">Having trouble?</h4>
          <ul className="text-xs text-muted-foreground space-y-1">
            <li>• Make sure your phone's time is correct</li>
            <li>• Try refreshing your authenticator app</li>
            <li>• Use a backup code if you can't access your authenticator</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
}