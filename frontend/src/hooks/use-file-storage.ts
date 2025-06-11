/**
 * Supabase Storage hooks for file upload and management
 * Provides type-safe file operations with progress tracking
 */

import { useState, useCallback } from "react";
import { useUser } from "@supabase/auth-helpers-react";
import { useSupabase } from "@/lib/supabase/client";
import { useSupabaseQuery, useSupabaseInsert, useSupabaseUpdate } from "./use-supabase-query";
import { useFileAttachmentRealtime } from "./use-supabase-realtime";
import type { FileAttachment, InsertTables } from "@/lib/supabase/database.types";

export interface FileUploadProgress {
  progress: number;
  isUploading: boolean;
  error: string | null;
}

export interface FileUploadOptions {
  tripId?: number;
  chatMessageId?: number;
  bucketName?: string;
  maxFileSize?: number; // in bytes
  allowedMimeTypes?: string[];
}

/**
 * Hook for uploading files to Supabase Storage
 */
export function useFileUpload(options: FileUploadOptions = {}) {
  const user = useUser();
  const supabase = useSupabase();
  const [uploadProgress, setUploadProgress] = useState<FileUploadProgress>({
    progress: 0,
    isUploading: false,
    error: null,
  });

  const createAttachmentMutation = useSupabaseInsert("file_attachments");

  const uploadFile = useCallback(async (file: File): Promise<FileAttachment> => {
    if (!user?.id) {
      throw new Error("User not authenticated");
    }

    const {
      tripId,
      chatMessageId,
      bucketName = "attachments",
      maxFileSize = 10 * 1024 * 1024, // 10MB default
      allowedMimeTypes,
    } = options;

    // Validate file size
    if (file.size > maxFileSize) {
      throw new Error(`File size exceeds ${maxFileSize / 1024 / 1024}MB limit`);
    }

    // Validate file type
    if (allowedMimeTypes && !allowedMimeTypes.includes(file.type)) {
      throw new Error(`File type ${file.type} is not allowed`);
    }

    setUploadProgress({
      progress: 0,
      isUploading: true,
      error: null,
    });

    try {
      // Generate unique filename
      const fileExt = file.name.split(".").pop()?.toLowerCase() || "";
      const fileName = `${user.id}/${Date.now()}_${Math.random().toString(36).substring(7)}.${fileExt}`;
      const filePath = `${bucketName}/${fileName}`;

      // Upload file to storage
      const { data: uploadData, error: uploadError } = await supabase.storage
        .from(bucketName)
        .upload(fileName, file, {
          cacheControl: "3600",
          upsert: false,
        });

      if (uploadError) {
        throw new Error(uploadError.message);
      }

      setUploadProgress(prev => ({ ...prev, progress: 90 }));

      // Create file attachment record
      const attachmentData: InsertTables<"file_attachments"> = {
        user_id: user.id,
        trip_id: tripId || null,
        chat_message_id: chatMessageId || null,
        filename: uploadData.path,
        original_filename: file.name,
        file_size: file.size,
        mime_type: file.type,
        file_path: uploadData.path,
        bucket_name: bucketName,
        upload_status: "completed",
        metadata: {
          uploaded_at: new Date().toISOString(),
          client_info: {
            user_agent: navigator.userAgent,
            timestamp: Date.now(),
          },
        },
      };

      const attachment = await createAttachmentMutation.mutateAsync(attachmentData);

      setUploadProgress({
        progress: 100,
        isUploading: false,
        error: null,
      });

      return attachment;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Upload failed";
      setUploadProgress({
        progress: 0,
        isUploading: false,
        error: errorMessage,
      });
      throw error;
    }
  }, [user?.id, supabase, options, createAttachmentMutation]);

  return {
    uploadFile,
    uploadProgress,
    isUploading: uploadProgress.isUploading,
  };
}

/**
 * Hook for downloading files from Supabase Storage
 */
export function useFileDownload() {
  const supabase = useSupabase();
  const [isDownloading, setIsDownloading] = useState(false);

  const downloadFile = useCallback(async (bucketName: string, filePath: string, fileName?: string) => {
    setIsDownloading(true);
    
    try {
      const { data, error } = await supabase.storage
        .from(bucketName)
        .download(filePath);

      if (error) {
        throw new Error(error.message);
      }

      // Create download link
      const url = URL.createObjectURL(data);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName || filePath.split("/").pop() || "download";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Failed to download file:", error);
      throw error;
    } finally {
      setIsDownloading(false);
    }
  }, [supabase]);

  const getPublicUrl = useCallback((bucketName: string, filePath: string) => {
    const { data } = supabase.storage
      .from(bucketName)
      .getPublicUrl(filePath);
    
    return data.publicUrl;
  }, [supabase]);

  return {
    downloadFile,
    getPublicUrl,
    isDownloading,
  };
}

/**
 * Hook for managing user's file attachments with real-time updates
 */
export function useFileAttachments(tripId?: number, chatMessageId?: number) {
  const user = useUser();

  let query = (q: any) => q.eq("user_id", user?.id);
  
  if (tripId) {
    query = (q: any) => q.eq("user_id", user?.id).eq("trip_id", tripId);
  }
  
  if (chatMessageId) {
    query = (q: any) => q.eq("user_id", user?.id).eq("chat_message_id", chatMessageId);
  }

  const attachmentsQuery = useSupabaseQuery(
    "file_attachments",
    query,
    {
      enabled: !!user?.id,
      staleTime: 30 * 1000, // 30 seconds
    }
  );

  // Enable real-time updates
  useFileAttachmentRealtime(user?.id || null);

  return {
    attachments: attachmentsQuery.data || [],
    isLoading: attachmentsQuery.isLoading,
    error: attachmentsQuery.error,
    refetch: attachmentsQuery.refetch,
  };
}

/**
 * Hook for deleting files and their attachments
 */
export function useDeleteFile() {
  const supabase = useSupabase();
  const [isDeleting, setIsDeleting] = useState(false);

  const deleteFile = useCallback(async (attachment: FileAttachment) => {
    setIsDeleting(true);
    
    try {
      // Delete from storage
      const { error: storageError } = await supabase.storage
        .from(attachment.bucket_name)
        .remove([attachment.file_path]);

      if (storageError) {
        console.warn("Failed to delete from storage:", storageError.message);
      }

      // Delete attachment record
      const { error: dbError } = await supabase
        .from("file_attachments")
        .delete()
        .eq("id", attachment.id);

      if (dbError) {
        throw new Error(dbError.message);
      }

      console.log("✅ File deleted:", attachment.original_filename);
    } catch (error) {
      console.error("❌ Failed to delete file:", error);
      throw error;
    } finally {
      setIsDeleting(false);
    }
  }, [supabase]);

  return {
    deleteFile,
    isDeleting,
  };
}

/**
 * Hook for bulk file operations
 */
export function useBulkFileOperations() {
  const supabase = useSupabase();
  const [isProcessing, setIsProcessing] = useState(false);

  const deleteMultipleFiles = useCallback(async (attachments: FileAttachment[]) => {
    setIsProcessing(true);
    
    try {
      // Group by bucket for efficient deletion
      const bucketGroups = attachments.reduce((acc, attachment) => {
        if (!acc[attachment.bucket_name]) {
          acc[attachment.bucket_name] = [];
        }
        acc[attachment.bucket_name].push(attachment);
        return acc;
      }, {} as Record<string, FileAttachment[]>);

      // Delete from storage
      for (const [bucketName, files] of Object.entries(bucketGroups)) {
        const filePaths = files.map(f => f.file_path);
        const { error } = await supabase.storage
          .from(bucketName)
          .remove(filePaths);
        
        if (error) {
          console.warn(`Failed to delete some files from ${bucketName}:`, error.message);
        }
      }

      // Delete attachment records
      const attachmentIds = attachments.map(a => a.id);
      const { error } = await supabase
        .from("file_attachments")
        .delete()
        .in("id", attachmentIds);

      if (error) {
        throw new Error(error.message);
      }

      console.log(`✅ Deleted ${attachments.length} files`);
    } catch (error) {
      console.error("❌ Failed to delete files:", error);
      throw error;
    } finally {
      setIsProcessing(false);
    }
  }, [supabase]);

  return {
    deleteMultipleFiles,
    isProcessing,
  };
}