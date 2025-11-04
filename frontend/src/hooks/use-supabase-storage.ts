/**
 * @fileoverview React hooks for Supabase Storage file management.
 *
 * Provides hooks for file uploads, downloads, storage stats,
 * and file attachment management with progress tracking.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { nowIso, secureUUID } from "@/lib/security/random";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useSupabase } from "@/lib/supabase/client";
import type {
  FileAttachment,
  FileAttachmentInsert,
  FileAttachmentUpdate,
  UploadStatus,
  VirusScanStatus,
} from "@/lib/supabase/database.types";
import { insertSingle, updateSingle } from "@/lib/supabase/typed-helpers";

interface UploadProgress {
  fileId: string;
  fileName: string;
  progress: number;
  status: "uploading" | "completed" | "error";
  error?: string;
}

interface UploadOptions {
  bucket?: string;
  tripId?: number;
  chatMessageId?: number;
  onProgress?: (progress: number) => void;
  maxFileSize?: number; // in bytes
  allowedTypes?: string[];
}

/**
 * Internal hook to get the current user ID from Supabase auth.
 *
 * @returns User ID or null if not authenticated
 */
function useUserId(): string | null {
  const supabase = useSupabase();
  const [userId, setUserId] = useState<string | null>(null);
  useEffect(() => {
    const isMounted = true;
    supabase.auth.getUser().then(({ data }) => {
      if (isMounted) setUserId(data.user?.id ?? null);
    });
    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      if (isMounted) setUserId(session?.user?.id ?? null);
    });
    return () => data.subscription.unsubscribe();
  }, [supabase]);
  return userId;
}

/**
 * Hook for managing file uploads and attachments with Supabase Storage.
 */
export function useSupabaseStorage() {
  const supabase = useSupabase();
  const queryClient = useQueryClient();
  const userId = useUserId();
  const [uploadProgress, setUploadProgress] = useState<Record<string, UploadProgress>>(
    {}
  );

  // Fetch user's file attachments
  const useFileAttachments = (filters?: {
    tripId?: number;
    chatMessageId?: number;
    uploadStatus?: UploadStatus;
    virusScanStatus?: VirusScanStatus;
  }) => {
    return useQuery({
      enabled: !!userId,
      queryFn: async () => {
        if (!userId) throw new Error("User not authenticated");

        let query = supabase
          .from("file_attachments")
          .select("*")
          .eq("user_id", userId)
          .order("created_at", { ascending: false });

        if (filters?.tripId) {
          query = query.eq("trip_id", filters.tripId);
        }
        if (filters?.chatMessageId) {
          query = query.eq("chat_message_id", filters.chatMessageId);
        }
        if (filters?.uploadStatus) {
          query = query.eq("upload_status", filters.uploadStatus);
        }
        if (filters?.virusScanStatus) {
          query = query.eq("virus_scan_status", filters.virusScanStatus);
        }

        const { data, error } = await query;
        if (error) throw error;
        return data as FileAttachment[];
      },
      queryKey: ["file-attachments", userId, filters],
      staleTime: 1000 * 60 * 5, // 5 minutes
    });
  };

  // Get file attachment by ID
  const useFileAttachment = (attachmentId: string | null) => {
    return useQuery({
      enabled: !!attachmentId,
      queryFn: async () => {
        if (!attachmentId) throw new Error("Attachment ID is required");

        const { data, error } = await supabase
          .from("file_attachments")
          .select("*")
          .eq("id", attachmentId)
          .single();

        if (error) throw error;
        return data as FileAttachment;
      },
      queryKey: ["file-attachment", attachmentId],
      staleTime: 1000 * 60 * 10, // 10 minutes
    });
  };

  // Get storage usage statistics
  const useStorageStats = () => {
    return useQuery({
      enabled: !!userId,
      queryFn: async () => {
        if (!userId) throw new Error("User not authenticated");

        type FileStatRow = Pick<
          FileAttachment,
          "file_size" | "mime_type" | "upload_status"
        >;
        const { data: files, error } = await supabase
          .from("file_attachments")
          .select("file_size, mime_type, upload_status")
          .eq("user_id", userId);

        if (error) throw error;

        const typedFiles = (files ?? []) as FileStatRow[];
        const totalSize = typedFiles.reduce((sum, file) => sum + file.file_size, 0);
        const filesByType = typedFiles.reduce(
          (acc, file) => {
            const type = file.mime_type.split("/")[0] || "other";
            acc[type] = (acc[type] || 0) + 1;
            return acc;
          },
          {} as Record<string, number>
        );

        const filesByStatus = typedFiles.reduce(
          (acc, file) => {
            acc[file.upload_status] = (acc[file.upload_status] || 0) + 1;
            return acc;
          },
          {} as Record<string, number>
        );

        return {
          filesByStatus,
          filesByType,
          totalFiles: files.length,
          totalSize,
          totalSizeMb: Math.round((totalSize / (1024 * 1024)) * 100) / 100,
        };
      },
      queryKey: ["storage-stats", userId],
      staleTime: 1000 * 60 * 15, // 15 minutes
    });
  };

  // Upload file mutation
  const uploadFile = useMutation({
    mutationFn: async ({
      file,
      options = {},
    }: {
      file: File;
      options?: UploadOptions;
    }) => {
      if (!userId) throw new Error("User not authenticated");

      const {
        bucket = "attachments",
        tripId,
        chatMessageId,
        onProgress,
        maxFileSize = 10 * 1024 * 1024, // 10MB default
        allowedTypes = [],
      } = options;

      // Validate file size
      if (file.size > maxFileSize) {
        throw new Error(
          `File size exceeds maximum allowed size of ${maxFileSize / (1024 * 1024)}MB`
        );
      }

      // Validate file type
      if (allowedTypes.length > 0 && !allowedTypes.includes(file.type)) {
        throw new Error(`File type ${file.type} is not allowed`);
      }

      const fileId = secureUUID();
      const fileExt = file.name.split(".").pop();
      const fileName = `${fileId}.${fileExt}`;
      const filePath = `${userId}/${fileName}`;

      // Track upload progress
      setUploadProgress((prev) => ({
        ...prev,
        [fileId]: {
          fileId,
          fileName: file.name,
          progress: 0,
          status: "uploading",
        },
      }));

      try {
        // Upload file to Supabase Storage
        const { data: uploadData, error: uploadError } = await supabase.storage
          .from(bucket)
          .upload(filePath, file, {
            cacheControl: "3600",
            upsert: false,
          });

        if (uploadError) throw uploadError;

        // Create file attachment record
        const attachmentData: FileAttachmentInsert = {
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          bucket_name: bucket,
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          chat_message_id: chatMessageId || null,
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          file_path: filePath,
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          file_size: file.size,
          filename: fileName,
          metadata: {
            // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
            file_extension: fileExt,
            // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
            upload_timestamp: nowIso(),
          },
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          mime_type: file.type,
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          original_filename: file.name,
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          trip_id: tripId || null,
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          upload_status: "completed",
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          user_id: userId,
          // biome-ignore lint/style/useNamingConvention: Database field names use snake_case
          virus_scan_status: "pending",
        };

        const { data: attachmentRecord, error: attachmentError } = await insertSingle(
          supabase,
          "file_attachments",
          attachmentData
        );

        if (attachmentError) throw attachmentError;

        // Update progress to completed
        setUploadProgress((prev) => ({
          ...prev,
          [fileId]: {
            ...prev[fileId],
            progress: 100,
            status: "completed",
          },
        }));

        // Call progress callback
        onProgress?.(100);

        return {
          attachment: attachmentRecord as FileAttachment,
          storagePath: uploadData.path,
        };
      } catch (error) {
        // Update progress to error
        setUploadProgress((prev) => ({
          ...prev,
          [fileId]: {
            ...prev[fileId],
            error: error instanceof Error ? error.message : "Upload failed",
            status: "error",
          },
        }));

        throw error;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["file-attachments"] });
      queryClient.invalidateQueries({ queryKey: ["storage-stats"] });
    },
  });

  // Upload multiple files
  const uploadMultipleFiles = useMutation({
    mutationFn: async ({
      files,
      options = {},
    }: {
      files: File[];
      options?: UploadOptions;
    }) => {
      const results = await Promise.allSettled(
        files.map((file) => uploadFile.mutateAsync({ file, options }))
      );

      const successful = results
        .filter(
          (
            result
          ): result is PromiseFulfilledResult<{
            attachment: FileAttachment;
            storagePath: string;
          }> => result.status === "fulfilled"
        )
        .map((result) => result.value);

      const failed = results
        .filter(
          (result): result is PromiseRejectedResult => result.status === "rejected"
        )
        .map((result) => result.reason);

      return {
        failed,
        failureCount: failed.length,
        successCount: successful.length,
        successful,
        totalCount: files.length,
      };
    },
  });

  // Delete file mutation
  const deleteFile = useMutation({
    mutationFn: async (attachmentId: string) => {
      // Get file info first
      const { data: attachment, error: fetchError } = await supabase
        .from("file_attachments")
        .select("*")
        .eq("id", attachmentId)
        .single();

      if (fetchError) throw fetchError;

      // Delete from storage
      const attachmentTyped = attachment as FileAttachment;
      const { error: storageError } = await supabase.storage
        .from(attachmentTyped.bucket_name)
        .remove([attachmentTyped.file_path]);

      if (storageError) throw storageError;

      // Delete attachment record
      const { error: dbError } = await supabase
        .from("file_attachments")
        .delete()
        .eq("id", attachmentId);

      if (dbError) throw dbError;

      return attachmentId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["file-attachments"] });
      queryClient.invalidateQueries({ queryKey: ["storage-stats"] });
    },
  });

  // Update file attachment metadata
  const updateFileAttachment = useMutation({
    mutationFn: async ({
      id,
      updates,
    }: {
      id: string;
      updates: FileAttachmentUpdate;
    }) => {
      const { data, error } = await updateSingle(
        supabase,
        "file_attachments",
        updates,
        (qb) => (qb as any).eq("id", id)
      );

      if (error) throw error;
      return data as FileAttachment;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["file-attachments"] });
      queryClient.invalidateQueries({ queryKey: ["file-attachment", data.id] });
    },
  });

  // Get download URL for a file
  const getDownloadUrl = useCallback(
    async (attachment: FileAttachment) => {
      const { data, error } = await supabase.storage
        .from(attachment.bucket_name)
        .createSignedUrl(attachment.file_path, 3600); // 1 hour expiry

      if (error) throw error;
      return data.signedUrl;
    },
    [supabase]
  );

  // Get public URL for a file (if public bucket)
  const getPublicUrl = useCallback(
    (attachment: FileAttachment) => {
      const { data } = supabase.storage
        .from(attachment.bucket_name)
        .getPublicUrl(attachment.file_path);

      return data.publicUrl;
    },
    [supabase]
  );

  // Clear upload progress for a specific file
  const clearUploadProgress = useCallback((fileId: string) => {
    setUploadProgress((prev) => {
      const { [fileId]: _removed, ...rest } = prev;
      return rest;
    });
  }, []);

  // Clear all upload progress
  const clearAllUploadProgress = useCallback(() => {
    setUploadProgress({});
  }, []);

  return useMemo(
    () => ({
      clearAllUploadProgress,
      clearUploadProgress,
      deleteFile,

      // Utilities
      getDownloadUrl,
      getPublicUrl,
      updateFileAttachment,

      // Mutations
      uploadFile,
      uploadMultipleFiles,

      // Upload progress
      uploadProgress,
      useFileAttachment,
      // Query hooks
      useFileAttachments,
      useStorageStats,
    }),
    [
      // Hook factories are stable functions that don't depend on changing state
      // biome-ignore lint/correctness/useExhaustiveDependencies: Hook factories are stable
      useFileAttachments,
      // biome-ignore lint/correctness/useExhaustiveDependencies: Hook factories are stable
      useFileAttachment,
      // biome-ignore lint/correctness/useExhaustiveDependencies: Hook factories are stable
      useStorageStats,
      uploadFile,
      uploadMultipleFiles,
      deleteFile,
      updateFileAttachment,
      getDownloadUrl,
      getPublicUrl,
      uploadProgress,
      clearUploadProgress,
      clearAllUploadProgress,
    ]
  );
}

/**
 * Hook for file type utilities and validation.
 */
export function useFileTypeUtils() {
  const getFileIcon = useCallback((mimeType: string) => {
    const type = mimeType.split("/")[0];
    switch (type) {
      case "image":
        return "🖼️";
      case "video":
        return "🎥";
      case "audio":
        return "🎵";
      case "application":
        if (mimeType.includes("pdf")) return "📄";
        if (mimeType.includes("zip") || mimeType.includes("rar")) return "🗜️";
        if (mimeType.includes("word")) return "📝";
        if (mimeType.includes("excel") || mimeType.includes("spreadsheet")) return "📊";
        if (mimeType.includes("powerpoint") || mimeType.includes("presentation"))
          return "📈";
        return "📎";
      case "text":
        return "📄";
      default:
        return "📎";
    }
  }, []);

  const formatFileSize = useCallback((bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${Number.parseFloat((bytes / k ** i).toFixed(2))} ${sizes[i]}`;
  }, []);

  const isImageFile = useCallback((mimeType: string) => {
    return mimeType.startsWith("image/");
  }, []);

  const isVideoFile = useCallback((mimeType: string) => {
    return mimeType.startsWith("video/");
  }, []);

  const isAudioFile = useCallback((mimeType: string) => {
    return mimeType.startsWith("audio/");
  }, []);

  const isDocumentFile = useCallback((mimeType: string) => {
    return (
      mimeType.includes("pdf") ||
      mimeType.includes("word") ||
      mimeType.includes("text") ||
      mimeType.includes("spreadsheet") ||
      mimeType.includes("presentation")
    );
  }, []);

  return {
    formatFileSize,
    getFileIcon,
    isAudioFile,
    isDocumentFile,
    isImageFile,
    isVideoFile,
  };
}
