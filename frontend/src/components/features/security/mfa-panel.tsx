/**
 * @fileoverview MFA management panel showing factors, status, and actions.
 */

"use client";

import type { MfaFactor } from "@schemas/mfa";
import { AlertCircleIcon, CheckCircle2Icon, ShieldIcon } from "lucide-react";
import Image from "next/image";
import { useId, useState, useTransition } from "react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
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
import {
  refreshMfaFactors,
  regenerateMfaBackups,
  resendMfaChallenge,
  revokeOtherSessions as revokeOtherSessionsAction,
  startMfaEnrollment,
  verifyMfaBackup,
  verifyMfaTotp,
} from "@/lib/security/mfa-client";
import { secureId } from "@/lib/security/random";
import { cn } from "@/lib/utils";

/** The UI message. */
type UIMessage = {
  id: string;
  text: string;
  type: "info" | "error" | "success";
};

/** The MFA panel props. */
type MfaPanelProps = {
  userEmail: string;
  initialAal: "aal1" | "aal2";
  factors: MfaFactor[];
  loadError?: string | null;
};

/**
 * The MFA panel component.
 *
 * @param userEmail - The user email.
 * @param initialAal - The initial AAL.
 * @param factors - The factors.
 * @param loadError - The load error.
 * @returns The MFA panel component.
 */
export function MfaPanel({ userEmail, initialAal, factors, loadError }: MfaPanelProps) {
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [qrCode, setQrCode] = useState<string | null>(null);
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [factorId, setFactorId] = useState<string | null>(null);
  const [verificationCode, setVerificationCode] = useState("");
  const [backupCode, setBackupCode] = useState("");
  const [backupCodes, setBackupCodes] = useState<Array<{ id: string; code: string }>>(
    []
  );
  const [status, setStatus] = useState<"aal1" | "aal2">(initialAal);
  const [factorList, setFactorList] = useState<MfaFactor[]>(factors);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isPending, startTransition] = useTransition();
  const [isRevoking, startRevoke] = useTransition();
  const totpInputId = useId();
  const backupInputId = useId();

  /** Pushes a message to the messages state. */
  const pushMessage = (msg: Omit<UIMessage, "id">) => {
    const message: UIMessage = { ...msg, id: secureId() };
    setMessages((prev) => [...prev.slice(-3), message]);
  };

  /** Refreshes the factors. */
  const refreshFactors = async () => {
    const { aal: nextAal, factors: nextFactors } = await refreshMfaFactors();
    setFactorList(nextFactors);
    setStatus(nextAal);
  };

  /** Handles refreshing factors with feedback. */
  const handleRefreshFactors = () => {
    setIsRefreshing(true);
    startTransition(async () => {
      try {
        await refreshFactors();
      } catch (error) {
        pushMessage({
          text: error instanceof Error ? error.message : "Failed to refresh factors",
          type: "error",
        });
      } finally {
        setIsRefreshing(false);
      }
    });
  };

  /** Begins the enrollment. */
  const beginEnrollment = () => {
    startTransition(async () => {
      setQrCode(null);
      setChallengeId(null);
      setFactorId(null);
      try {
        const data = await startMfaEnrollment();
        setQrCode(data.qrCode ?? null);
        setChallengeId(data.challengeId ?? null);
        setFactorId(data.factorId ?? null);
        pushMessage({
          text: "Scan the QR code and enter the 6-digit code.",
          type: "info",
        });
      } catch (error) {
        setQrCode(null);
        setChallengeId(null);
        setFactorId(null);
        pushMessage({
          text: error instanceof Error ? error.message : "Failed to start enrollment",
          type: "error",
        });
      }
    });
  };

  /** Resends the challenge. */
  const resendChallenge = () => {
    if (!factorId) {
      pushMessage({ text: "Start enrollment first.", type: "error" });
      return;
    }
    startTransition(async () => {
      try {
        const data = await resendMfaChallenge({ factorId });
        setChallengeId(data.challengeId);
        pushMessage({
          text: "New challenge issued. Enter the new 6-digit code.",
          type: "info",
        });
      } catch (error) {
        pushMessage({
          text: error instanceof Error ? error.message : "Failed to resend challenge",
          type: "error",
        });
      }
    });
  };

  /** Verifies the code. */
  const verifyCode = () => {
    if (!factorId || !challengeId || verificationCode.length !== 6) {
      pushMessage({ text: "Enter the 6-digit code first.", type: "error" });
      return;
    }
    startTransition(async () => {
      try {
        const data = await verifyMfaTotp({
          challengeId,
          code: verificationCode,
          factorId,
        });
        setStatus(data.aal);
        setFactorList(data.factors);
        setBackupCodes(
          (data.backupCodes ?? []).map((code) => ({ code, id: secureId() }))
        );
        setQrCode(null);
        setChallengeId(null);
        setFactorId(null);
        setVerificationCode("");
        pushMessage({ text: "MFA verified and enabled.", type: "success" });
        await refreshFactors().catch((error) =>
          pushMessage({
            text: error instanceof Error ? error.message : "Could not refresh factors",
            type: "error",
          })
        );
      } catch (error) {
        pushMessage({
          text: error instanceof Error ? error.message : "Verification failed",
          type: "error",
        });
      }
    });
  };

  /** Verifies the backup code. */
  const verifyBackup = () => {
    if (!backupCode) {
      pushMessage({ text: "Enter a backup code.", type: "error" });
      return;
    }
    startTransition(async () => {
      try {
        const data = await verifyMfaBackup(backupCode);
        pushMessage({
          text: `Backup code accepted. Remaining codes: ${data.remaining}`,
          type: "success",
        });
        setBackupCode("");
      } catch (error) {
        pushMessage({
          text: error instanceof Error ? error.message : "Backup code invalid",
          type: "error",
        });
      }
    });
  };

  /** Regenerates the backups. */
  const regenerateBackups = () => {
    const confirmed =
      typeof window !== "undefined" &&
      window.confirm(
        "Regenerating backup codes will invalidate your existing backup codes. Do you want to continue?"
      );
    if (!confirmed) {
      return;
    }
    startTransition(async () => {
      try {
        const data = await regenerateMfaBackups(10);
        setBackupCodes(
          (data.backupCodes ?? []).map((code) => ({ code, id: secureId() }))
        );
        pushMessage({ text: "Backup codes regenerated.", type: "success" });
      } catch (error) {
        pushMessage({
          text: error instanceof Error ? error.message : "Could not regenerate codes",
          type: "error",
        });
      }
    });
  };

  /** Revokes the other sessions. */
  const revokeOtherSessions = () => {
    startRevoke(async () => {
      try {
        await revokeOtherSessionsAction();
        pushMessage({ text: "Other sessions revoked.", type: "success" });
      } catch (error) {
        pushMessage({
          text: error instanceof Error ? error.message : "Failed to revoke sessions",
          type: "error",
        });
      }
    });
  };

  return (
    <div className="space-y-6">
      {loadError ? (
        <Alert variant="destructive" role="alert">
          <div className="flex items-center gap-2">
            <AlertCircleIcon className="h-4 w-4" />
            <AlertDescription>{loadError}</AlertDescription>
          </div>
        </Alert>
      ) : null}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldIcon className="h-5 w-5" />
            Multi-factor Authentication
          </CardTitle>
          <CardDescription>
            Protect your account with an authenticator app and backup codes.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center gap-3">
            <Badge variant={status === "aal2" ? "default" : "secondary"}>
              {status === "aal2" ? "Enabled" : "Not enabled"}
            </Badge>
            <span className="text-sm text-muted-foreground">
              Signed in as <strong>{userEmail}</strong>
            </span>
          </div>

          <div className="space-y-3">
            <Button onClick={beginEnrollment} disabled={isPending}>
              {isPending ? "Working..." : "Start TOTP enrollment"}
            </Button>
            {factorId && (
              <Button variant="outline" onClick={resendChallenge} disabled={isPending}>
                Resend / Refresh Challenge
              </Button>
            )}
            {qrCode && (
              <div className="rounded-lg border p-4 flex flex-col items-center gap-3">
                <Image
                  src={qrCode}
                  alt="TOTP QR code"
                  width={192}
                  height={192}
                  className="h-48 w-48 rounded bg-white p-2"
                />
                <p className="text-sm text-muted-foreground text-center">
                  Scan the QR code with your authenticator app, then enter the 6-digit
                  code below.
                </p>
              </div>
            )}
          </div>

          <Separator />

          <div className="space-y-3">
            <Label htmlFor={totpInputId}>6-digit code</Label>
            <div className="flex gap-2">
              <Input
                id={totpInputId}
                inputMode="numeric"
                maxLength={6}
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ""))}
                className="max-w-xs text-center tracking-widest font-mono"
                disabled={isPending}
              />
              <Button
                onClick={verifyCode}
                disabled={isPending || verificationCode.length !== 6}
              >
                Verify & Enable
              </Button>
            </div>
          </div>

          {backupCodes.length > 0 && (
            <div className="space-y-2">
              <Label>Backup codes (store securely)</Label>
              <div className="grid grid-cols-2 gap-2">
                {backupCodes.map((item) => (
                  <code
                    key={item.id}
                    className="text-sm rounded bg-muted px-3 py-2 text-center font-mono"
                  >
                    {item.code}
                  </code>
                ))}
              </div>
            </div>
          )}

          <Separator />

          <div className="space-y-3">
            <Label htmlFor={backupInputId}>Backup code</Label>
            <div className="flex gap-2">
              <Input
                id={backupInputId}
                placeholder="ABCDE-12345"
                value={backupCode}
                onChange={(e) => setBackupCode(e.target.value.toUpperCase())}
                className="max-w-xs text-center font-mono"
                disabled={isPending}
              />
              <Button variant="secondary" onClick={verifyBackup} disabled={isPending}>
                Verify Backup Code
              </Button>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={regenerateBackups}
                disabled={isPending}
              >
                Regenerate codes
              </Button>
              <Button
                variant="ghost"
                onClick={() => revokeOtherSessions()}
                disabled={isPending || isRevoking}
              >
                {isRevoking ? "Revoking…" : "Sign out other sessions"}
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Existing factors</Label>
              <Button
                size="sm"
                variant="outline"
                disabled={isPending || isRefreshing}
                onClick={handleRefreshFactors}
              >
                {isRefreshing ? "Refreshing..." : "Refresh"}
              </Button>
            </div>
            {factorList.length > 0 ? (
              <div className="grid grid-cols-1 gap-2">
                {factorList.map((factor) => (
                  <div
                    key={factor.id}
                    className={cn(
                      "border rounded-lg p-3 flex items-center justify-between",
                      factor.status === "verified"
                        ? "border-green-500/40"
                        : "border-muted-foreground/20"
                    )}
                  >
                    <div className="space-y-1">
                      <div className="font-medium text-sm">
                        {factor.friendlyName ?? factor.type.toUpperCase()}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {factor.type.toUpperCase()} • {factor.status}
                      </div>
                    </div>
                    {factor.status === "verified" ? (
                      <CheckCircle2Icon className="h-5 w-5 text-green-500" />
                    ) : (
                      <AlertCircleIcon className="h-5 w-5 text-amber-500" />
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No factors enrolled yet.</p>
            )}
          </div>

          {messages.length > 0 && (
            <output className="space-y-2" aria-live="polite" aria-atomic="true">
              {messages.map((msg) => (
                <Alert
                  key={msg.id}
                  variant={msg.type === "error" ? "destructive" : "default"}
                >
                  <AlertDescription className="flex items-center gap-2">
                    {msg.type === "success" ? (
                      <CheckCircle2Icon className="h-4 w-4" />
                    ) : null}
                    {msg.text}
                  </AlertDescription>
                </Alert>
              ))}
            </output>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
