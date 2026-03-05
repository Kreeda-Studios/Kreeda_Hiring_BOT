/**
 * File Proxy API Route
 * GET /api/files/[bucket]/[...key]
 * 
 * Proxies file requests to internal MinIO server
 * This allows exposing only port 3000 publicly while keeping MinIO internal
 */

import { NextRequest, NextResponse } from 'next/server';
import { minioClient } from '@/backend/config/minio';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ bucket: string; key: string[] }> }
) {
  try {
    const { bucket, key } = await params;
    const objectKey = key.join('/');

    console.log(`[File Proxy] Fetching: ${bucket}/${objectKey}`);

    // Get file from MinIO
    const stream = await minioClient.getObject(bucket, objectKey);

    // Get file metadata for content type
    const stat = await minioClient.statObject(bucket, objectKey);

    // Convert stream to buffer
    const chunks: Buffer[] = [];
    for await (const chunk of stream) {
      chunks.push(chunk);
    }
    const buffer = Buffer.concat(chunks);

    // Return file with appropriate headers
    return new NextResponse(buffer, {
      headers: {
        'Content-Type': stat.metaData['content-type'] || 'application/octet-stream',
        'Content-Length': stat.size.toString(),
        'Cache-Control': 'public, max-age=31536000, immutable', // Cache for 1 year
        'Content-Disposition': `inline; filename="${objectKey.split('/').pop()}"`,
      },
    });

  } catch (error: any) {
    console.error('[File Proxy] Error:', error);
    
    if (error.code === 'NoSuchKey' || error.code === 'NotFound') {
      return NextResponse.json(
        { error: 'File not found' },
        { status: 404 }
      );
    }

    return NextResponse.json(
      { error: 'Failed to fetch file', details: error.message },
      { status: 500 }
    );
  }
}
