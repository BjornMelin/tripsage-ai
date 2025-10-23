"use client";

// caching handled at app level via cacheComponents; no per-file directive
import { ApiKeySettings } from "@/components/api-key-management/api-key-settings";

export default function ApiKeysPage() {
  return (
    <div className="container py-8">
      <h1 className="text-3xl font-bold mb-8">API Key Settings</h1>
      <ApiKeySettings />
    </div>
  );
}
