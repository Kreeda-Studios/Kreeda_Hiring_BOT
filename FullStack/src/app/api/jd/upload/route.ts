/**
 * JD Upload API Route
 * POST /api/jd/upload
 */

import { NextRequest, NextResponse } from 'next/server';
import { PutObjectCommand } from '@aws-sdk/client-s3';
import { s3Client, s3Config } from '@/backend/config/s3';
import { JDService } from '@/backend/services/jd.service';
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

    // Validate file type
    const fileType = file.type;
    if (!fileType.includes('pdf') && !fileType.includes('docx')) {
      return NextResponse.json(
        { error: 'Only PDF and DOCX files are supported' },
        { status: 400 }
      );
    }

    // Generate unique filename
    const randomPrefix = randomUUID().slice(0, 8);
    const originalFileName = file.name;
    const fileName = `${randomPrefix}_${originalFileName}`;
    const fileExtension = originalFileName.split('.').pop() || 'pdf';

    // Convert file to buffer
    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    // Upload to S3 / MinIO
    const bucket = s3Config.buckets.jds;
    const s3Key = fileName;

    const command = new PutObjectCommand({
      Bucket: bucket,
      Key: s3Key,
      Body: buffer,
      ContentType: file.type,
    });

    await s3Client.send(command);

    // Create JD entry in database
    const jd = await JDService.createJD({
      fileName,
      originalFileName,
      jdFilePath: s3Key,
      fileSize: file.size,
      fileType: fileExtension === 'pdf' ? 'pdf' : 'docx',
    });

    // Add to processing queue
    await JDService.addToQueue(
      jd._id.toString(),
      fileName,
      s3Key
    );

    return NextResponse.json({
      success: true,
      data: {
        jdId: jd._id,
        fileName,
        originalFileName,
        status: jd.status,
        uploadedAt: jd.uploadedAt,
      },
    });

  } catch (error) {
    console.error('Error uploading JD:', error);
    return NextResponse.json(
      { error: 'Failed to upload JD', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
