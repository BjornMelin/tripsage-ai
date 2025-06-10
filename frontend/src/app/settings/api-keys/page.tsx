"use client";

import { ApiKeySettings } from "@/components/api-key-management/api-key-settings";

// Force dynamic rendering to avoid SSG issues with authentication
export const dynamic = "force-dynamic";

export default function ApiKeysPage() {
  return (
    <div className="container py-8">
      <h1 className="text-3xl font-bold mb-8">API Key Settings</h1>
      <ApiKeySettings />
    </div>
  );
}
