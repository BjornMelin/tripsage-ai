"use client";

import { useState } from "react";
import { useApiKeyStore } from "@/stores/api-key-store";
import { useDeleteApiKey, useValidateApiKey } from "@/hooks/use-api-keys";
import type { ApiKey } from "@/types/api-keys";
import { formatDistanceToNow } from "date-fns";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Loader2, CheckCircle, XCircle, RefreshCw, Trash2 } from "lucide-react";

export function ApiKeyList() {
  const { keys } = useApiKeyStore();
  const [keyToDelete, setKeyToDelete] = useState<string | null>(null);
  const { mutate: deleteKey, isPending: isDeleting } = useDeleteApiKey();
  const { mutate: validateKey, isPending: isValidating } = useValidateApiKey();

  // Convert record to array for easier rendering
  const keysList = Object.entries(keys).map(([service, keyData]) => ({
    service,
    ...keyData,
  }));

  // Format timestamp to readable format
  const formatTimestamp = (timestamp: string | undefined) => {
    if (!timestamp) return "Never";
    try {
      return formatDistanceToNow(new Date(timestamp), { addSuffix: true });
    } catch (e) {
      return "Invalid date";
    }
  };

  // Handle delete confirmation
  const handleDelete = () => {
    if (keyToDelete) {
      deleteKey({ service: keyToDelete });
      setKeyToDelete(null);
    }
  };

  // Handle validation
  const handleValidate = (service: string, apiKey: ApiKey) => {
    validateKey({
      service,
      api_key: "", // We don't need to pass the actual key, the backend will use the stored one
      save: true,
    });
  };

  if (keysList.length === 0) {
    return (
      <div className="text-center p-8 border rounded-lg bg-muted/20">
        <h3 className="text-lg font-medium">No API Keys Added</h3>
        <p className="text-muted-foreground mt-2">
          You haven't added any API keys yet. Add a key to use external
          services.
        </p>
      </div>
    );
  }

  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Service</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Last Used</TableHead>
            <TableHead>Last Validated</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {keysList.map((key) => (
            <TableRow key={key.service}>
              <TableCell className="font-medium">{key.service}</TableCell>
              <TableCell>
                {key.is_valid ? (
                  <Badge
                    variant="outline"
                    className="bg-green-50 text-green-700 border-green-200"
                  >
                    <CheckCircle className="h-3 w-3 mr-1" />
                    Valid
                  </Badge>
                ) : (
                  <Badge
                    variant="outline"
                    className="bg-red-50 text-red-700 border-red-200"
                  >
                    <XCircle className="h-3 w-3 mr-1" />
                    Invalid
                  </Badge>
                )}
              </TableCell>
              <TableCell>{formatTimestamp(key.last_used)}</TableCell>
              <TableCell>{formatTimestamp(key.last_validated)}</TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleValidate(key.service, key)}
                    disabled={isValidating}
                  >
                    {isValidating ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <RefreshCw className="h-4 w-4 mr-1" />
                    )}
                    Validate
                  </Button>
                  <AlertDialog
                    open={keyToDelete === key.service}
                    onOpenChange={(open) => !open && setKeyToDelete(null)}
                  >
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        className="text-red-600 border-red-200 hover:bg-red-50"
                        onClick={() => setKeyToDelete(key.service)}
                        disabled={isDeleting}
                      >
                        {isDeleting && keyToDelete === key.service ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4 mr-1" />
                        )}
                        Remove
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                        <AlertDialogDescription>
                          This will permanently delete your {key.service} API
                          key. You will need to add it again if you want to use
                          this service.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={handleDelete}
                          className="bg-red-600 hover:bg-red-700"
                        >
                          Delete
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
