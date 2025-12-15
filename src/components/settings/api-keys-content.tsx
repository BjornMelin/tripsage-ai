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
  useRef,
  useState,
} from "react";
import { z } from "zod";
import { updateGatewayFallbackPreference } from "@/app/dashboard/settings/api-keys/actions";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/use-toast";
import { useAuthenticatedApi } from "@/hooks/use-authenticated-api";
import { useZodForm } from "@/hooks/use-zod-form";
import { ApiError } from "@/lib/api/error-types";
import { getErrorMessage } from "@/lib/errors/get-error-message";
import { validateApiKeyInput } from "@/lib/security/api-key-validation";
import { recordClientErrorOnActiveSpan } from "@/lib/telemetry/client-errors";

const SUPPORTED = ["openai", "openrouter", "anthropic", "xai"] as const;

type AllowedService = (typeof SUPPORTED)[number];

const API_KEY_FORM_SCHEMA = z.strictObject({
  apiKey: z.string().min(1),
  service: z.enum(SUPPORTED),
});

type ApiKeyFormValues = z.infer<typeof API_KEY_FORM_SCHEMA>;

const PROVIDER_DISPLAY_NAMES: Record<AllowedService, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  openrouter: "OpenRouter",
  xai: "xAI",
};

const SUPPORTED_SET: ReadonlySet<AllowedService> = new Set(SUPPORTED);

function IsAllowedService(value: string): value is AllowedService {
  return SUPPORTED_SET.has(value as AllowedService);
}

function ToTitleCaseIdentifier(value: string): string {
  return value
    .trim()
    .split(/[-_\s]+/g)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function GetProviderDisplayName(providerId: string): string {
  const normalized = providerId.trim().toLowerCase();
  if (IsAllowedService(normalized)) return PROVIDER_DISPLAY_NAMES[normalized];
  return ToTitleCaseIdentifier(providerId) || providerId;
}

type ApiKeySummary = {
  service: AllowedService;
  createdAt: string;
  lastUsed?: string | null;
  hasKey: boolean;
  isValid: boolean;
};

/**
 * Render the API Keys management UI.
 *
 * @returns The BYOK management UI component.
 */
export function ApiKeysContent() {
  const { authenticatedApi, cancelRequests } = useAuthenticatedApi();
  const { toast } = useToast();
  const abortControllerRef = useRef<AbortController | null>(null);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [items, setItems] = useState<ApiKeySummary[]>([]);
  const [allowGatewayFallback, setAllowGatewayFallback] = useState<boolean | null>(
    null
  );
  const isBusy = loading || initialLoading;

  const form = useZodForm<ApiKeyFormValues>({
    defaultValues: { apiKey: "", service: "openai" },
    schema: API_KEY_FORM_SCHEMA,
    validateMode: "onChange",
  });
  const service = form.watch("service");

  const itemsByService = useMemo(() => {
    return new Map<AllowedService, ApiKeySummary>(
      items.map((item) => [item.service, item])
    );
  }, [items]);

  const load = useCallback(async () => {
    const signal = abortControllerRef.current?.signal;
    if (!signal || signal.aborted) return;
    setLoading(true);
    try {
      const keysPromise = authenticatedApi.get<ApiKeySummary[]>("/api/keys");
      const settingsPromise = authenticatedApi.get<{
        allowGatewayFallback: boolean | null;
      }>("/api/user-settings");

      const [data, settings] = await Promise.all([keysPromise, settingsPromise]);
      if (!signal.aborted) {
        setItems(data);
        setAllowGatewayFallback(settings.allowGatewayFallback);
      }
    } catch (error) {
      if (!signal || signal.aborted) return;
      if (error instanceof ApiError && error.code === "REQUEST_CANCELLED") return;
      recordClientErrorOnActiveSpan(
        error instanceof Error ? error : new Error(String(error)),
        { action: "load", context: "ApiKeysContent" }
      );
      toast({
        description:
          error instanceof ApiError
            ? error.userMessage
            : getErrorMessage(error, "Failed to load API keys."),
        title: "Failed to load",
        variant: "destructive",
      });
    } finally {
      if (!signal.aborted) {
        setLoading(false);
        setInitialLoading(false);
      }
    }
  }, [authenticatedApi, toast]);

  useEffect(() => {
    abortControllerRef.current = new AbortController();
    load();
    return () => {
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
      cancelRequests();
    };
  }, [load, cancelRequests]);

  const onSave = form.handleSubmitSafe(async ({ apiKey, service }) => {
    const apiKeyResult = validateApiKeyInput(apiKey, { service });
    if (!apiKeyResult.ok) {
      toast({
        description: apiKeyResult.error,
        title: "Invalid API key",
        variant: "destructive",
      });
      return;
    }

    const signal = abortControllerRef.current?.signal;
    if (!signal || signal.aborted) return;
    setLoading(true);
    try {
      await authenticatedApi.post("/api/keys", {
        apiKey: apiKeyResult.apiKey,
        service,
      });
      form.reset({ apiKey: "", service });
      await load();
    } catch (error) {
      if (!signal || signal.aborted) return;
      if (error instanceof ApiError && error.code === "REQUEST_CANCELLED") return;
      recordClientErrorOnActiveSpan(
        error instanceof Error ? error : new Error(String(error)),
        { action: "onSave", context: "ApiKeysContent", service }
      );
      toast({
        description:
          error instanceof ApiError
            ? error.userMessage
            : getErrorMessage(error, "Failed to save API key."),
        title: "Save failed",
        variant: "destructive",
      });
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  });

  const onDelete = async (svc: AllowedService) => {
    const signal = abortControllerRef.current?.signal;
    if (!signal || signal.aborted) return;
    setLoading(true);
    try {
      await authenticatedApi.delete(`/api/keys/${encodeURIComponent(svc)}`);
      await load();
    } catch (error) {
      if (!signal || signal.aborted) return;
      if (error instanceof ApiError && error.code === "REQUEST_CANCELLED") return;
      recordClientErrorOnActiveSpan(
        error instanceof Error ? error : new Error(String(error)),
        { action: "onDelete", context: "ApiKeysContent", service: svc }
      );
      toast({
        description:
          error instanceof ApiError
            ? error.userMessage
            : getErrorMessage(error, "Failed to delete API key."),
        title: "Delete failed",
        variant: "destructive",
      });
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  };

  const [_actionState, actionDispatch, isPending] = useActionState<
    { success: boolean },
    { next: boolean; previous: boolean | null }
  >(
    async (_prevState, action) => {
      const { next, previous } = action;
      try {
        await updateGatewayFallbackPreference(next);
        return { success: true };
      } catch (error) {
        setAllowGatewayFallback(previous);
        recordClientErrorOnActiveSpan(
          error instanceof Error ? error : new Error(String(error)),
          { action: "updateGatewayFallbackPreference", context: "ApiKeysContent" }
        );
        toast({
          description: "Failed to update gateway fallback. Please try again.",
          title: "Update failed",
          variant: "destructive",
        });
        return { success: false };
      }
    },
    { success: true }
  );

  const onToggleFallback = (next: boolean) => {
    const previous = allowGatewayFallback;
    setAllowGatewayFallback(next);
    actionDispatch({ next, previous });
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
            {initialLoading ? (
              <>
                <div className="space-y-2">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-10 w-full rounded-md" />
                </div>
                <div className="sm:col-span-2 space-y-2">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-10 w-full rounded-md" />
                </div>
              </>
            ) : (
              <>
                <div className="space-y-2">
                  <Label htmlFor={serviceId}>Provider</Label>
                  <Select
                    value={service}
                    onValueChange={(v) => {
                      if (IsAllowedService(v)) {
                        form.setValue("service", v, {
                          shouldDirty: true,
                          shouldValidate: true,
                        });
                      }
                    }}
                  >
                    <SelectTrigger id={serviceId}>
                      <SelectValue placeholder="Select provider" />
                    </SelectTrigger>
                    <SelectContent>
                      {SUPPORTED.map((s) => (
                        <SelectItem key={s} value={s}>
                          {GetProviderDisplayName(s)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="sm:col-span-2 space-y-2">
                  <Label htmlFor={apiKeyId}>API Key</Label>
                  <Input
                    autoComplete="off"
                    id={apiKeyId}
                    type="password"
                    placeholder="Paste your API key"
                    {...form.register("apiKey")}
                  />
                </div>
              </>
            )}
          </div>
          <div className="flex justify-end">
            {initialLoading ? (
              <Skeleton className="h-10 w-28 rounded-md" />
            ) : (
              <Button onClick={onSave} disabled={isBusy || !form.formState.isValid}>
                {loading ? "Saving..." : "Save Key"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Stored Keys</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {initialLoading
            ? SUPPORTED.map((s) => (
                <div key={s} className="flex items-center justify-between py-2">
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-3 w-44" />
                  </div>
                  <Skeleton className="h-8 w-20 rounded-md" />
                </div>
              ))
            : SUPPORTED.map((s) => {
                const row = itemsByService.get(s);
                const present = row !== undefined;
                return (
                  <div key={s} className="flex items-center justify-between py-2">
                    <div className="space-y-1">
                      <div className="font-medium">{GetProviderDisplayName(s)}</div>
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
                          disabled={isBusy}
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
            Keys are encrypted at rest with Supabase Vault. Avoid logging secrets and
            restrict access to decrypted values.
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Gateway Fallback Consent</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {initialLoading ? (
            <>
              <div className="flex items-center justify-between py-2">
                <div className="space-y-2">
                  <Skeleton className="h-4 w-52" />
                  <Skeleton className="h-3 w-80" />
                </div>
                <Skeleton className="h-6 w-10 rounded-full" />
              </div>
              <Skeleton className="h-3 w-64" />
            </>
          ) : (
            <>
              <div className="flex items-center justify-between py-2">
                <div className="space-y-1">
                  <div className="font-medium">Allow fallback to team Gateway</div>
                  <div className="text-sm text-muted-foreground">
                    When no BYOK key is present, permit using the team Vercel AI
                    Gateway.
                  </div>
                </div>
                <Switch
                  checked={allowGatewayFallback === true}
                  disabled={isBusy || allowGatewayFallback === null || isPending}
                  onCheckedChange={onToggleFallback}
                />
              </div>
              <div className="text-xs text-muted-foreground">
                You can change this at any time. Some features may require an active
                provider key if disabled.
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
