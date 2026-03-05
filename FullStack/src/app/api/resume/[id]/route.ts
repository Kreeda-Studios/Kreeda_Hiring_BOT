/**
 * Get Single Resume API Route
 * GET /api/resume/[id]
 */

import { NextRequest, NextResponse } from 'next/server';
import { ResumeService } from '@/backend/services/resume.service';
import { getPublicUrl } from '@/backend/config/minio';

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
    const bucket = process.env.MINIO_BUCKET_RESUMES!;
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
        // Cache for 5 minutes to reduce API calls
        'Cache-Control': 'private, max-age=300',
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
