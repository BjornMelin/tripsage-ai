import type { NextRequest } from 'next/server';
import { randomUUID } from 'crypto';
import { z } from 'zod';
import path from 'path';
import { writeFile, mkdir } from 'fs/promises';

// Mock in-memory storage for uploaded files
// In production, you would use proper file storage like S3, Supabase Storage, etc.
const UPLOADS_DIR = path.join(process.cwd(), 'public', 'uploads');

// Create a temporary in-memory cache for this example
const fileCache = new Map<string, { name: string, type: string, size: number }>();

/**
 * POST handler for /api/chat/attachments
 * For prototype purposes, this saves files to the local /public/uploads folder
 * In production, you'd use cloud storage like S3 or Supabase Storage
 */
export async function POST(req: NextRequest) {
  try {
    // Ensure the uploads directory exists
    try {
      await mkdir(UPLOADS_DIR, { recursive: true });
    } catch (error) {
      console.error('Error creating uploads directory:', error);
    }

    // Process form data with files
    const formData = await req.formData();
    const files: File[] = [];
    
    // Extract files from form data
    for (const entry of Array.from(formData.entries())) {
      const [key, value] = entry;
      
      if (value instanceof File) {
        files.push(value);
      }
    }
    
    if (files.length === 0) {
      return new Response(
        JSON.stringify({ error: 'No files uploaded' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }
    
    // Process and save each file
    const savedFiles = await Promise.all(
      files.map(async (file) => {
        const fileId = randomUUID();
        const fileName = file.name.replace(/[^a-zA-Z0-9.-]/g, '_');
        const fileExt = path.extname(fileName);
        const uniqueFileName = `${fileId}${fileExt}`;
        const filePath = path.join(UPLOADS_DIR, uniqueFileName);
        
        // Save to a buffer before writing to file
        const buffer = Buffer.from(await file.arrayBuffer());
        await writeFile(filePath, buffer);
        
        // Store metadata in memory (in production, use a database)
        fileCache.set(fileId, {
          name: fileName,
          type: file.type,
          size: file.size,
        });
        
        // Generate public URL
        const publicUrl = `/uploads/${uniqueFileName}`;
        
        return publicUrl;
      })
    );
    
    // Return URLs of saved files
    return new Response(
      JSON.stringify({ urls: savedFiles }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    );
  } catch (error) {
    console.error('Error processing file upload:', error);
    return new Response(
      JSON.stringify({ error: 'Failed to process file upload' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}