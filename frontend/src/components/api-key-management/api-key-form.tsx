"use client";

import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Loader2 } from "lucide-react";
import { ApiKeyInput } from "./api-key-input";
import { ServiceSelector } from "./service-selector";
import { useApiKeyStore } from "@/stores/api-key-store";
import { useAddApiKey, useValidateApiKey } from "@/hooks/use-api-keys";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { CheckCircle, AlertCircle } from "lucide-react";

// Define form schema with Zod
const formSchema = z.object({
  service: z.string({
    required_error: "Please select a service",
  }),
  apiKey: z.string().min(1, {
    message: "API key is required",
  }),
  save: z.boolean().default(true),
});

export function ApiKeyForm() {
  const [validationResult, setValidationResult] = useState<{
    isValid: boolean;
    message: string;
  } | null>(null);

  const { supportedServices, selectedService, setSelectedService } =
    useApiKeyStore();
  const { mutate: validateKey, isPending: isValidating } = useValidateApiKey();
  const { mutate: addKey, isPending: isAdding } = useAddApiKey();

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      service: selectedService || "",
      apiKey: "",
      save: true,
    },
  });

  // Update form when selected service changes
  const serviceValue = form.watch("service");
  if (selectedService !== serviceValue && serviceValue) {
    setSelectedService(serviceValue);
  }

  // Handle form submission
  const onSubmit = (values: z.infer<typeof formSchema>) => {
    // First validate the key
    validateKey(
      {
        service: values.service,
        api_key: values.apiKey,
        save: false, // Just validate, don't save yet
      },
      {
        onSuccess: (data) => {
          setValidationResult({
            isValid: data.is_valid,
            message: data.message,
          });

          // If validation successful and user wants to save, add the key
          if (data.is_valid && values.save) {
            addKey(
              {
                service: values.service,
                api_key: values.apiKey,
                save: true,
              },
              {
                onSuccess: () => {
                  // Reset form on successful save
                  form.reset({
                    service: "",
                    apiKey: "",
                    save: true,
                  });
                  setValidationResult(null);
                },
              }
            );
          }
        },
        onError: (error) => {
          setValidationResult({
            isValid: false,
            message:
              error instanceof Error
                ? error.message
                : "Failed to validate API key",
          });
        },
      }
    );
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        {validationResult && (
          <Alert variant={validationResult.isValid ? "default" : "destructive"}>
            {validationResult.isValid ? (
              <CheckCircle className="h-4 w-4" />
            ) : (
              <AlertCircle className="h-4 w-4" />
            )}
            <AlertTitle>
              {validationResult.isValid ? "Valid API Key" : "Invalid API Key"}
            </AlertTitle>
            <AlertDescription>{validationResult.message}</AlertDescription>
          </Alert>
        )}

        <FormField
          control={form.control}
          name="service"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Service</FormLabel>
              <FormControl>
                <ServiceSelector
                  services={supportedServices}
                  selectedService={field.value}
                  onServiceChange={field.onChange}
                  disabled={isValidating || isAdding}
                />
              </FormControl>
              <FormDescription>
                Select the service for this API key.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="apiKey"
          render={({ field }) => (
            <FormItem>
              <FormLabel>API Key</FormLabel>
              <FormControl>
                <ApiKeyInput
                  value={field.value}
                  onChange={field.onChange}
                  onBlur={field.onBlur}
                  disabled={isValidating || isAdding}
                  error={form.formState.errors.apiKey?.message}
                />
              </FormControl>
              <FormDescription>
                Enter your API key for the selected service. This will never be
                stored in plain text.
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="save"
          render={({ field }) => (
            <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
              <div className="space-y-0.5">
                <FormLabel className="text-base">Save API Key</FormLabel>
                <FormDescription>
                  Save this API key for future use. Keys are stored securely
                  using envelope encryption.
                </FormDescription>
              </div>
              <FormControl>
                <Switch
                  checked={field.value}
                  onCheckedChange={field.onChange}
                  disabled={isValidating || isAdding}
                />
              </FormControl>
            </FormItem>
          )}
        />

        <Button
          type="submit"
          disabled={isValidating || isAdding}
          className="w-full"
        >
          {(isValidating || isAdding) && (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          )}
          {isValidating
            ? "Validating..."
            : isAdding
              ? "Saving..."
              : "Validate & Save"}
        </Button>
      </form>
    </Form>
  );
}
