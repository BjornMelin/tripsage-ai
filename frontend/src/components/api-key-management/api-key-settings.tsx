"use client";

import { useEffect } from "react";
import { useApiKeys } from "@/lib/hooks/use-api-keys";
import { ApiKeyForm } from "./api-key-form";
import { ApiKeyList } from "./api-key-list";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Loader2 } from "lucide-react";

export function ApiKeySettings() {
  const { isLoading, isError, error, refetch } = useApiKeys();

  // Initial data fetch
  useEffect(() => {
    refetch();
  }, [refetch]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <Card className="border-red-200">
        <CardHeader>
          <CardTitle className="text-red-600">Error Loading API Keys</CardTitle>
          <CardDescription>
            There was a problem loading your API keys. Please try again later.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-red-500">
            {error instanceof Error ? error.message : "Unknown error occurred"}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>API Key Management</CardTitle>
        <CardDescription>
          Manage your API keys for external services. These keys are securely
          stored and used to access various services on your behalf.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="keys" className="w-full">
          <TabsList className="mb-4">
            <TabsTrigger value="keys">Your API Keys</TabsTrigger>
            <TabsTrigger value="add">Add New Key</TabsTrigger>
          </TabsList>

          <TabsContent value="keys" className="mt-4">
            <ApiKeyList />
          </TabsContent>

          <TabsContent value="add" className="mt-4">
            <div className="flex justify-center">
              <ApiKeyForm />
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
