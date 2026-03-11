/**
 * Get Single JD by ID
 * GET /api/jd/[id]
 */

import { NextRequest, NextResponse } from 'next/server';
import { JDService } from '@/backend/services/jd.service';
import { getPublicUrl, s3Config } from '@/backend/config/s3';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    if (!id) {
      return NextResponse.json({ error: 'JD ID is required' }, { status: 400 });
    }

    const jd = await JDService.getJDById(id);

    if (!jd) {
      return NextResponse.json({ error: 'JD not found' }, { status: 404 });
    }

    // Generate a proxied URL for the PDF viewer
    const bucket = s3Config.buckets.jds;
    const fileUrl = getPublicUrl(bucket, jd.jdFilePath);

    return NextResponse.json(
      {
        success: true,
        data: { jd, fileUrl },
      },
      {
        headers: { 'Cache-Control': 'no-store, no-cache, must-revalidate' },
      }
    );

  } catch (error) {
    console.error('Error fetching JD:', error);
    return NextResponse.json(
      { error: 'Failed to fetch JD', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
