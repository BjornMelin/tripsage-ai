import { createClient as createBrowserClient } from "@/lib/supabase/client";
import type { ChatCompletionRequest, ChatCompletionResponse } from "@/types/chat";

// The base URL for API requests
// const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || ""; // Future use

// Helper function to get auth headers
const getAuthHeaders = async () => {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  // Get auth token from Supabase
  if (typeof window !== "undefined") {
    try {
      const supabase = createBrowserClient();
      const {
        data: { session },
        error,
      } = await supabase.auth.getSession();

      if (!error && session?.access_token) {
        headers.Authorization = `Bearer ${session.access_token}`;
      }
    } catch (error) {
      console.warn("Failed to get Supabase session:", error);
    }
  }

  return headers;
};

// Extend fetch with timeout functionality
const fetchWithTimeout = async (url: string, options: RequestInit, timeout = 30000) => {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });

    clearTimeout(id);
    return response;
  } catch (error) {
    clearTimeout(id);
    throw error;
  }
};

/**
 * Send a chat completion request to the API
 * This is used for non-streaming requests
 */
export async function sendChatRequest(
  request: ChatCompletionRequest
): Promise<ChatCompletionResponse> {
  try {
    const headers = await getAuthHeaders();
    const response = await fetchWithTimeout(
      "/api/chat",
      {
        method: "POST",
        headers,
        body: JSON.stringify(request),
      },
      60000
    ); // 60 second timeout

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API request failed: ${response.status} ${errorText}`);
    }

    const data = await response.json();
    return data as ChatCompletionResponse;
  } catch (error) {
    console.error("Error sending chat message:", error);
    throw error;
  }
}

/**
 * Upload attachments to the API
 */
export async function uploadAttachments(files: File[]): Promise<{ urls: string[] }> {
  try {
    // Create FormData to send files
    const formData = new FormData();
    files.forEach((file, i) => {
      formData.append(`file-${i}`, file);
    });

    const authHeaders = await getAuthHeaders();
    // Remove Content-Type for FormData (browser will set multipart/form-data automatically)
    const { "Content-Type": _, ...headersWithoutContentType } = authHeaders;

    const response = await fetch("/api/chat/attachments", {
      method: "POST",
      headers: headersWithoutContentType,
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`File upload failed: ${response.status} ${errorText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error uploading files:", error);
    throw error;
  }
}
