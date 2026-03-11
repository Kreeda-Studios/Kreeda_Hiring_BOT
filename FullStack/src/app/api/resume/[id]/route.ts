/**
 * Get Single Resume API Route
 * GET /api/resume/[id]
 */

import { NextRequest, NextResponse } from 'next/server';
import { ResumeService } from '@/backend/services/resume.service';
import { getPublicUrl, s3Config } from '@/backend/config/s3';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    
    console.log('Fetching resume with ID:', id);

    const resume = await ResumeService.getResumeById(id);
    
    console.log('Resume found:', resume ? 'Yes' : 'No');

    if (!resume) {
      return NextResponse.json(
        { error: 'Resume not found' },
        { status: 404 }
      );
    }

    // Generate file URL for viewing
    const bucket = s3Config.buckets.resumes;
    const fileUrl = getPublicUrl(bucket, resume.resumeFilePath);
    
    console.log('Generated file URL:', fileUrl);

    return NextResponse.json({
      success: true,
      data: {
        resume,
        fileUrl,
      },
    }, {
      headers: {
        // No cache - always fetch fresh data
        'Cache-Control': 'no-store, no-cache, must-revalidate',
      },
    });

  } catch (error) {
    console.error('Get resume error:', error);
    return NextResponse.json(
      { 
        error: 'Failed to fetch resume', 
        details: error instanceof Error ? error.message : 'Unknown error' 
      },
      { status: 500 }
    );
  }
}
