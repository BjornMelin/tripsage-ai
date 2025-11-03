/**
 * @fileoverview BYOK API keys management UI. Provides provider selection and secured
 * key storage operations via authenticated API. IDs are generated with `useId` to
 * avoid duplicate DOM identifiers when multiple instances are rendered.
 */

"use client";

import { useEffect, useId, useMemo, useState } from "react";
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
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";

type AllowedService = "openai" | "openrouter" | "anthropic" | "xai";

type ApiKeySummary = {
  service: AllowedService;
  created_at: string;
  last_used?: string | null;
  has_key: boolean;
  is_valid: boolean;
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

  const hasMap = useMemo(() => new Map(items.map((k) => [k.service, true])), [items]);

  const load = async () => {
    setLoading(true);
    try {
      const data = await authenticatedApi.get<ApiKeySummary[]>("/api/keys");
      setItems(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSave = async () => {
    if (!apiKey.trim()) return;
    setLoading(true);
    try {
      await authenticatedApi.post("/api/keys", { api_key: apiKey.trim(), service });
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
                    {present
                      ? `Added: ${new Date(row!.created_at).toLocaleString()}`
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
    </div>
  );
}
