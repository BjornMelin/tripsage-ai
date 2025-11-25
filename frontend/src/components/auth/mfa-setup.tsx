"use client";

import {
  AlertCircle,
  CheckCircle2,
  Copy,
  Loader2,
  Shield,
  Smartphone,
} from "lucide-react";
import Image from "next/image";
import { useId, useState } from "react";
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
import { Separator } from "@/components/ui/separator";

interface MfaSetupProps {
  onComplete: (backupCodes: string[]) => void;
  onCancel: () => void;
}

interface MfaSetupData {
  secret: string;
  qrCodeUrl: string;
  backupCodes: string[];
  manualEntryKey: string;
}

export function MfaSetup({ onComplete, onCancel }: MfaSetupProps) {
  const [step, setStep] = useState<"setup" | "verify" | "complete">("setup");
  const [setupData, setSetupData] = useState<MfaSetupData | null>(null);
  const [verificationCode, setVerificationCode] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedSecret, setCopiedSecret] = useState(false);
  const verificationInputId = useId();

  const handleInitiateSetup = async () => {
    setIsLoading(true);
    setError(null);

    try {
      /**
       * TODO: Replace mock API call with real MFA setup implementation.
       *
       * Requirements:
       * - Call Supabase Auth MFA setup endpoint or use Supabase client methods
       * - Generate TOTP secret using Supabase Auth or compatible library
       * - Generate QR code URL for authenticator app scanning
       * - Generate backup codes (typically 8-10 codes)
       * - Store backup codes securely (encrypted in database or returned to user)
       * - Handle API errors (network failures, rate limiting, invalid requests)
       * - Add proper error messages for different failure scenarios
       * - Consider using `@supabase/supabase-js` auth.mfa methods
       */
      if (process.env.NODE_ENV !== "development") {
        throw new Error("MFA setup is not implemented in production.");
      }
      // Demo-only mock API call
      await new Promise((resolve) => setTimeout(resolve, 1000));

      /**
       * TODO: Replace with real MFA setup data from Supabase Auth
       *
       * Requirements:
       * - Generate TOTP secret using Supabase Auth or compatible library
       * - Generate QR code URL for authenticator app scanning
       * - Generate backup codes (typically 8-10 codes)
       * - Store backup codes securely (encrypted in database or returned to user)
       */
      const mockSetupData: MfaSetupData = {
        backupCodes: [
          "12345-67890",
          "23456-78901",
          "34567-89012",
          "45678-90123",
          "56789-01234",
          "67890-12345",
          "78901-23456",
          "89012-34567",
          "90123-45678",
          "01234-56789",
        ],
        manualEntryKey: "JBSWY3DPEHPK3PXP",
        qrCodeUrl:
          "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
        secret: "JBSWY3DPEHPK3PXP",
      };

      setSetupData(mockSetupData);
      setStep("verify");
    } catch (_err) {
      setError("Failed to initialize MFA setup. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyCode = async () => {
    if (!verificationCode || verificationCode.length !== 6) {
      setError("Please enter a 6-digit verification code");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      /**
       * TODO: Replace mock API call with real MFA verification implementation.
       *
       * Requirements:
       * - Verify TOTP code using Supabase Auth MFA verification endpoint
       * - Use `supabase.auth.mfa.verify()` or equivalent API call
       * - Validate code format and length before sending to API
       * - Handle verification failures (invalid code, expired code, rate limiting)
       * - On successful verification, enable MFA for the user account
       * - Store MFA status in user profile/metadata
       * - Show appropriate error messages for different failure types
       * - Add telemetry tracking for MFA setup completion
       */
      // Mock API call - replace with actual implementation
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // TODO: Replace with real MFA verification: await supabase.auth.mfa.verify({ code: verificationCode })
      // Mock verification (accept any 6-digit code for demo)
      if (verificationCode.length === 6) {
        setStep("complete");
        onComplete(setupData?.backupCodes || []);
      } else {
        setError("Invalid verification code. Please try again.");
      }
    } catch (_err) {
      setError("Failed to verify code. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 2000);
    } catch (err) {
      console.error("Failed to copy to clipboard:", err);
    }
  };

  if (step === "setup") {
    return (
      <Card className="w-full max-w-lg">
        <CardHeader className="text-center">
          <div className="flex items-center justify-center mb-2">
            <Shield className="h-8 w-8 text-primary" />
          </div>
          <CardTitle>Enable Two-Factor Authentication</CardTitle>
          <CardDescription>
            Add an extra layer of security to your account with two-factor
            authentication
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-4">
            <div className="flex items-start space-x-3">
              <div className="shrink-0 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-semibold">
                1
              </div>
              <div>
                <h3 className="font-medium">Install an authenticator app</h3>
                <p className="text-sm text-muted-foreground">
                  Download an app like Google Authenticator, Authy, or 1Password
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-3">
              <div className="shrink-0 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-semibold">
                2
              </div>
              <div>
                <h3 className="font-medium">Scan QR code or enter secret</h3>
                <p className="text-sm text-muted-foreground">
                  We'll generate a QR code and secret key for your authenticator app
                </p>
              </div>
            </div>

            <div className="flex items-start space-x-3">
              <div className="shrink-0 w-6 h-6 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-semibold">
                3
              </div>
              <div>
                <h3 className="font-medium">Verify setup</h3>
                <p className="text-sm text-muted-foreground">
                  Enter the 6-digit code from your authenticator app to complete setup
                </p>
              </div>
            </div>
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <div className="flex space-x-3">
            <Button variant="outline" onClick={onCancel} className="flex-1">
              Cancel
            </Button>
            <Button
              onClick={handleInitiateSetup}
              disabled={isLoading}
              className="flex-1"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Setting up...
                </>
              ) : (
                <>
                  <Smartphone className="mr-2 h-4 w-4" />
                  Start Setup
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (step === "verify" && setupData) {
    return (
      <Card className="w-full max-w-lg">
        <CardHeader className="text-center">
          <CardTitle>Scan QR Code</CardTitle>
          <CardDescription>
            Scan this QR code with your authenticator app or enter the secret manually
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* QR Code */}
          <div className="flex justify-center">
            <div className="p-4 bg-white rounded-lg border">
              <Image
                src={setupData.qrCodeUrl}
                alt="QR Code for MFA setup"
                width={192}
                height={192}
                className="w-48 h-48"
              />
            </div>
          </div>

          {/* Manual Entry */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">
              Can't scan? Enter this code manually:
            </Label>
            <div className="flex items-center space-x-2">
              <Input
                value={setupData.manualEntryKey}
                readOnly
                className="font-mono text-sm"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(setupData.manualEntryKey)}
              >
                {copiedSecret ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>

          <Separator />

          {/* Verification */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor={verificationInputId}>
                Enter the 6-digit code from your authenticator app:
              </Label>
              <Input
                id={verificationInputId}
                type="text"
                placeholder="123456"
                value={verificationCode}
                onChange={(e) => {
                  const value = e.target.value.replace(/\D/g, "").slice(0, 6);
                  setVerificationCode(value);
                  setError(null);
                }}
                maxLength={6}
                className="text-center text-lg tracking-widest font-mono"
                disabled={isLoading}
              />
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="flex space-x-3">
              <Button variant="outline" onClick={onCancel} className="flex-1">
                Cancel
              </Button>
              <Button
                onClick={handleVerifyCode}
                disabled={isLoading || verificationCode.length !== 6}
                className="flex-1"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  "Verify & Enable"
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (step === "complete") {
    return (
      <Card className="w-full max-w-lg">
        <CardHeader className="text-center">
          <div className="flex items-center justify-center mb-2">
            <CheckCircle2 className="h-8 w-8 text-green-600" />
          </div>
          <CardTitle>Two-Factor Authentication Enabled!</CardTitle>
          <CardDescription>
            Your account is now protected with two-factor authentication
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <Alert>
            <Shield className="h-4 w-4" />
            <AlertDescription>
              Your account security has been enhanced. You'll now need to enter a code
              from your authenticator app when signing in.
            </AlertDescription>
          </Alert>

          <div className="space-y-4">
            <div>
              <h3 className="font-medium mb-2">Important:</h3>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Keep your backup codes in a safe place</li>
                <li>• Don't share your backup codes with anyone</li>
                <li>• You can use backup codes if you lose your phone</li>
                <li>• You can regenerate backup codes in your security settings</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return null;
}
