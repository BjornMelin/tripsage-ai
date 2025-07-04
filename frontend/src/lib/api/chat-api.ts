import { createClient as createBrowserClient } from "@/lib/supabase/client";
import type { ChatCompletionRequest, ChatCompletionResponse } from "@/types/chat";

// The base URL for API requests
// const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || ""; // Future use

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
 * Stream a chat completion request to the API
 * NOTE: This implementation is kept for backward compatibility.
 * For new code, use the Vercel AI SDK's useChat hook instead, which handles
 * streaming internally.
 */
export function streamChatRequest(
  request: ChatCompletionRequest,
  {
    onStart,
    onMessage,
    onFinish,
    onError,
    onAbort,
  }: {
    onStart?: () => void;
    onMessage?: (message: string) => void;
    onFinish?: () => void;
    onError?: (error: Error) => void;
    onAbort?: () => void;
  } = {}
): { abort: () => void } {
  const controller = new AbortController();
  const signal = controller.signal;

  const fetchData = async () => {
    try {
      if (onStart) onStart();

      const headers = await getAuthHeaders();
      const response = await fetch("/api/chat", {
        // Updated to use /api/chat instead of /api/chat/stream
        method: "POST",
        headers,
        body: JSON.stringify(request),
        signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API stream request failed: ${response.status} ${errorText}`);
      }

      if (!response.body) {
        throw new Error("ReadableStream not supported");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let done = false;
      let buffer = "";

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;

        if (done) {
          if (onFinish) onFinish();
          break;
        }

        // Decode the stream chunk to text
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // Process any complete JSON objects in the buffer
        let newlineIndex;
        while ((newlineIndex = buffer.indexOf("\n")) !== -1) {
          const line = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 1);

          if (line.trim()) {
            try {
              const data = JSON.parse(line);

              // Handle streamed content from Vercel AI SDK format
              if (data.content) {
                if (onMessage) onMessage(data.content);
              } else if (data.type === "error") {
                throw new Error(data.message || "Stream error");
              }
            } catch (e) {
              console.error("Error parsing stream chunk:", e);
              if (onError) onError(new Error("Error parsing stream data"));
            }
          }
        }
      }
    } catch (error) {
      if (signal.aborted) {
        if (onAbort) onAbort();
      } else {
        console.error("Stream error:", error);
        if (onError) onError(error instanceof Error ? error : new Error(String(error)));
      }
    }
  };

  fetchData();

  return {
    abort: () => controller.abort(),
  };
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
