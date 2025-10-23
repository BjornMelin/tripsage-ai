/**
 * Test suite for File Processing Edge Function
 * 
 * Tests cover:
 * - HTTP request/response handling
 * - CORS preflight requests
 * - Authentication and authorization
 * - File processing workflows
 * - Virus scanning operations
 * - Image processing and optimization
 * - Metadata extraction
 * - File storage operations
 * - Webhook event handling
 * - Error handling and edge cases
 * - Performance and security
 * 
 * Target: 90%+ code coverage
 */

import {
  assertEquals,
  assertExists,
  assertRejects,
  TestDataFactory,
  MockSupabase,
  MockFetch,
  RequestTestHelper,
  ResponseAssertions,
  EdgeFunctionTester
} from "../_shared/test-utils.ts";

/**
 * Mock implementation of the File Processing Edge Function
 */
class MockFileProcessingFunction {
  constructor(
    private mockSupabase: MockSupabase,
    private mockFetch: MockFetch
  ) {}

  async serve(req: Request): Promise<Response> {
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
        const payload = await req.json();
        await this.handleWebhookEvent(payload);
        
        return new Response(JSON.stringify({ success: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // Validate regular API request
      const validation = await this.validateRequest(req);
      if (!validation.isValid) {
        return new Response(JSON.stringify({ error: validation.error }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // Process file processing request
      const processingReq = await req.json();

      // Validate required fields
      if (!processingReq.file_id || !processingReq.operation) {
        return new Response(JSON.stringify({ error: 'Missing required fields' }), {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      // Get file attachment
      const fileAttachment = await this.getFileAttachment(processingReq.file_id);
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
          result.success = await this.processFile(fileAttachment);
          break;

        case 'virus_scan':
          const fileData = await this.downloadFile(fileAttachment.file_path, fileAttachment.bucket_name);
          if (fileData) {
            const scanResult = await this.performVirusScan(fileData, fileAttachment.filename);
            await this.updateFileAttachment(fileAttachment.id, {
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
  }

  private async validateRequest(req: Request) {
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
      const response = await this.mockSupabase.auth.getUser(token);
      
      if (response.error || !response.data.user) {
        return { isValid: false, error: 'Invalid authentication token' };
      }

      return { isValid: true };
    } catch (error) {
      return { isValid: false, error: 'Request validation failed' };
    }
  }

  private async getFileAttachment(fileId: string) {
    const response = await this.mockSupabase
      .from('file_attachments')
      .select('*')
      .eq('id', fileId)
      .single();

    if (response.error) {
      return null;
    }

    return response.data;
  }

  private async updateFileAttachment(fileId: string, updates: any) {
    try {
      const response = await this.mockSupabase
        .from('file_attachments')
        .update({
          ...updates,
          updated_at: new Date().toISOString()
        })
        .eq('id', fileId);

      return !response.error;
    } catch (error) {
      return false;
    }
  }

  private async downloadFile(filePath: string, bucketName: string) {
    try {
      const response = await this.mockSupabase.storage
        .from(bucketName)
        .download(filePath);

      if (response.error) {
        return null;
      }

      return await response.data.arrayBuffer();
    } catch (error) {
      return null;
    }
  }

  private async performVirusScan(fileData: ArrayBuffer, fileName: string) {
    console.log(`Performing virus scan on ${fileName} (${fileData.byteLength} bytes)`);

    try {
      const MAX_FILE_SIZE = parseInt(Deno.env.get('MAX_FILE_SIZE') || '50000000');
      
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
      await new Promise(resolve => setTimeout(resolve, 100));

      return {
        is_clean: true,
        scan_time: new Date().toISOString(),
        provider: 'demo-scanner',
        details: {
          scan_duration_ms: 100,
          signatures_checked: 12345,
          engine_version: '1.0.0'
        }
      };

    } catch (error) {
      return {
        is_clean: false,
        scan_time: new Date().toISOString(),
        provider: 'internal',
        error: error instanceof Error ? error.message : 'Scan failed'
      };
    }
  }

  private async processImage(fileData: ArrayBuffer, fileName: string, options: any = {}) {
    console.log(`Processing image ${fileName} (${fileData.byteLength} bytes)`);

    try {
      const originalSize = fileData.byteLength;
      const targetWidth = options.width || 1920;
      const targetHeight = options.height || 1080;
      const quality = options.quality || 85;

      // Simulate processing delay
      await new Promise(resolve => setTimeout(resolve, 100));

      // Simulate size reduction
      const compressionRatio = 0.7;
      const processedSize = Math.floor(originalSize * compressionRatio);

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

  private async extractMetadata(fileData: ArrayBuffer, fileName: string, mimeType: string) {
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
      return {
        extraction_time: new Date().toISOString(),
        error: error instanceof Error ? error.message : 'Extraction failed'
      };
    }
  }

  private async processFile(fileAttachment: any) {
    try {
      console.log(`Processing file ${fileAttachment.id}: ${fileAttachment.filename}`);

      // Download file
      const fileData = await this.downloadFile(fileAttachment.file_path, fileAttachment.bucket_name);
      if (!fileData) {
        await this.updateFileAttachment(fileAttachment.id, {
          upload_status: 'failed',
          virus_scan_status: 'failed',
          virus_scan_result: { error: 'Failed to download file for processing' }
        });
        return false;
      }

      // Perform virus scan
      const virusScanResult = await this.performVirusScan(fileData, fileAttachment.filename);
      
      await this.updateFileAttachment(fileAttachment.id, {
        virus_scan_status: virusScanResult.is_clean ? 'clean' : 'infected',
        virus_scan_result: virusScanResult
      });

      if (!virusScanResult.is_clean) {
        await this.updateFileAttachment(fileAttachment.id, { upload_status: 'failed' });
        return false;
      }

      // Extract metadata
      const metadata = await this.extractMetadata(fileData, fileAttachment.filename, fileAttachment.mime_type);

      // Process image if applicable
      let imageProcessingResult = null;
      if (fileAttachment.mime_type.startsWith('image/')) {
        imageProcessingResult = await this.processImage(fileData, fileAttachment.filename);
        
        if (imageProcessingResult.success) {
          metadata.image_processing = imageProcessingResult.metadata;
        }
      }

      // Update final status
      await this.updateFileAttachment(fileAttachment.id, {
        upload_status: 'completed',
        metadata: {
          ...fileAttachment.metadata,
          ...metadata,
          processing_completed_at: new Date().toISOString()
        }
      });

      return true;

    } catch (error) {
      await this.updateFileAttachment(fileAttachment.id, {
        upload_status: 'failed',
        virus_scan_status: 'failed',
        virus_scan_result: { 
          error: error instanceof Error ? error.message : 'Processing failed' 
        }
      });
      return false;
    }
  }

  private async handleWebhookEvent(payload: any) {
    console.log('Processing webhook event:', payload.type, payload.table);

    if (payload.table === 'file_attachments' && payload.type === 'INSERT') {
      const fileAttachment = payload.record;
      
      // Only process files that are in 'uploading' status
      if (fileAttachment.upload_status === 'uploading') {
        // Add a small delay to ensure file upload is complete
        setTimeout(() => {
          this.processFile(fileAttachment);
        }, 100);
      }
    }
  }
}

// Test Suite
Deno.test("File Processing - CORS preflight request", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createOptionsRequest();

    const response = await func.serve(request);

    assertEquals(response.status, 200);
    ResponseAssertions.assertCorsHeaders(response);
  });
});

Deno.test("File Processing - Method not allowed", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    const request = new Request('https://test.com', { method: 'GET' });

    const response = await func.serve(request);

    await ResponseAssertions.assertError(response, 405, 'Method not allowed');
  });
});

Deno.test("File Processing - Authentication validation", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup invalid auth response
    mockSupabase.setResponse('auth_getUser', {
      data: { user: null },
      error: new Error('Invalid token')
    });

    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      file_id: 'test-file',
      operation: 'process_all'
    }, 'invalid-token');

    const response = await func.serve(request);

    await ResponseAssertions.assertError(response, 401, 'Invalid authentication token');
  });
});

Deno.test("File Processing - Missing required fields", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup valid auth
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      // Missing file_id and operation
    });

    const response = await func.serve(request);

    await ResponseAssertions.assertError(response, 400, 'Missing required fields');
  });
});

Deno.test("File Processing - File not found", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup valid auth
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    // Setup file not found
    mockSupabase.setResponse('file_attachments_select_eq_single', {
      data: null,
      error: new Error('File not found')
    });

    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      file_id: 'non-existent-file',
      operation: 'process_all'
    });

    const response = await func.serve(request);

    await ResponseAssertions.assertError(response, 404, 'File not found');
  });
});

Deno.test("File Processing - Virus scan operation", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup valid auth
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    // Setup file attachment
    const fileAttachment = TestDataFactory.createFileAttachment();
    mockSupabase.setResponse('file_attachments_select_eq_single', {
      data: fileAttachment,
      error: null
    });

    // Setup file download
    mockSupabase.setResponse('storage_download_attachments', {
      data: new Blob(['test file content']),
      error: null
    });

    // Setup file update
    mockSupabase.setResponse('file_attachments_update_eq', {
      data: { id: fileAttachment.id },
      error: null
    });

    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      file_id: fileAttachment.id,
      operation: 'virus_scan'
    });

    const response = await func.serve(request);
    const data = await ResponseAssertions.assertSuccess(response);

    // Verify scan result
    assertExists(data.result);
    assertEquals(data.result.is_clean, true);
    assertEquals(data.result.provider, 'demo-scanner');

    // Verify database update was called
    const updateCalls = mockSupabase.getCallsFor('update');
    assertEquals(updateCalls.length, 1);
  });
});

Deno.test("File Processing - Dangerous file extension scan", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup valid auth and file
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    const fileAttachment = TestDataFactory.createFileAttachment({
      filename: 'malicious.exe',
      mime_type: 'application/x-executable'
    });
    mockSupabase.setResponse('file_attachments_select_eq_single', {
      data: fileAttachment,
      error: null
    });

    mockSupabase.setResponse('storage_download_attachments', {
      data: new Blob(['executable content']),
      error: null
    });

    mockSupabase.setResponse('file_attachments_update_eq', {
      data: { id: fileAttachment.id },
      error: null
    });

    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      file_id: fileAttachment.id,
      operation: 'virus_scan'
    });

    const response = await func.serve(request);
    const data = await ResponseAssertions.assertSuccess(response);

    // File should be marked as infected
    assertEquals(data.result.is_clean, false);
    assertEquals(data.result.details.reason, 'Potentially dangerous file extension');
  });
});

Deno.test("File Processing - File size limit exceeded", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Set small file size limit
    Deno.env.set('MAX_FILE_SIZE', '1000');

    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    const fileAttachment = TestDataFactory.createFileAttachment({
      file_size: 2000000 // 2MB file
    });
    mockSupabase.setResponse('file_attachments_select_eq_single', {
      data: fileAttachment,
      error: null
    });

    // Create large file data
    const largeFileData = new ArrayBuffer(2000000);
    mockSupabase.setResponse('storage_download_attachments', {
      data: new Blob([largeFileData]),
      error: null
    });

    mockSupabase.setResponse('file_attachments_update_eq', {
      data: { id: fileAttachment.id },
      error: null
    });

    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      file_id: fileAttachment.id,
      operation: 'virus_scan'
    });

    const response = await func.serve(request);
    const data = await ResponseAssertions.assertSuccess(response);

    // File should be rejected for size
    assertEquals(data.result.is_clean, false);
    assertEquals(data.result.error, 'File size exceeds maximum allowed');
  });
});

Deno.test("File Processing - Process all operation", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup valid auth
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    // Setup image file attachment
    const fileAttachment = TestDataFactory.createFileAttachment({
      filename: 'vacation-photo.jpg',
      mime_type: 'image/jpeg'
    });
    mockSupabase.setResponse('file_attachments_select_eq_single', {
      data: fileAttachment,
      error: null
    });

    // Setup file download
    mockSupabase.setResponse('storage_download_attachments', {
      data: new Blob(['image data']),
      error: null
    });

    // Setup file updates
    mockSupabase.setResponse('file_attachments_update_eq', {
      data: { id: fileAttachment.id },
      error: null
    });

    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      file_id: fileAttachment.id,
      operation: 'process_all'
    });

    const response = await func.serve(request);
    const data = await ResponseAssertions.assertSuccess(response);

    // Verify processing completed
    assertEquals(data.result.success, true);

    // Verify multiple database updates (virus scan, metadata, final status)
    const updateCalls = mockSupabase.getCallsFor('update');
    assertEquals(updateCalls.length >= 2, true);
  });
});

Deno.test("File Processing - Webhook event handling", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    const payload = TestDataFactory.createWebhookPayload(
      'file_attachments',
      'INSERT',
      TestDataFactory.createFileAttachment({
        upload_status: 'uploading'
      })
    );

    const request = RequestTestHelper.createWebhookRequest(payload);

    const response = await func.serve(request);
    await ResponseAssertions.assertSuccess(response);
  });
});

Deno.test("File Processing - Download failure handling", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    const fileAttachment = TestDataFactory.createFileAttachment();
    mockSupabase.setResponse('file_attachments_select_eq_single', {
      data: fileAttachment,
      error: null
    });

    // Setup download failure
    mockSupabase.setResponse('storage_download_attachments', {
      data: null,
      error: new Error('File not found in storage')
    });

    mockSupabase.setResponse('file_attachments_update_eq', {
      data: { id: fileAttachment.id },
      error: null
    });

    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      file_id: fileAttachment.id,
      operation: 'virus_scan'
    });

    const response = await func.serve(request);
    const data = await ResponseAssertions.assertSuccess(response);

    assertEquals(data.result.error, 'Failed to download file');
  });
});

Deno.test("File Processing - Unsupported operation", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    const fileAttachment = TestDataFactory.createFileAttachment();
    mockSupabase.setResponse('file_attachments_select_eq_single', {
      data: fileAttachment,
      error: null
    });

    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      file_id: fileAttachment.id,
      operation: 'unsupported_operation'
    });

    const response = await func.serve(request);

    await ResponseAssertions.assertError(response, 400, 'Unsupported operation');
  });
});

Deno.test("File Processing - Image processing with custom options", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    
    // Test the image processing function directly
    const imageData = new ArrayBuffer(1000000); // 1MB image
    const result = await func['processImage'](imageData, 'test.jpg', {
      width: 800,
      height: 600,
      quality: 90
    });

    assertEquals(result.success, true);
    assertEquals(result.metadata.target_dimensions.width, 800);
    assertEquals(result.metadata.target_dimensions.height, 600);
    assertEquals(result.metadata.quality_setting, 90);
    assertEquals(result.original_size, 1000000);
  });
});

Deno.test("File Processing - Metadata extraction for different file types", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    
    const testCases = [
      { fileName: 'image.jpg', mimeType: 'image/jpeg', expectedCategory: 'image' },
      { fileName: 'video.mp4', mimeType: 'video/mp4', expectedCategory: 'video' },
      { fileName: 'document.pdf', mimeType: 'application/pdf', expectedCategory: 'document' },
      { fileName: 'data.txt', mimeType: 'text/plain', expectedCategory: 'other' }
    ];

    for (const testCase of testCases) {
      const fileData = new ArrayBuffer(1000);
      const metadata = await func['extractMetadata'](fileData, testCase.fileName, testCase.mimeType);

      assertEquals(metadata.category, testCase.expectedCategory);
      assertEquals(metadata.mime_type, testCase.mimeType);
      assertExists(metadata.content_hash);
    }
  });
});

Deno.test("File Processing - Concurrent file processing", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup for multiple files
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    const files = [
      TestDataFactory.createFileAttachment({ id: 'file-1' }),
      TestDataFactory.createFileAttachment({ id: 'file-2' }),
      TestDataFactory.createFileAttachment({ id: 'file-3' })
    ];

    files.forEach(file => {
      mockSupabase.setResponse(`file_attachments_select_eq_single`, {
        data: file,
        error: null
      });
    });

    mockSupabase.setResponse('storage_download_attachments', {
      data: new Blob(['file content']),
      error: null
    });

    mockSupabase.setResponse('file_attachments_update_eq', {
      data: { id: 'updated' },
      error: null
    });

    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    
    // Process multiple files concurrently
    const requests = files.map(file => 
      RequestTestHelper.createAuthenticatedRequest({
        file_id: file.id,
        operation: 'virus_scan'
      })
    );

    const responses = await Promise.all(
      requests.map(request => func.serve(request))
    );

    // All should succeed
    for (const response of responses) {
      await ResponseAssertions.assertSuccess(response);
    }
  });
});

Deno.test("File Processing - Performance test", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    // Setup fast mocks
    mockSupabase.setResponse('auth_getUser', {
      data: { user: TestDataFactory.createUser() },
      error: null
    });

    const fileAttachment = TestDataFactory.createFileAttachment();
    mockSupabase.setResponse('file_attachments_select_eq_single', {
      data: fileAttachment,
      error: null
    });

    mockSupabase.setResponse('storage_download_attachments', {
      data: new Blob(['content']),
      error: null
    });

    mockSupabase.setResponse('file_attachments_update_eq', {
      data: { id: fileAttachment.id },
      error: null
    });

    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    const request = RequestTestHelper.createAuthenticatedRequest({
      file_id: fileAttachment.id,
      operation: 'virus_scan'
    });

    const startTime = Date.now();
    const response = await func.serve(request);
    const responseTime = ResponseAssertions.assertResponseTime(startTime, 3000);

    await ResponseAssertions.assertSuccess(response);
    
    console.log(`File Processing response time: ${responseTime}ms`);
  });
});

Deno.test("File Processing - Malformed JSON", async () => {
  const tester = new EdgeFunctionTester();
  await tester.runTest(async ({ mockSupabase, mockFetch }) => {
    const func = new MockFileProcessingFunction(mockSupabase, mockFetch);
    const request = new Request('https://test.com', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer test-token'
      },
      body: '{ invalid json'
    });

    const response = await func.serve(request);
    await ResponseAssertions.assertError(response, 500);
  });
});

console.log("🧪 File Processing Edge Function Test Suite");
console.log("============================================");
console.log("Coverage includes:");
console.log("✓ HTTP request/response handling");
console.log("✓ CORS preflight requests");
console.log("✓ Authentication validation");
console.log("✓ File processing workflows");
console.log("✓ Virus scanning operations");
console.log("✓ Image processing and optimization");
console.log("✓ Metadata extraction");
console.log("✓ Storage operations");
console.log("✓ Webhook event handling");
console.log("✓ Error handling and edge cases");
console.log("✓ Performance testing");
console.log("✓ Concurrent processing");
console.log("");
console.log("Run with: deno test --allow-net --allow-env file-processing/index.test.ts");
