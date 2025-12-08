/**
 * @fileoverview BYOK API keys management UI. Provides provider selection and secured
 * key storage operations via authenticated API. IDs are generated with `useId` to
 * avoid duplicate DOM identifiers when multiple instances are rendered.
 */

"use client";

import {
  useActionState,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useState,
} from "react";
import { updateGatewayFallbackPreference } from "@/app/api/user-settings/actions";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";

type AllowedService = "openai" | "openrouter" | "anthropic" | "xai";

type ApiKeySummary = {
  service: AllowedService;
  createdAt: string;
  lastUsed?: string | null;
  hasKey: boolean;
  isValid: boolean;
};

const SUPPORTED: AllowedService[] = ["openai", "openrouter", "anthropic", "xai"];

/**
 * Render the API Keys management page.
 *
 * @returns The BYOK management UI component.
 */
export default function ApiKeysPage() {
  const { authenticatedApi } = useAuthenticatedApi();
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<ApiKeySummary[]>([]);
  const [service, setService] = useState<AllowedService>("openai");
  const [apiKey, setApiKey] = useState("");
  const [allowGatewayFallback, setAllowGatewayFallback] = useState<boolean | null>(
    null
  );

  const hasMap = useMemo(() => new Map(items.map((k) => [k.service, true])), [items]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await authenticatedApi.get<ApiKeySummary[]>("/api/keys");
      setItems(data);
      // Load consent flag
      const settings = await authenticatedApi.get<{
        allowGatewayFallback: boolean | null;
      }>("/api/user-settings");
      setAllowGatewayFallback(settings.allowGatewayFallback);
    } finally {
      setLoading(false);
    }
  }, [authenticatedApi]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load]);

  const onSave = async () => {
    if (!apiKey.trim()) return;
    setLoading(true);
    try {
      await authenticatedApi.post("/api/keys", { apiKey: apiKey.trim(), service });
      setApiKey("");
      await load();
    } finally {
      setLoading(false);
    }
  };

  const onDelete = async (svc: AllowedService) => {
    setLoading(true);
    try {
      await authenticatedApi.delete(`/api/keys/${svc}`);
      await load();
    } finally {
      setLoading(false);
    }
  };

  const [_actionState, actionDispatch, isPending] = useActionState(
    async (_prevState: unknown, val: boolean) => {
      try {
        await updateGatewayFallbackPreference(val);
        setAllowGatewayFallback(val);
        return { success: true };
      } catch {
        // revert on failure
        setAllowGatewayFallback((prev) => !prev);
        return { success: false };
      }
    },
    { success: true }
  );

  const onToggleFallback = (val: boolean) => {
    setAllowGatewayFallback(val);
    actionDispatch(val);
  };

  // Generate unique ids for form controls to satisfy accessibility and lint rules
  const serviceId = useId();
  const apiKeyId = useId();

  return (
    <div className="container mx-auto max-w-3xl space-y-6 py-8">
      <Card>
        <CardHeader>
          <CardTitle>Bring Your Own Key (BYOK)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor={serviceId}>Provider</Label>
              <Select
                value={service}
                onValueChange={(v) => setService(v as AllowedService)}
              >
                <SelectTrigger id={serviceId}>
                  <SelectValue placeholder="Select provider" />
                </SelectTrigger>
                <SelectContent>
                  {SUPPORTED.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s.toUpperCase()}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="sm:col-span-2 space-y-2">
              <Label htmlFor={apiKeyId}>API Key</Label>
              <Input
                id={apiKeyId}
                type="password"
                placeholder="Paste your API key"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
            </div>
          </div>
          <div className="flex justify-end">
            <Button onClick={onSave} disabled={loading || !apiKey.trim()}>
              {loading ? "Saving..." : "Save Key"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Stored Keys</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {SUPPORTED.map((s) => {
            const present = hasMap.get(s);
            const row = items.find((i) => i.service === s);
            return (
              <div key={s} className="flex items-center justify-between py-2">
                <div className="space-y-1">
                  <div className="font-medium">{s.toUpperCase()}</div>
                  <div className="text-sm text-muted-foreground">
                    {present && row?.createdAt
                      ? `Added: ${new Date(row.createdAt).toLocaleString()}`
                      : "Not set"}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {present ? (
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => onDelete(s)}
                      disabled={loading}
                    >
                      Remove
                    </Button>
                  ) : (
                    <span className="text-sm text-muted-foreground">—</span>
                  )}
                </div>
              </div>
            );
          })}
          <Separator />
          <div className="text-xs text-muted-foreground">
            Keys are encrypted with Supabase Vault. We never store plaintext.
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Gateway Fallback Consent</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-center justify-between py-2">
            <div className="space-y-1">
              <div className="font-medium">Allow fallback to team Gateway</div>
              <div className="text-sm text-muted-foreground">
                When no BYOK key is present, permit using the team Vercel AI Gateway.
              </div>
            </div>
            <Switch
              checked={!!allowGatewayFallback}
              disabled={loading || allowGatewayFallback === null || isPending}
              onCheckedChange={onToggleFallback}
            />
          </div>
          <div className="text-xs text-muted-foreground">
            You can change this at any time. Some features may require an active
            provider key if disabled.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
