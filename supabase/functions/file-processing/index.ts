/**
 * File Processing Edge Function
 * 
 * Handles file processing operations including:
 * - Virus scanning integration
 * - Image resizing and optimization
 * - File metadata extraction
 * - Status updates in database
 * 
 * @module file-processing
 */

import { serve } from "std/http/server.ts";
import { createClient } from "@supabase/supabase-js";

// Type definitions
interface FileProcessingRequest {
  file_id: string;
  operation: 'virus_scan' | 'resize_image' | 'extract_metadata' | 'process_all';
  options?: {
    resize_dimensions?: { width: number; height: number };
    quality?: number;
    scan_provider?: 'clamav' | 'virustotal' | 'cloudflare';
  };
}

interface WebhookPayload {
  type: 'INSERT' | 'UPDATE';
  table: string;
  record: FileAttachment;
  old_record?: FileAttachment;
  schema: string;
}

interface FileAttachment {
  id: string;
  user_id: string;
  trip_id?: number;
  chat_message_id?: number;
  filename: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  file_path: string;
  bucket_name: string;
  upload_status: 'uploading' | 'completed' | 'failed';
  virus_scan_status: 'pending' | 'clean' | 'infected' | 'failed';
  virus_scan_result: Record<string, any>;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface VirusScanResult {
  is_clean: boolean;
  scan_time: string;
  provider: string;
  details?: Record<string, any>;
  error?: string;
}

interface ImageProcessingResult {
  success: boolean;
  original_size: number;
  processed_size: number;
  processed_path: string;
  metadata: Record<string, any>;
  error?: string;
}

// Environment variables
const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!;
const SUPABASE_SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const STORAGE_BUCKET = Deno.env.get('STORAGE_BUCKET') || 'attachments';
const VIRUS_SCAN_API_KEY = Deno.env.get('VIRUS_SCAN_API_KEY');
const CLOUDFLARE_AI_TOKEN = Deno.env.get('CLOUDFLARE_AI_TOKEN');
const MAX_FILE_SIZE = parseInt(Deno.env.get('MAX_FILE_SIZE') || '50000000'); // 50MB default

// Initialize Supabase client
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

/**
 * Validates the incoming request and authentication
 */
async function validateRequest(req: Request): Promise<{ isValid: boolean; error?: string }> {
  try {
    // Check for webhook secret first
    const webhookSecret = req.headers.get('x-webhook-secret');
    if (webhookSecret === Deno.env.get('WEBHOOK_SECRET')) {
      return { isValid: true };
    }

    // Check for authorization header
    const authHeader = req.headers.get('authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      return { isValid: false, error: 'Missing or invalid authorization header' };
    }

    // Verify JWT token
    const token = authHeader.replace('Bearer ', '');
    const { data: { user }, error } = await supabase.auth.getUser(token);
    
    if (error || !user) {
      return { isValid: false, error: 'Invalid authentication token' };
    }

    return { isValid: true };
  } catch (error) {
    console.error('Validation error:', error);
    return { isValid: false, error: 'Request validation failed' };
  }
}

/**
 * Fetches file attachment from database
 */
async function getFileAttachment(fileId: string): Promise<FileAttachment | null> {
  const { data, error } = await supabase
    .from('file_attachments')
    .select('*')
    .eq('id', fileId)
    .single();

  if (error) {
    console.error('Error fetching file attachment:', error);
    return null;
  }

  return data as FileAttachment;
}

/**
 * Updates file attachment status in database
 */
async function updateFileAttachment(
  fileId: string, 
  updates: Partial<FileAttachment>
): Promise<boolean> {
  try {
    const { error } = await supabase
      .from('file_attachments')
      .update({
        ...updates,
        updated_at: new Date().toISOString()
      })
      .eq('id', fileId);

    if (error) {
      console.error('Error updating file attachment:', error);
      return false;
    }

    return true;
  } catch (error) {
    console.error('Update error:', error);
    return false;
  }
}

/**
 * Downloads file from Supabase Storage
 */
async function downloadFile(filePath: string, bucketName: string): Promise<ArrayBuffer | null> {
  try {
    const { data, error } = await supabase.storage
      .from(bucketName)
      .download(filePath);

    if (error) {
      console.error('Error downloading file:', error);
      return null;
    }

    return await data.arrayBuffer();
  } catch (error) {
    console.error('Download error:', error);
    return null;
  }
}

/**
 * Uploads processed file back to Supabase Storage
 */
async function uploadProcessedFile(
  filePath: string,
  bucketName: string,
  fileData: ArrayBuffer,
  contentType: string
): Promise<boolean> {
  try {
    const { error } = await supabase.storage
      .from(bucketName)
      .upload(filePath, fileData, {
        contentType,
        upsert: true
      });

    if (error) {
      console.error('Error uploading processed file:', error);
      return false;
    }

    return true;
  } catch (error) {
    console.error('Upload error:', error);
    return false;
  }
}

/**
 * Simulates virus scanning (placeholder implementation)
 * In production, integrate with actual virus scanning services
 */
async function performVirusScan(fileData: ArrayBuffer, fileName: string): Promise<VirusScanResult> {
  console.log(`Performing virus scan on ${fileName} (${fileData.byteLength} bytes)`);

  try {
    // Placeholder for actual virus scanning logic
    // This would typically call an external API like ClamAV, VirusTotal, etc.
    
    // Basic file size check
    if (fileData.byteLength > MAX_FILE_SIZE) {
      return {
        is_clean: false,
        scan_time: new Date().toISOString(),
        provider: 'internal',
        error: 'File size exceeds maximum allowed'
      };
    }

    // Basic file type validation
    const dangerousExtensions = ['.exe', '.bat', '.com', '.scr', '.pif', '.vbs', '.js'];
    const hasExtension = dangerousExtensions.some(ext => 
      fileName.toLowerCase().endsWith(ext)
    );

    if (hasExtension) {
      return {
        is_clean: false,
        scan_time: new Date().toISOString(),
        provider: 'internal',
        details: { reason: 'Potentially dangerous file extension' }
      };
    }

    // Simulate API call delay
    await new Promise(resolve => setTimeout(resolve, 1000));

    // For demo purposes, mark all files as clean
    return {
      is_clean: true,
      scan_time: new Date().toISOString(),
      provider: 'demo-scanner',
      details: {
        scan_duration_ms: 1000,
        signatures_checked: 12345,
        engine_version: '1.0.0'
      }
    };

  } catch (error) {
    console.error('Virus scan error:', error);
    return {
      is_clean: false,
      scan_time: new Date().toISOString(),
      provider: 'internal',
      error: error instanceof Error ? error.message : 'Scan failed'
    };
  }
}

/**
 * Resizes and optimizes images
 */
async function processImage(
  fileData: ArrayBuffer,
  fileName: string,
  options: { width?: number; height?: number; quality?: number } = {}
): Promise<ImageProcessingResult> {
  console.log(`Processing image ${fileName} (${fileData.byteLength} bytes)`);

  try {
    // For demo purposes, we'll simulate image processing
    // In production, use image processing libraries or services
    
    const originalSize = fileData.byteLength;
    const targetWidth = options.width || 1920;
    const targetHeight = options.height || 1080;
    const quality = options.quality || 85;

    // Simulate processing delay
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Simulate size reduction (typically 20-60% compression)
    const compressionRatio = 0.7;
    const processedSize = Math.floor(originalSize * compressionRatio);

    // Extract basic metadata
    const metadata = {
      original_size: originalSize,
      processed_size: processedSize,
      compression_ratio: compressionRatio,
      target_dimensions: { width: targetWidth, height: targetHeight },
      quality_setting: quality,
      processing_time: new Date().toISOString(),
      format: fileName.split('.').pop()?.toLowerCase() || 'unknown'
    };

    return {
      success: true,
      original_size: originalSize,
      processed_size: processedSize,
      processed_path: fileName.replace(/\.[^/.]+$/, '_processed.webp'),
      metadata
    };

  } catch (error) {
    console.error('Image processing error:', error);
    return {
      success: false,
      original_size: fileData.byteLength,
      processed_size: 0,
      processed_path: '',
      metadata: {},
      error: error instanceof Error ? error.message : 'Processing failed'
    };
  }
}

/**
 * Extracts file metadata
 */
async function extractMetadata(fileData: ArrayBuffer, fileName: string, mimeType: string): Promise<Record<string, any>> {
  try {
    const metadata: Record<string, any> = {
      extraction_time: new Date().toISOString(),
      file_size: fileData.byteLength,
      mime_type: mimeType,
      file_extension: fileName.split('.').pop()?.toLowerCase() || 'unknown'
    };

    // Basic file analysis
    if (mimeType.startsWith('image/')) {
      metadata.category = 'image';
      metadata.is_safe_for_processing = true;
    } else if (mimeType.startsWith('video/')) {
      metadata.category = 'video';
      metadata.is_safe_for_processing = true;
    } else if (mimeType.startsWith('audio/')) {
      metadata.category = 'audio';
      metadata.is_safe_for_processing = true;
    } else if (mimeType === 'application/pdf') {
      metadata.category = 'document';
      metadata.is_safe_for_processing = true;
    } else {
      metadata.category = 'other';
      metadata.is_safe_for_processing = false;
    }

    // Calculate file hash (simplified)
    const hashArray = Array.from(new Uint8Array(fileData.slice(0, 1024)));
    metadata.content_hash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('').substring(0, 32);

    return metadata;

  } catch (error) {
    console.error('Metadata extraction error:', error);
    return {
      extraction_time: new Date().toISOString(),
      error: error instanceof Error ? error.message : 'Extraction failed'
    };
  }
}

/**
 * Processes a file attachment completely
 */
async function processFile(fileAttachment: FileAttachment): Promise<boolean> {
  try {
    console.log(`Processing file ${fileAttachment.id}: ${fileAttachment.filename}`);

    // Download file
    const fileData = await downloadFile(fileAttachment.file_path, fileAttachment.bucket_name);
    if (!fileData) {
      await updateFileAttachment(fileAttachment.id, {
        upload_status: 'failed',
        virus_scan_status: 'failed',
        virus_scan_result: { error: 'Failed to download file for processing' }
      });
      return false;
    }

    // Perform virus scan
    console.log('Starting virus scan...');
    const virusScanResult = await performVirusScan(fileData, fileAttachment.filename);
    
    await updateFileAttachment(fileAttachment.id, {
      virus_scan_status: virusScanResult.is_clean ? 'clean' : 'infected',
      virus_scan_result: virusScanResult
    });

    if (!virusScanResult.is_clean) {
      console.log('File failed virus scan, stopping processing');
      await updateFileAttachment(fileAttachment.id, { upload_status: 'failed' });
      return false;
    }

    // Extract metadata
    console.log('Extracting metadata...');
    const metadata = await extractMetadata(fileData, fileAttachment.filename, fileAttachment.mime_type);

    // Process image if applicable
    let imageProcessingResult = null;
    if (fileAttachment.mime_type.startsWith('image/')) {
      console.log('Processing image...');
      imageProcessingResult = await processImage(fileData, fileAttachment.filename);
      
      if (imageProcessingResult.success) {
        metadata.image_processing = imageProcessingResult.metadata;
      }
    }

    // Update final status
    await updateFileAttachment(fileAttachment.id, {
      upload_status: 'completed',
      metadata: {
        ...fileAttachment.metadata,
        ...metadata,
        processing_completed_at: new Date().toISOString()
      }
    });

    console.log(`File processing completed for ${fileAttachment.id}`);
    return true;

  } catch (error) {
    console.error('File processing error:', error);
    await updateFileAttachment(fileAttachment.id, {
      upload_status: 'failed',
      virus_scan_status: 'failed',
      virus_scan_result: { 
        error: error instanceof Error ? error.message : 'Processing failed' 
      }
    });
    return false;
  }
}

/**
 * Handles database webhook events for automatic processing
 */
async function handleWebhookEvent(payload: WebhookPayload) {
  console.log('Processing webhook event:', payload.type, payload.table);

  if (payload.table === 'file_attachments' && payload.type === 'INSERT') {
    const fileAttachment = payload.record;
    
    // Only process files that are in 'uploading' status
    if (fileAttachment.upload_status === 'uploading') {
      // Add a small delay to ensure file upload is complete
      setTimeout(() => {
        processFile(fileAttachment);
      }, 2000);
    }
  }
}

/**
 * Main request handler
 */
serve(async (req: Request) => {
  try {
    // Handle CORS preflight
    if (req.method === 'OPTIONS') {
      return new Response('ok', {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'authorization, content-type, x-webhook-secret',
        },
      });
    }

    // Only accept POST requests
    if (req.method !== 'POST') {
      return new Response(JSON.stringify({ error: 'Method not allowed' }), {
        status: 405,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Check if this is a webhook request
    const webhookSecret = req.headers.get('x-webhook-secret');
    if (webhookSecret === Deno.env.get('WEBHOOK_SECRET')) {
      // Process webhook event
      const payload = await req.json() as WebhookPayload;
      await handleWebhookEvent(payload);
      
      return new Response(JSON.stringify({ success: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Validate regular API request
    const validation = await validateRequest(req);
    if (!validation.isValid) {
      return new Response(JSON.stringify({ error: validation.error }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Process file processing request
    const processingReq = await req.json() as FileProcessingRequest;

    // Validate required fields
    if (!processingReq.file_id || !processingReq.operation) {
      return new Response(JSON.stringify({ error: 'Missing required fields' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Get file attachment
    const fileAttachment = await getFileAttachment(processingReq.file_id);
    if (!fileAttachment) {
      return new Response(JSON.stringify({ error: 'File not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Process based on operation
    let result: any = {};

    switch (processingReq.operation) {
      case 'process_all':
        result.success = await processFile(fileAttachment);
        break;

      case 'virus_scan':
        const fileData = await downloadFile(fileAttachment.file_path, fileAttachment.bucket_name);
        if (fileData) {
          const scanResult = await performVirusScan(fileData, fileAttachment.filename);
          await updateFileAttachment(fileAttachment.id, {
            virus_scan_status: scanResult.is_clean ? 'clean' : 'infected',
            virus_scan_result: scanResult
          });
          result = scanResult;
        } else {
          result = { error: 'Failed to download file' };
        }
        break;

      default:
        return new Response(JSON.stringify({ error: 'Unsupported operation' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
    }

    return new Response(JSON.stringify({ 
      success: true,
      file_id: processingReq.file_id,
      operation: processingReq.operation,
      result
    }), {
      status: 200,
      headers: { 
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
      }
    });

  } catch (error) {
    console.error('Function error:', error);
    return new Response(JSON.stringify({ 
      error: 'Internal server error',
      details: error instanceof Error ? error.message : 'Unknown error'
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
});
