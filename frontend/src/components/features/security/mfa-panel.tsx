/**
 * @fileoverview MFA management panel showing factors, status, and actions.
 */

"use client";

import { type MfaFactor, mfaFactorSchema } from "@schemas/mfa";
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
import { cn } from "@/lib/utils";

/** The UI message. */
type UIMessage =
  | { type: "info"; text: string }
  | { type: "error"; text: string }
  | { type: "success"; text: string };

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
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [status, setStatus] = useState<"aal1" | "aal2">(initialAal);
  const [factorList, setFactorList] = useState<MfaFactor[]>(factors);
  const [isPending, startTransition] = useTransition();
  const [isRevoking, startRevoke] = useTransition();
  const totpInputId = useId();
  const backupInputId = useId();

  /** Pushes a message to the messages state. */
  const pushMessage = (msg: UIMessage) => {
    setMessages((prev) => [...prev.slice(-3), msg]);
  };

  /** Calls the JSON API. */
  const callJson = async <T,>(url: string, body?: unknown): Promise<T> => {
    const res = await fetch(url, {
      body: body ? JSON.stringify(body) : undefined,
      headers: { "Content-Type": "application/json" },
      method: "POST",
    });
    if (!res.ok) {
      const reason = await res.json().catch(() => ({}));
      throw new Error(reason?.error ?? `Request failed (${res.status})`);
    }
    const json = (await res.json()) as { data: T };
    return json.data;
  };

  /** Refreshes the factors. */
  const refreshFactors = async () => {
    const res = await fetch("/api/auth/mfa/factors/list");
    if (!res.ok) {
      const reason = await res.json().catch(() => ({}));
      throw new Error(reason?.error ?? `Request failed (${res.status})`);
    }
    const json = (await res.json()) as {
      data?: { factors?: MfaFactor[]; aal?: string };
    };
    const parsedFactors = mfaFactorSchema.array().parse(json.data?.factors ?? []);
    setFactorList(parsedFactors);
    if (json.data?.aal === "aal2" || json.data?.aal === "aal1") {
      setStatus(json.data.aal);
    }
  };

  /** Begins the enrollment. */
  const beginEnrollment = () => {
    startTransition(async () => {
      try {
        const data = await callJson<{
          challengeId: string;
          factorId: string;
          qrCode: string;
        }>("/api/auth/mfa/setup");
        setQrCode(data.qrCode ?? null);
        setChallengeId(data.challengeId ?? null);
        setFactorId(data.factorId ?? null);
        pushMessage({
          text: "Scan the QR code and enter the 6-digit code.",
          type: "info",
        });
      } catch (error) {
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
        const data = await callJson<{ challengeId: string }>(
          "/api/auth/mfa/challenge",
          {
            factorId,
          }
        );
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
        const data = await callJson<{ status: string; backupCodes: string[] }>(
          "/api/auth/mfa/verify",
          {
            challengeId,
            code: verificationCode,
            factorId,
          }
        );
        setStatus("aal2");
        setBackupCodes(data.backupCodes ?? []);
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
        const data = await callJson<{ remaining: number }>(
          "/api/auth/mfa/backup/verify",
          { code: backupCode }
        );
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
    startTransition(async () => {
      try {
        const data = await callJson<{ backupCodes: string[] }>(
          "/api/auth/mfa/backup/regenerate",
          { count: 10 }
        );
        setBackupCodes(data.backupCodes ?? []);
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
        await callJson<{ status: string }>("/api/auth/mfa/sessions/revoke", {
          scope: "others",
        });
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
                {backupCodes.map((code) => (
                  <code
                    key={code}
                    className="text-sm rounded bg-muted px-3 py-2 text-center font-mono"
                  >
                    {code}
                  </code>
                ))}
              </div>
              <Button
                variant="secondary"
                onClick={regenerateBackups}
                disabled={isPending}
              >
                Regenerate codes
              </Button>
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
              <Button size="sm" variant="outline" onClick={() => refreshFactors()}>
                Refresh
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
            <div className="space-y-2">
              {messages.map((msg, idx) => (
                <Alert
                  key={`${msg.text}-${idx}`}
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
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
