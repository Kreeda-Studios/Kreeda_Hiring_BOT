/**
 * File Upload API Route - MinIO/S3 Example
 * POST /api/upload
 */

import { NextRequest, NextResponse } from 'next/server';
import { PutObjectCommand } from '@aws-sdk/client-s3';
import { s3Client, minioConfig, getPublicUrl } from '@/backend/config/minio';
import { randomUUID } from 'crypto';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const file = formData.get('file') as File;

    if (!file) {
      return NextResponse.json(
        { error: 'No file provided' },
        { status: 400 }
      );
    }

    // Generate unique filename
    const fileExtension = file.name.split('.').pop();
    const fileName = `${randomUUID()}.${fileExtension}`;

    // Convert file to buffer
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    // Upload to MinIO
    const bucket = minioConfig.buckets.resumes;
    const command = new PutObjectCommand({
      Bucket: bucket,
      Key: fileName,
      Body: buffer,
      ContentType: file.type,
    });

    await s3Client.send(command);

    // Get public URL
    const fileUrl = getPublicUrl(bucket, fileName);

    return NextResponse.json({
      success: true,
      data: {
        fileName,
        fileUrl,
        bucket,
        size: file.size,
        type: file.type,
      },
    });

  } catch (error) {
    console.error('File upload error:', error);
    return NextResponse.json(
      { error: 'Failed to upload file', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

// GET endpoint to list files
export async function GET() {
  try {
    // This is a placeholder - implement listing logic as needed
    return NextResponse.json({
      message: 'File upload endpoint',
      usage: 'POST with multipart/form-data containing a file field',
    });
  } catch (error) {
    console.error('Error:', error);
    return NextResponse.json(
      { error: 'Failed to process request' },
      { status: 500 }
    );
  }
}
