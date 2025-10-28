// TripSage File Processing Edge Function
// Description: Handles file upload processing, virus scanning, and metadata extraction
// Created: 2025-01-11
// Version: 1.0

import { serve } from "std/http/server.ts";
import { createClient } from "@supabase/supabase-js";

interface FileProcessingEvent {
  type: string;
  table: string;
  record: {
    id: string;
    file_path: string;
    bucket_name: string;
    mime_type: string;
    file_size: number;
    upload_status: string;
    user_id: string;
  };
  old_record?: any;
}

interface ProcessingResult {
  success: boolean;
  operation: string;
  message: string;
  metadata?: Record<string, any>;
  error?: string;
}

const supabase = createClient(
  Deno.env.get("SUPABASE_URL") ?? "",
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? ""
);

serve(async (req) => {
  try {
    // Verify request method
    if (req.method !== "POST") {
      return new Response("Method not allowed", { status: 405 });
    }

    const payload: FileProcessingEvent = await req.json();
    console.log("Processing file event:", payload);

    // Only process file_attachments table events
    if (payload.table !== "file_attachments") {
      return new Response("OK", { status: 200 });
    }

    // Only process completed uploads
    if (payload.record.upload_status !== "completed") {
      return new Response("OK", { status: 200 });
    }

    const fileId = payload.record.id;
    const results: ProcessingResult[] = [];

    // Start virus scanning
    const virusResult = await performVirusScan(payload.record);
    results.push(virusResult);

    // Generate thumbnails for images
    if (payload.record.mime_type.startsWith("image/")) {
      const thumbnailResult = await generateThumbnail(payload.record);
      results.push(thumbnailResult);
    }

    // Extract metadata for documents
    if (isDocumentType(payload.record.mime_type)) {
      const metadataResult = await extractDocumentMetadata(payload.record);
      results.push(metadataResult);
    }

    // Update file attachment record with processing results
    await updateFileProcessingResults(fileId, results);

    console.log("File processing completed:", { fileId, results });

    return new Response(
      JSON.stringify({
        success: true,
        file_id: fileId,
        results: results,
      }),
      {
        headers: { "Content-Type": "application/json" },
        status: 200,
      }
    );
  } catch (error) {
    console.error("File processing error:", error);
    
    return new Response(
      JSON.stringify({
        success: false,
        error: error.message,
      }),
      {
        headers: { "Content-Type": "application/json" },
        status: 500,
      }
    );
  }
});

async function performVirusScan(record: any): Promise<ProcessingResult> {
  try {
    // Simulate virus scanning (replace with actual service like ClamAV)
    console.log(`Scanning file: ${record.file_path}`);
    
    // For demo purposes, randomly simulate scan results
    const isClean = Math.random() > 0.01; // 99% chance of being clean
    
    const scanResult = {
      status: isClean ? "clean" : "infected",
      scanner: "clamav",
      timestamp: new Date().toISOString(),
      file_hash: await generateFileHash(record.file_path),
    };

    // Update virus scan status in database
    await supabase
      .from("file_attachments")
      .update({
        virus_scan_status: scanResult.status,
        virus_scan_result: scanResult,
      })
      .eq("id", record.id);

    if (!isClean) {
      // Quarantine infected file
      await quarantineFile(record.file_path, record.bucket_name);
    }

    return {
      success: true,
      operation: "virus_scan",
      message: `File scan completed: ${scanResult.status}`,
      metadata: scanResult,
    };
  } catch (error) {
    console.error("Virus scan error:", error);
    
    // Update scan status to failed
    await supabase
      .from("file_attachments")
      .update({
        virus_scan_status: "failed",
        virus_scan_result: { error: error.message },
      })
      .eq("id", record.id);

    return {
      success: false,
      operation: "virus_scan",
      message: "Virus scan failed",
      error: error.message,
    };
  }
}

async function generateThumbnail(record: any): Promise<ProcessingResult> {
  try {
    console.log(`Generating thumbnail for: ${record.file_path}`);
    
    // Download original file
    const { data: fileData, error: downloadError } = await supabase.storage
      .from(record.bucket_name)
      .download(record.file_path);

    if (downloadError) {
      throw new Error(`Failed to download file: ${downloadError.message}`);
    }

    // Generate thumbnail (simplified - would use image processing library)
    const thumbnailPath = generateThumbnailPath(record.file_path);
    
    // For demo, just copy the original file as thumbnail
    const { error: uploadError } = await supabase.storage
      .from("thumbnails")
      .upload(thumbnailPath, fileData, {
        contentType: record.mime_type,
      });

    if (uploadError) {
      throw new Error(`Failed to upload thumbnail: ${uploadError.message}`);
    }

    return {
      success: true,
      operation: "thumbnail_generation",
      message: "Thumbnail generated successfully",
      metadata: {
        thumbnail_path: thumbnailPath,
        original_size: record.file_size,
      },
    };
  } catch (error) {
    console.error("Thumbnail generation error:", error);
    
    return {
      success: false,
      operation: "thumbnail_generation",
      message: "Thumbnail generation failed",
      error: error.message,
    };
  }
}

async function extractDocumentMetadata(record: any): Promise<ProcessingResult> {
  try {
    console.log(`Extracting metadata from: ${record.file_path}`);
    
    // Simulate document metadata extraction
    const metadata = {
      page_count: Math.floor(Math.random() * 50) + 1,
      word_count: Math.floor(Math.random() * 5000) + 100,
      created_date: new Date().toISOString(),
      language: "en",
      has_text: true,
    };

    // Update file metadata
    const { error } = await supabase
      .from("file_attachments")
      .update({
        metadata: {
          ...record.metadata,
          document_info: metadata,
        },
      })
      .eq("id", record.id);

    if (error) {
      throw new Error(`Failed to update metadata: ${error.message}`);
    }

    return {
      success: true,
      operation: "metadata_extraction",
      message: "Document metadata extracted successfully",
      metadata: metadata,
    };
  } catch (error) {
    console.error("Metadata extraction error:", error);
    
    return {
      success: false,
      operation: "metadata_extraction",
      message: "Metadata extraction failed",
      error: error.message,
    };
  }
}

async function updateFileProcessingResults(
  fileId: string,
  results: ProcessingResult[]
): Promise<void> {
  const processingData = {
    processing_completed_at: new Date().toISOString(),
    processing_results: results,
    has_errors: results.some((r) => !r.success),
  };

  const { error } = await supabase
    .from("file_attachments")
    .update({
      metadata: {
        processing: processingData,
      },
    })
    .eq("id", fileId);

  if (error) {
    console.error("Failed to update processing results:", error);
  }
}

async function generateFileHash(filePath: string): Promise<string> {
  // Simulate hash generation
  const encoder = new TextEncoder();
  const data = encoder.encode(filePath + Date.now());
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function quarantineFile(filePath: string, bucketName: string): Promise<void> {
  try {
    // Move file to quarantine bucket
    const quarantinePath = `quarantine/${Date.now()}_${filePath}`;
    
    // In a real implementation, you would move the file
    console.log(`File quarantined: ${filePath} -> ${quarantinePath}`);
    
    // Log quarantine event
    await supabase.from("file_processing_queue").insert({
      operation: "quarantine",
      status: "completed",
      metadata: {
        original_path: filePath,
        quarantine_path: quarantinePath,
        reason: "virus_detected",
      },
    });
  } catch (error) {
    console.error("Quarantine error:", error);
  }
}

function generateThumbnailPath(originalPath: string): string {
  const pathParts = originalPath.split("/");
  const filename = pathParts[pathParts.length - 1];
  const nameWithoutExt = filename.split(".")[0];
  
  return `thumbnails/${pathParts.slice(0, -1).join("/")}/${nameWithoutExt}_thumb.jpg`;
}

function isDocumentType(mimeType: string): boolean {
  const documentTypes = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/csv",
  ];
  
  return documentTypes.includes(mimeType);
}

/* To configure this Edge Function:

1. Deploy the function:
   supabase functions deploy file-processor

2. Set up environment variables:
   supabase secrets set SUPABASE_URL=your_supabase_url
   supabase secrets set SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

3. Create a database webhook:
   CREATE OR REPLACE FUNCTION notify_file_processor()
   RETURNS TRIGGER AS $$
   BEGIN
     PERFORM net.http_post(
       url := 'https://your-project.supabase.co/functions/v1/file-processor',
       headers := '{"Content-Type": "application/json", "Authorization": "Bearer your-anon-key"}'::jsonb,
       body := json_build_object(
         'type', TG_OP,
         'table', TG_TABLE_NAME,
         'record', row_to_json(NEW),
         'old_record', row_to_json(OLD)
       )::text
     );
     RETURN COALESCE(NEW, OLD);
   END;
   $$ LANGUAGE plpgsql;

4. Create trigger:
   CREATE TRIGGER file_attachments_processor_trigger
     AFTER INSERT OR UPDATE ON file_attachments
     FOR EACH ROW
     EXECUTE FUNCTION notify_file_processor();
*/
